# execution-engine (The Weapon)

Rust ultra-low-latency execution for sovereign bare-metal hosts.

## Build

```bash
cd execution-engine
cargo build --release
EXEC_ENGINE_VALIDATE_ONLY=1 HDC_MASKS_PATH=config/hdc_masks.example.json cargo run --release
```

AVX-512 popcount: `cargo build --release --features avx512 -C target-cpu=native`

## Config

Copy masks from alpha-swarm:

```bash
cp ../alpha-swarm/output/hdc_masks.json config/hdc_masks.json
```

## Features

| Feature | Purpose |
|---------|---------|
| `avx512` | AVX-512 XOR/popcount on x86_64 |
| `kernel-bypass` | AF_XDP + eBPF (wire on PREEMPT_RT host) |

## Host requirements

PREEMPT_RT kernel, `isolcpus`, hugepages, XDP-capable NIC. See [docs/SOVEREIGN_ARCHITECTURE.md](../docs/SOVEREIGN_ARCHITECTURE.md).
