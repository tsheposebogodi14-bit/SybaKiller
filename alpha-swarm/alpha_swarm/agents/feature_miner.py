"""Agent 2 — OBI, VPIN, inter-arrival jitter features."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from alpha_swarm.agents.base import Agent


class FeatureMiner(Agent):
    name = "feature_miner"

    def run(self, *, parquet_path: str, depth: int = 5) -> dict[str, Any]:
        df = pd.read_parquet(parquet_path)
        if df.empty:
            return {"obi": 0.0, "vpin": 0.0, "jitter_p99_ns": 0.0}

        ts = df["ts_ns"].astype(np.int64).to_numpy()
        if len(ts) < 2:
            return {"obi": 0.0, "vpin": 0.0, "jitter_p99_ns": 0.0}

        inter = np.diff(ts)
        jitter_p99 = float(np.percentile(inter, 99))

        # Proxy OBI/VPIN from payload size volatility when book data not parsed yet.
        sizes = df["payload_hex"].str.len().astype(float).to_numpy()
        obi = float((sizes[-depth:].mean() - sizes.mean()) / (sizes.std() + 1e-9))
        vpin = float(np.clip(sizes.std() / (sizes.mean() + 1e-9), 0.0, 1.0))

        summary = self.llm_prompt(
            "llama3.2",
            f"Summarize jitter={jitter_p99:.0f}ns obi={obi:.3f} vpin={vpin:.3f} for temporal arb.",
        )
        return {
            "obi": obi,
            "vpin": vpin,
            "jitter_p99_ns": jitter_p99,
            "llm_summary": summary,
        }
