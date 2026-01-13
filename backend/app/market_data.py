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


class AlphaVantageClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("ALPHAVANTAGE_API_KEY")
        if not self.api_key:
            raise ValueError("ALPHAVANTAGE_API_KEY is not set")

    def fetch_daily_bars(self, symbol: str) -> list[DailyBar]:
        payload = self._request(
            {
                "function": "TIME_SERIES_DAILY_ADJUSTED",
                "symbol": symbol,
                "apikey": self.api_key,
                "outputsize": "compact",
            }
        )
        if self._is_premium_required(payload):
            payload = self._request(
                {
                    "function": "TIME_SERIES_DAILY",
                    "symbol": symbol,
                    "apikey": self.api_key,
                    "outputsize": "compact",
                }
            )

        series = payload.get("Time Series (Daily)")
        if not series:
            raise ValueError(f"Unexpected response for {symbol}: {payload}")

        bars = []
        for date_str, values in series.items():
            bar_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            adjusted = values.get("5. adjusted close")
            volume_key = "6. volume" if "6. volume" in values else "5. volume"
            bars.append(
                DailyBar(
                    bar_date=bar_date,
                    open=float(values["1. open"]),
                    high=float(values["2. high"]),
                    low=float(values["3. low"]),
                    close=float(values["4. close"]),
                    adjusted_close=float(adjusted) if adjusted is not None else None,
                    volume=int(values[volume_key]),
                )
            )

        bars.sort(key=lambda b: b.bar_date)
        return bars

    def fetch_intraday_price(self, symbol: str) -> float:
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": self.api_key,
        }
        payload = self._request(params)
        quote = payload.get("Global Quote")
        if not quote:
            raise ValueError(f"Unexpected response for {symbol}: {payload}")
        return float(quote["05. price"])

    def _request(self, params: dict) -> dict:
        backoff = [5, 15, 30]
        for attempt in range(len(backoff) + 1):
            response = requests.get("https://www.alphavantage.co/query", params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            if self._is_premium_required(payload):
                return payload
            if not self._is_rate_limited(payload):
                return payload
            if attempt < len(backoff):
                time.sleep(backoff[attempt])
        raise ValueError(f"Alpha Vantage rate limit: {payload}")

    def _is_rate_limited(self, payload: dict) -> bool:
        note = payload.get("Note")
        return bool(note)

    def _is_premium_required(self, payload: dict) -> bool:
        info = payload.get("Information", "")
        return "premium" in info.lower()
