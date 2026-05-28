from sybakiller.exchanges.filters import SymbolFilters, parse_symbol_filters


def _sol_filters() -> SymbolFilters:
    payload = {
        "symbol": "SOLUSDT",
        "filters": [
            {
                "filterType": "PRICE_FILTER",
                "minPrice": "0.01000000",
                "maxPrice": "100000",
                "tickSize": "0.01000000",
            },
            {
                "filterType": "LOT_SIZE",
                "minQty": "0.00100000",
                "maxQty": "9000000",
                "stepSize": "0.00100000",
            },
            {"filterType": "NOTIONAL", "minNotional": "5.00000000"},
            {
                "filterType": "PERCENT_PRICE_BY_SIDE",
                "bidMultiplierUp": "1.2",
                "bidMultiplierDown": "0.8",
                "askMultiplierUp": "1.2",
                "askMultiplierDown": "0.8",
            },
        ],
    }
    return parse_symbol_filters("SOLUSDT", payload)


def test_notional_rejected() -> None:
    rules = _sol_filters()
    err = rules.validate_limit_order(
        side="buy", quantity=0.01, price=1.0, ref_bid=80.0, ref_ask=80.1
    )
    assert err is not None
    assert "notional" in err


def test_valid_limit_passes() -> None:
    rules = _sol_filters()
    err = rules.validate_limit_order(
        side="buy", quantity=0.1, price=75.0, ref_bid=80.0, ref_ask=80.1
    )
    assert err is None
