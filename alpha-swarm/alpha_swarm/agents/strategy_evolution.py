"""Agent 3 — genetic evolution of HDC binary masks."""

from __future__ import annotations

import random
from typing import Any

import numpy as np

from alpha_swarm.agents.base import Agent
from alpha_swarm.output_schema import HdcMaskOutput, MaskProvenance

HYPERVECTOR_BYTES = 10_000 // 8


class StrategyEvolution(Agent):
    name = "strategy_evolution"

    def run(
        self,
        *,
        features: dict[str, Any],
        population: int = 32,
        generations: int = 10,
    ) -> HdcMaskOutput:
        rng = random.Random(42)
        jitter = float(features.get("jitter_p99_ns", 0.0))
        obi = float(features.get("obi", 0.0))

        def fitness(mask: bytes) -> float:
            density = sum(mask) / (len(mask) * 255)
            return density * 0.4 + min(jitter / 1e9, 1.0) * 0.3 + min(abs(obi), 1.0) * 0.3

        best = rng.randbytes(HYPERVECTOR_BYTES)
        best_score = fitness(best)
        for _ in range(generations):
            pop = [rng.randbytes(HYPERVECTOR_BYTES) for _ in range(population)]
            for candidate in pop:
                score = fitness(candidate)
                if score > best_score:
                    best, best_score = candidate, score
            # mutate elite
            mutant = bytearray(best)
            for i in range(16):
                mutant[rng.randrange(len(mutant))] ^= 1 << rng.randrange(8)
            mutant_score = fitness(bytes(mutant))
            if mutant_score > best_score:
                best, best_score = bytes(mutant), mutant_score

        threshold = float(np.clip(0.55 + best_score * 0.35, 0.5, 0.95))
        return HdcMaskOutput(
            id="evolved-001",
            target_hypervector_mask=best.hex(),
            similarity_threshold=threshold,
            provenance=MaskProvenance(agent=self.name, symbol="BTCUSDT", generation=generations),
        )
