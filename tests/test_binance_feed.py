from sybakiller.feeds.binance import parse_binance_book_ticker
from sybakiller.types import Symbol


def test_parse_direct_book_ticker() -> None:
    payload = {
        "u": 400900217,
        "s": "BTCUSDT",
        "b": "65000.10",
        "B": "1.5",
        "a": "65000.20",
        "A": "2.0",
    }
    tick = parse_binance_book_ticker(payload)
    assert tick.symbol == Symbol("BTCUSDT")
    assert tick.bid == 65000.10
    assert tick.ask == 65000.20


def test_parse_combined_stream_wrapper() -> None:
    payload = {
        "stream": "ethusdt@bookTicker",
        "data": {
            "u": 1,
            "s": "ETHUSDT",
            "b": "3000.0",
            "B": "1",
            "a": "3000.5",
            "A": "1",
        },
    }
    tick = parse_binance_book_ticker(payload)
    assert str(tick.symbol) == "ETHUSDT"
    assert tick.ask > tick.bid
