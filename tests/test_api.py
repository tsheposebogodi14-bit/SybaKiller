import pytest
from api.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_health() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_kill_blocks_orders() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/kill")
        resp = await client.post(
            "/orders",
            json={"symbol": "BTCUSDT", "side": "buy", "quantity": 0.01, "price": 100.0},
        )
        assert resp.status_code == 400
        await client.post("/kill/release")
