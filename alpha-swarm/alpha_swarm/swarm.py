"""Orchestrate agents and write execution-engine JSON."""

from __future__ import annotations

import json
from pathlib import Path

from alpha_swarm.agents import DataArchivist, FeatureMiner, StrategyEvolution, StressTest
from alpha_swarm.output_schema import SwarmOutputDocument


def run_swarm(
    *,
    pcap_path: Path,
    data_dir: Path,
    output_path: Path,
) -> SwarmOutputDocument:
    data_dir.mkdir(parents=True, exist_ok=True)
    parquet = data_dir / "archive.parquet"

    archivist = DataArchivist()
    archivist.run(pcap_path=pcap_path, out_parquet=parquet)

    miner = FeatureMiner()
    features = miner.run(parquet_path=str(parquet))

    evolution = StrategyEvolution()
    mask = evolution.run(features=features)

    stress = StressTest()
    report = stress.run(mask=mask)
    if not report["approved"]:
        raise RuntimeError(f"stress test failed: {report}")

    doc = SwarmOutputDocument(version=1, masks=[mask])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(doc.model_dump(), indent=2), encoding="utf-8")
    return doc
