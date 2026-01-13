import os
import pytest

from app.market_data import AlphaVantageClient


@pytest.mark.skipif(
    not os.getenv("ALPHAVANTAGE_API_KEY"),
    reason="ALPHAVANTAGE_API_KEY not set",
)
def test_live_alphavantage_smoke():
    client = AlphaVantageClient()
    bars = client.fetch_daily_bars("AAPL")
    assert bars
    price = client.fetch_intraday_price("AAPL")
    assert price > 0
