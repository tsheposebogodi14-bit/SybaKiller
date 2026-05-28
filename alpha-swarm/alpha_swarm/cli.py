"""CLI entry — research sandbox only."""

from __future__ import annotations

import argparse
from pathlib import Path

from alpha_swarm.swarm import run_swarm


def main() -> None:
    parser = argparse.ArgumentParser(description="Alpha swarm — HDC mask research")
    parser.add_argument("--pcap", type=Path, default=Path("data/sample.pcap"))
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--output", type=Path, default=Path("output/hdc_masks.json"))
    args = parser.parse_args()

    doc = run_swarm(pcap_path=args.pcap, data_dir=args.data_dir, output_path=args.output)
    print(f"wrote {args.output} ({len(doc.masks)} masks)")


if __name__ == "__main__":
    main()
