"""Agent 4 — stress masks under drop/spoof simulation."""

from __future__ import annotations

import random
from typing import Any

from alpha_swarm.agents.base import Agent
from alpha_swarm.output_schema import HdcMaskOutput


class StressTest(Agent):
    name = "stress_test"

    def run(
        self, *, mask: HdcMaskOutput, trials: int = 100, drop_rate: float = 0.05
    ) -> dict[str, Any]:
        rng = random.Random(7)
        raw = bytes.fromhex(mask.target_hypervector_mask)
        passed = 0
        for _ in range(trials):
            corrupted = bytearray(raw)
            if rng.random() < drop_rate:
                corrupted[rng.randrange(len(corrupted))] = 0
            if rng.random() < 0.02:
                # spoof flip burst
                for _ in range(8):
                    corrupted[rng.randrange(len(corrupted))] ^= 0xFF
            distance = sum((a ^ b).bit_count() for a, b in zip(raw, corrupted, strict=True))
            similarity = 1.0 - distance / (len(raw) * 8)
            if similarity >= mask.similarity_threshold * 0.9:
                passed += 1
        return {
            "trials": trials,
            "passed": passed,
            "pass_rate": passed / trials,
            "approved": passed / trials >= 0.8,
        }
