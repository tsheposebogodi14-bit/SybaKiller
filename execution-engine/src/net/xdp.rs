//! AF_XDP / eBPF UMEM — enabled with `kernel-bypass` on PREEMPT_RT hosts.

#[cfg(feature = "kernel-bypass")]
pub fn init_nic(_ifname: &str) -> Result<(), Box<dyn std::error::Error>> {
    Err("kernel-bypass: wire aya/xsk-rs on target hardware".into())
}

#[cfg(not(feature = "kernel-bypass"))]
pub fn init_nic(_ifname: &str) -> Result<(), Box<dyn std::error::Error>> {
    Ok(())
}
