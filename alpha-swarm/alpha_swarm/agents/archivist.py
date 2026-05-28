"""Agent 1 — PCAP ingest, repair drops, Parquet archive."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from alpha_swarm.agents.base import Agent


class DataArchivist(Agent):
    name = "data_archivist"

    def run(self, *, pcap_path: Path, out_parquet: Path) -> dict[str, Any]:
        out_parquet.parent.mkdir(parents=True, exist_ok=True)
        if not pcap_path.exists():
            # Scaffold path: empty frame until scapy extra is installed on host.
            frame = pd.DataFrame(columns=["ts_ns", "src_mac", "dst_mac", "eth_type", "payload_hex"])
            frame.to_parquet(out_parquet, index=False)
            return {"rows": 0, "parquet": str(out_parquet), "note": "pcap missing — empty archive"}

        try:
            from scapy.all import rdpcap  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError("install alpha-swarm[pcap] for PCAP ingest") from exc

        packets = rdpcap(str(pcap_path))
        rows: list[dict[str, Any]] = []
        for pkt in packets:
            rows.append(
                {
                    "ts_ns": int(float(pkt.time) * 1e9),
                    "src_mac": pkt[0].src if pkt.haslayer(0) else "",
                    "dst_mac": pkt[0].dst if pkt.haslayer(0) else "",
                    "eth_type": int(pkt[0].type) if pkt.haslayer(0) else 0,
                    "payload_hex": bytes(pkt).hex(),
                }
            )
        frame = pd.DataFrame(rows)
        frame.to_parquet(out_parquet, index=False)
        return {"rows": len(frame), "parquet": str(out_parquet)}
