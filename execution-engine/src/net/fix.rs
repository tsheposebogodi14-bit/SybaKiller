//! FIX over pre-serialized Ethernet frames (TX ring stub).

use crate::pipeline::HotTick;

/// Stage execution trigger — temporal arb, jitter-tolerant.
pub fn stage_trigger(_tick: &HotTick, mask_id: &str) -> Result<(), ()> {
    // Production: push pre-serialized frame to AF_XDP TX ring.
    tracing::debug!(mask_id, "FIX frame staged (TX stub)");
    Ok(())
}
