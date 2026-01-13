from typing import Any, Callable

from . import indicator_engine, models
from .series import SeriesAccessor


def build_series_context(
    bars: list[models.DailyBar],
    indicators: list[models.IndicatorDef],
    current_price: float | None = None,
):
    if not bars:
        raise ValueError("No bars available")

    bars_sorted = sorted(bars, key=lambda b: b.bar_date)
    bars_desc = list(reversed(bars_sorted))

    adjusted_close_values = [bar.adjusted_close or bar.close for bar in bars_desc]
    close_series = SeriesAccessor([bar.close for bar in bars_desc])
    adjusted_close_series = SeriesAccessor(adjusted_close_values)
    open_series = SeriesAccessor([bar.open for bar in bars_desc])
    high_series = SeriesAccessor([bar.high for bar in bars_desc])
    low_series = SeriesAccessor([bar.low for bar in bars_desc])
    volume_series = SeriesAccessor([bar.volume for bar in bars_desc])

    context: dict[str, Any] = {
        "Close": close_series,
        "Open": open_series,
        "High": high_series,
        "Low": low_series,
        "Volume": volume_series,
        "price.close": close_series,
        "price.adjusted_close": adjusted_close_series,
        "price.open": open_series,
        "price.high": high_series,
        "price.low": low_series,
        "volume": volume_series,
    }

    if current_price is not None and close_series.values:
        close_series.values[0] = current_price

    for indicator in indicators:
        series_asc = indicator_engine.compute_indicator_series(indicator, bars_sorted)
        series_desc = list(reversed(series_asc))
        context[f"ind.{indicator.indicator_id}"] = SeriesAccessor(series_desc)

    return context


def build_functions(bars: list[models.DailyBar]):
    bars_sorted = sorted(bars, key=lambda b: b.bar_date)

    def sma(period: float):
        return SeriesAccessor(
            list(
                reversed(
                    indicator_engine.compute_sma([bar.close for bar in bars_sorted], int(period))
                )
            )
        )

    def ema(period: float):
        return SeriesAccessor(
            list(
                reversed(
                    indicator_engine.compute_ema([bar.close for bar in bars_sorted], int(period))
                )
            )
        )

    def rsi(period: float):
        return SeriesAccessor(
            list(
                reversed(
                    indicator_engine.compute_rsi([bar.close for bar in bars_sorted], int(period))
                )
            )
        )

    def vwap(period: float):
        prices = [bar.close for bar in bars_sorted]
        volumes = [bar.volume for bar in bars_sorted]
        return SeriesAccessor(
            list(reversed(indicator_engine.compute_vwap(prices, volumes, int(period))))
        )

    def highest(series: SeriesAccessor, period: float):
        values = series.values[: int(period)]
        values = [v for v in values if v is not None]
        return max(values) if values else None

    def lowest(series: SeriesAccessor, period: float):
        values = series.values[: int(period)]
        values = [v for v in values if v is not None]
        return min(values) if values else None

    def change(series: SeriesAccessor):
        if not isinstance(series, SeriesAccessor):
            return None
        current = series.value_at(0)
        previous = series.value_at(1)
        if current is None or previous is None:
            return None
        return current - previous

    def diff(a, b):
        if isinstance(a, SeriesAccessor):
            a = a.value_at(0)
        if isinstance(b, SeriesAccessor):
            b = b.value_at(0)
        if a is None or b is None:
            return None
        return a - b

    return {
        "SMA": sma,
        "EMA": ema,
        "RSI": rsi,
        "VWAP": vwap,
        "highest": highest,
        "lowest": lowest,
        "change": change,
        "diff": diff,
    }
