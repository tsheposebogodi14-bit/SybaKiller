"""Strict JSON contract handed to execution-engine."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

HYPERVECTOR_BITS = 10_000
HYPERVECTOR_HEX_LEN = (HYPERVECTOR_BITS // 8) * 2


class MaskProvenance(BaseModel):
    agent: str
    symbol: str = "BTCUSDT"
    generation: int = 0


class HdcMaskOutput(BaseModel):
    id: str
    target_hypervector_mask: str = Field(description="hex-encoded 10000-bit vector")
    similarity_threshold: float = Field(ge=0.0, le=1.0)
    provenance: MaskProvenance | None = None

    @field_validator("target_hypervector_mask")
    @classmethod
    def _hex_len(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if len(cleaned) != HYPERVECTOR_HEX_LEN:
            raise ValueError(
                f"mask hex must be {HYPERVECTOR_HEX_LEN} chars ({HYPERVECTOR_BITS} bits)"
            )
        int(cleaned, 16)
        return cleaned


class SwarmOutputDocument(BaseModel):
    version: int = 1
    masks: list[HdcMaskOutput]
