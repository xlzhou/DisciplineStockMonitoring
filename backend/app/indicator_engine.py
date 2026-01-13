from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

from sqlalchemy.orm import Session

from . import models


@dataclass
class IndicatorResult:
    as_of_date: date
    value: float | None
    status: str
    lookback_used: int


def compute_sma(values: list[float], period: int) -> list[float | None]:
    if period <= 0:
        return [None] * len(values)
    sma = []
    window_sum = 0.0
    for idx, value in enumerate(values):
        window_sum += value
        if idx >= period:
            window_sum -= values[idx - period]
        if idx + 1 < period:
            sma.append(None)
        else:
            sma.append(window_sum / period)
    return sma


def compute_ema(values: list[float], period: int) -> list[float | None]:
    if period <= 0:
        return [None] * len(values)
    ema: list[float | None] = [None] * len(values)
    if len(values) < period:
        return ema

    sma_start = sum(values[:period]) / period
    multiplier = 2 / (period + 1)
    ema[period - 1] = sma_start
    for idx in range(period, len(values)):
        prev = ema[idx - 1]
        if prev is None:
            prev = values[idx - 1]
        ema[idx] = (values[idx] - prev) * multiplier + prev
    return ema


def compute_rsi(values: list[float], period: int) -> list[float | None]:
    if period <= 0:
        return [None] * len(values)
    rsi: list[float | None] = [None] * len(values)
    if len(values) <= period:
        return rsi

    gains = []
    losses = []
    for idx in range(1, period + 1):
        change = values[idx] - values[idx - 1]
        gains.append(max(change, 0))
        losses.append(abs(min(change, 0)))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        rsi[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100 - (100 / (1 + rs))

    for idx in range(period + 1, len(values)):
        change = values[idx] - values[idx - 1]
        gain = max(change, 0)
        loss = abs(min(change, 0))
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0:
            rsi[idx] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[idx] = 100 - (100 / (1 + rs))

    return rsi


def compute_vwap(prices: list[float], volumes: list[int], period: int) -> list[float | None]:
    if period <= 0:
        return [None] * len(prices)
    if len(prices) != len(volumes):
        raise ValueError("Prices and volumes length mismatch")

    vwap: list[float | None] = []
    for idx in range(len(prices)):
        if idx + 1 < period:
            vwap.append(None)
            continue
        price_slice = prices[idx + 1 - period : idx + 1]
        volume_slice = volumes[idx + 1 - period : idx + 1]
        total_volume = sum(volume_slice)
        if total_volume == 0:
            vwap.append(None)
        else:
            weighted_sum = sum(p * v for p, v in zip(price_slice, volume_slice))
            vwap.append(weighted_sum / total_volume)
    return vwap


def compute_indicator_series(indicator: models.IndicatorDef, bars: list[models.DailyBar]):
    if indicator.price_field == "adjusted_close":
        closes = [bar.adjusted_close or bar.close for bar in bars]
    else:
        closes = [bar.close for bar in bars]
    volumes = [bar.volume for bar in bars]
    params = json_loads(indicator.params_json)
    period = int(params.get("period", 0))

    if indicator.indicator_type == "MA":
        ma_type = params.get("ma_type", "SMA")
        if ma_type == "EMA":
            return compute_ema(closes, period)
        return compute_sma(closes, period)

    if indicator.indicator_type == "RSI":
        return compute_rsi(closes, period)

    if indicator.indicator_type == "VWAP":
        return compute_vwap(closes, volumes, period)

    raise ValueError(f"Unsupported indicator type: {indicator.indicator_type}")


def upsert_indicator_value(
    db: Session,
    indicator: models.IndicatorDef,
    bar: models.DailyBar,
    value: float | None,
    status: str,
    lookback: int,
    source: str,
):
    existing = (
        db.query(models.IndicatorValue)
        .filter(
            models.IndicatorValue.stock_id == indicator.stock_id,
            models.IndicatorValue.indicator_id == indicator.indicator_id,
            models.IndicatorValue.as_of_date == bar.bar_date,
        )
        .first()
    )
    if existing:
        existing.value = value
        existing.status = status
        existing.lookback_used = lookback
        existing.computed_at = datetime.utcnow()
        existing.source = source
        return existing

    record = models.IndicatorValue(
        stock_id=indicator.stock_id,
        indicator_id=indicator.indicator_id,
        as_of_date=bar.bar_date,
        value=value,
        status=status,
        lookback_used=lookback,
        computed_at=datetime.utcnow(),
        source=source,
    )
    db.add(record)
    return record


def compute_indicators_for_stock(db: Session, stock_id: int, source: str = "local"):
    bars = (
        db.query(models.DailyBar)
        .filter(models.DailyBar.stock_id == stock_id)
        .order_by(models.DailyBar.bar_date)
        .all()
    )
    if not bars:
        return

    indicators = (
        db.query(models.IndicatorDef)
        .filter(models.IndicatorDef.stock_id == stock_id)
        .all()
    )
    if not indicators:
        return

    latest_bar = bars[-1]

    for indicator in indicators:
        series = compute_indicator_series(indicator, bars)
        value = series[-1]
        params = json_loads(indicator.params_json)
        lookback = int(params.get("period", 0))

        if value is None:
            status = "INSUFFICIENT_HISTORY"
        else:
            status = "OK"

        upsert_indicator_value(
            db=db,
            indicator=indicator,
            bar=latest_bar,
            value=value,
            status=status,
            lookback=lookback,
            source=source,
        )

    db.commit()


def json_loads(payload: str) -> dict:
    import json

    return json.loads(payload)
