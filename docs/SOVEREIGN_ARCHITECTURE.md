# Sovereign HFT Architecture

SybaKiller / Project Oodi is split into **three layers** with hard boundaries:

```
┌─────────────────────────────────────────────────────────────┐
│  alpha-swarm/          Python research (The Sandbox)        │
│  PCAP → Parquet → OBI/VPIN → GA masks → hdc_masks.json    │
└──────────────────────────────┬──────────────────────────────┘
                               │ JSON masks only
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  execution-engine/     Rust bare-metal (The Weapon)         │
│  AF_XDP → HDC SIMD → FIX → NIC TX                           │
└──────────────────────────────┬──────────────────────────────┘
                               │ optional status
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  sybakiller/ + api/    Control plane (admin, testnet REST)  │
└─────────────────────────────────────────────────────────────┘
```

## Directories

| Path | Purpose |
|------|---------|
| `execution-engine/` | Ultra-low-latency Rust engine |
| `alpha-swarm/` | Multi-agent quant research swarm |
| `sybakiller/` | Existing Python stack (control plane) |

## Boot order (production)

1. `alpha-swarm` produces verified `output/hdc_masks.json`.
2. Copy masks to execution host: `execution-engine/config/hdc_masks.json`.
3. Start `execution-engine` on PREEMPT_RT host with isolated CPUs.
4. Optionally start `make api` for monitoring only.

## Kernel / hardware prerequisites (execution host)

- PREEMPT_RT kernel
- CPU isolation (`isolcpus`, `nohz_full`)
- NIC with XDP support, hugepages for UMEM
- See `execution-engine/README.md`
