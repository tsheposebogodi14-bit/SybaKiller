//! Sovereign execution engine — loads HDC masks, runs hot-path pipeline.

mod config;
mod hdc;
mod pipeline;
mod net;

use std::path::PathBuf;
use std::sync::Arc;

use tracing::info;

use crate::config::HdcMaskConfig;
use crate::hdc::{Hypervector, HdcEngine};
use crate::pipeline::SpscIngress;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();

    let mask_path = std::env::var("HDC_MASKS_PATH")
        .map(PathBuf::from)
        .unwrap_or_else(|_| PathBuf::from("config/hdc_masks.json"));

    let masks = HdcMaskConfig::load(&mask_path)?;
    info!(path = %mask_path.display(), count = masks.masks.len(), "HDC masks loaded");

    let engine = Arc::new(HdcEngine::from_config(&masks)?);
    let mut ingress = SpscIngress::new(65_536)?;

    if std::env::var("EXEC_ENGINE_VALIDATE_ONLY").is_ok() {
        info!("mask validation OK");
        return Ok(());
    }

    info!("execution-engine ready (ingress=SPSC, kernel-bypass=stub)");
    loop {
        if let Ok(tick) = ingress.pop() {
            let feature = Hypervector::from_market_tick(&tick);
            if let Some(score) = engine.best_match(&feature) {
                if score.similarity >= score.threshold {
                    info!(
                        mask_id = score.mask_id,
                        similarity = score.similarity,
                        "HDC trigger (temporal arb)"
                    );
                    let _ = net::fix::stage_trigger(&tick, &score.mask_id);
                }
            }
        }
        std::hint::spin_loop();
    }
}
