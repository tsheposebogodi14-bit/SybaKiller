//! Hyperdimensional Computing — 10_000-bit vectors, XOR + popcount hot path.

mod simd;

use crate::config::HdcMaskConfig;

pub const HYPERVECTOR_BITS: usize = 10_000;
pub const HYPERVECTOR_BYTES: usize = HYPERVECTOR_BITS / 8;

/// Cache-line aligned hypervector (1250 bytes + padding).
#[repr(C, align(64))]
pub struct Hypervector {
    pub data: [u8; HYPERVECTOR_BYTES],
    _pad: [u8; 30],
}

impl Hypervector {
    pub fn from_hex(hex_str: &str) -> Result<Self, Box<dyn std::error::Error>> {
        let bytes = hex::decode(hex_str.trim())?;
        if bytes.len() != HYPERVECTOR_BYTES {
            return Err(format!(
                "mask must be {} bytes ({} bits), got {}",
                HYPERVECTOR_BYTES,
                HYPERVECTOR_BITS,
                bytes.len()
            )
            .into());
        }
        let mut data = [0u8; HYPERVECTOR_BYTES];
        data.copy_from_slice(&bytes);
        Ok(Self { data, _pad: [0; 30] })
    }

    pub fn from_market_tick(tick: &crate::pipeline::HotTick) -> Self {
        let mut hv = Self {
            data: [0u8; HYPERVECTOR_BYTES],
            _pad: [0; 30],
        };
        // Deterministic feature packing for temporal-arb triggers (not micro-arb).
        let bid_q = (tick.bid_fp as u64).to_le_bytes();
        let ask_q = (tick.ask_fp as u64).to_le_bytes();
        let ts_q = tick.ts_ns.to_le_bytes();
        let sym_hash = tick.symbol_id.to_le_bytes();
        hv.data[0..8].copy_from_slice(&bid_q);
        hv.data[8..16].copy_from_slice(&ask_q);
        hv.data[16..24].copy_from_slice(&ts_q);
        hv.data[24..28].copy_from_slice(&sym_hash);
        hv
    }

    pub fn hamming_similarity(&self, other: &Self) -> f64 {
        let distance = simd::popcount_xor(&self.data, &other.data);
        1.0 - (distance as f64 / HYPERVECTOR_BITS as f64)
    }
}

pub struct MatchScore {
    pub mask_id: String,
    pub similarity: f64,
    pub threshold: f64,
}

pub struct HdcEngine {
    masks: Vec<(String, Hypervector, f64)>,
}

impl HdcEngine {
    pub fn from_config(cfg: &HdcMaskConfig) -> Result<Self, Box<dyn std::error::Error>> {
        let mut masks = Vec::with_capacity(cfg.masks.len());
        for entry in &cfg.masks {
            masks.push((entry.id.clone(), entry.decode_mask()?, entry.similarity_threshold));
        }
        Ok(Self { masks })
    }

    pub fn best_match(&self, feature: &Hypervector) -> Option<MatchScore> {
        let mut best: Option<MatchScore> = None;
        for (id, mask, threshold) in &self.masks {
            let similarity = feature.hamming_similarity(mask);
            if similarity >= *threshold {
                let replace = best
                    .as_ref()
                    .map(|b| similarity > b.similarity)
                    .unwrap_or(true);
                if replace {
                    best = Some(MatchScore {
                        mask_id: id.clone(),
                        similarity,
                        threshold: *threshold,
                    });
                }
            }
        }
        best
    }
}
