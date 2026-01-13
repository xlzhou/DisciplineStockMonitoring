from datetime import datetime

from sqlalchemy.orm import Session

from . import models


def upsert_daily_bars(db: Session, stock_id: int, bars: list[dict], source: str):
    for bar in bars:
        existing = (
            db.query(models.DailyBar)
            .filter(
                models.DailyBar.stock_id == stock_id,
                models.DailyBar.bar_date == bar["bar_date"],
            )
            .first()
        )
        if existing:
            existing.open = bar["open"]
            existing.high = bar["high"]
            existing.low = bar["low"]
            existing.close = bar["close"]
            existing.adjusted_close = bar.get("adjusted_close")
            existing.volume = bar["volume"]
            existing.source = source
            continue

        record = models.DailyBar(
            stock_id=stock_id,
            bar_date=bar["bar_date"],
            open=bar["open"],
            high=bar["high"],
            low=bar["low"],
            close=bar["close"],
            adjusted_close=bar.get("adjusted_close"),
            volume=bar["volume"],
            source=source,
        )
        db.add(record)

    db.commit()


def record_audit(db: Session, stock_id: int | None, event_type: str, payload: dict):
    record = models.AuditLog(
        timestamp=datetime.utcnow(),
        stock_id=stock_id,
        event_type=event_type,
        payload_json=json_dumps(payload),
    )
    db.add(record)
    db.commit()


def json_dumps(payload: dict) -> str:
    import json

    return json.dumps(payload)
