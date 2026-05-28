//! Lock-free SPSC ingress — zero heap in hot path after setup.

mod spsc;

pub use spsc::SpscIngress;

/// Cache-line aligned market tick (hot path).
#[repr(C, align(64))]
pub struct HotTick {
    pub symbol_id: u32,
    pub bid_fp: i64,
    pub ask_fp: i64,
    pub ts_ns: u64,
    pub jitter_ns: u32,
    _pad: u32,
}

impl HotTick {
    pub fn new(symbol_id: u32, bid_fp: i64, ask_fp: i64, ts_ns: u64, jitter_ns: u32) -> Self {
        Self {
            symbol_id,
            bid_fp,
            ask_fp,
            ts_ns,
            jitter_ns,
            _pad: 0,
        }
    }
}
