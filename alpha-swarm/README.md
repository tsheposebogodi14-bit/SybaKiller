# alpha-swarm (The Sandbox)

Python research swarm — **never** places live orders. Outputs `output/hdc_masks.json` for `execution-engine/`.

## Install

```bash
cd alpha-swarm
uv sync --extra dev
```

## Run pipeline

```bash
uv run alpha-swarm --pcap data/sample.pcap --output output/hdc_masks.json
```

Requires local [Ollama](https://ollama.com) only for optional LLM summaries (pipeline runs without it).

## Agents

| Agent | Role |
|-------|------|
| Data Archivist | PCAP → Parquet |
| Feature Miner | OBI, VPIN, jitter |
| Strategy Evolution | GA → 10k-bit mask |
| Stress-Test | drop/spoof simulation |

## Handoff

```bash
cp output/hdc_masks.json ../execution-engine/config/hdc_masks.json
cd ../execution-engine && EXEC_ENGINE_VALIDATE_ONLY=1 cargo run --release
```
