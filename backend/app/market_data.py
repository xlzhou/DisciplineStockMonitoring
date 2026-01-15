import os
import time
from dataclasses import dataclass
from datetime import date, datetime

import requests


@dataclass
class DailyBar:
    bar_date: date
    open: float
    high: float
    low: float
    close: float
    adjusted_close: float | None
    volume: int


_GLOBAL_PRICE_CACHE: dict[str, tuple[float, float]] = {}


class TwelveDataClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("TWELVEDATA_API_KEY")
        if not self.api_key:
            raise ValueError("TWELVEDATA_API_KEY is not set")
        self._price_cache: dict[str, tuple[float, float]] = {}

    def fetch_daily_bars(self, symbol: str) -> list[DailyBar]:
        payload = self._request(
            {
                "symbol": symbol,
                "interval": "1day",
                "apikey": self.api_key,
                "outputsize": 100,
            },
            endpoint="time_series",
        )

        values = payload.get("values")
        if not values:
            raise ValueError(f"Unexpected response for {symbol}: {payload}")

        bars = []
        for row in values:
            bar_date = datetime.strptime(row["datetime"], "%Y-%m-%d").date()
            bars.append(
                DailyBar(
                    bar_date=bar_date,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    adjusted_close=None,
                    volume=int(row["volume"]),
                )
            )

        bars.sort(key=lambda b: b.bar_date)
        return bars

    def fetch_intraday_price(self, symbol: str) -> float:
        payload = self._request(
            {
                "symbol": symbol,
                "apikey": self.api_key,
            },
            endpoint="quote",
        )
        price = payload.get("close")
        if price is None:
            raise ValueError(f"Unexpected response for {symbol}: {payload}")
        return float(price)

    def fetch_intraday_price_cached(self, symbol: str, ttl_seconds: int = 60) -> float:
        now = time.time()
        cached = _GLOBAL_PRICE_CACHE.get(symbol)
        if cached and now - cached[0] < ttl_seconds:
            return cached[1]

        price = self.fetch_intraday_price(symbol)
        _GLOBAL_PRICE_CACHE[symbol] = (now, price)
        return price

    def _request(self, params: dict, endpoint: str = "quote") -> dict:
        backoff = [5, 15, 30]
        for attempt in range(len(backoff) + 1):
            response = requests.get(
                f"https://api.twelvedata.com/{endpoint}",
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            if not self._is_rate_limited(payload):
                return payload
            if attempt < len(backoff):
                time.sleep(backoff[attempt])
        raise ValueError(f"Twelve Data rate limit: {payload}")

    def _is_rate_limited(self, payload: dict) -> bool:
        if payload.get("status") == "error":
            code = str(payload.get("code", ""))
            message = str(payload.get("message", "")).lower()
            return code == "429" or "limit" in message
        return False


def get_cached_price(symbol: str, ttl_seconds: int = 60) -> float | None:
    now = time.time()
    cached = _GLOBAL_PRICE_CACHE.get(symbol)
    if cached and now - cached[0] < ttl_seconds:
        return cached[1]
    return None


def set_cached_price(symbol: str, price: float):
    _GLOBAL_PRICE_CACHE[symbol] = (time.time(), price)
