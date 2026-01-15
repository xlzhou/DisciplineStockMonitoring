import os
import pytest

from app.config import load_env
from app.market_data import TwelveDataClient

load_env()


@pytest.mark.skipif(
    not os.getenv("TWELVEDATA_API_KEY"),
    reason="TWELVEDATA_API_KEY not set",
)
def test_live_twelvedata_smoke():
    client = TwelveDataClient()
    bars = client.fetch_daily_bars("AAPL")
    assert bars
    price = client.fetch_intraday_price("AAPL")
    assert price > 0
