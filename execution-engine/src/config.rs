//! JSON mask configuration consumed from alpha-swarm output.

use std::fs;
use std::path::Path;

use serde::Deserialize;

use crate::hdc::Hypervector;

#[derive(Debug, Clone, Deserialize)]
pub struct MaskEntry {
    pub id: String,
    pub target_hypervector_mask: String,
    pub similarity_threshold: f64,
}

#[derive(Debug, Clone, Deserialize)]
pub struct HdcMaskConfig {
    pub version: u32,
    pub masks: Vec<MaskEntry>,
}

impl HdcMaskConfig {
    pub fn load(path: &Path) -> Result<Self, Box<dyn std::error::Error>> {
        let raw = fs::read_to_string(path)?;
        let cfg: Self = serde_json::from_str(&raw)?;
        Ok(cfg)
    }
}

impl MaskEntry {
    pub fn decode_mask(&self) -> Result<Hypervector, Box<dyn std::error::Error>> {
        Hypervector::from_hex(&self.target_hypervector_mask)
    }
}
