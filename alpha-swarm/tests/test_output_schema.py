from alpha_swarm.output_schema import HdcMaskOutput, SwarmOutputDocument

MASK_HEX = "ab" * 1250


def test_mask_output_roundtrip() -> None:
    doc = SwarmOutputDocument(
        version=1,
        masks=[
            HdcMaskOutput(
                id="t1",
                target_hypervector_mask=MASK_HEX,
                similarity_threshold=0.8,
            )
        ],
    )
    raw = doc.model_dump()
    assert len(raw["masks"][0]["target_hypervector_mask"]) == 2500
