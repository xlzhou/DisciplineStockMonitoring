import json

from sqlalchemy.orm import Session

from . import crud, indicator_engine, ingestion, models, notifications, rule_engine
from .market_data import TwelveDataClient


def ingest_daily_bars(db: Session, stock: models.Stock, client: TwelveDataClient):
    bars = client.fetch_daily_bars(stock.ticker)
    payload = [
        {
            "bar_date": bar.bar_date,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "adjusted_close": bar.adjusted_close,
            "volume": bar.volume,
        }
        for bar in bars
    ]
    ingestion.upsert_daily_bars(db, stock.id, payload, source="alphavantage")
    ingestion.record_audit(
        db,
        stock.id,
        "DAILY_BARS_INGESTED",
        {"count": len(payload)},
    )


def update_indicators(db: Session, stock: models.Stock):
    indicator_engine.compute_indicators_for_stock(db, stock.id, source="computed")
    ingestion.record_audit(
        db,
        stock.id,
        "INDICATORS_COMPUTED",
        {"stock_id": stock.id},
    )


def evaluate_rules(
    db: Session,
    stock: models.Stock,
    position_state: str,
    current_price: float | None = None,
):
    plan = crud.get_active_rule_plan(db, stock.id)
    if not plan:
        raise ValueError("No active rule plan")

    bars = (
        db.query(models.DailyBar)
        .filter(models.DailyBar.stock_id == stock.id)
        .order_by(models.DailyBar.bar_date)
        .all()
    )
    if not bars:
        raise ValueError("No daily bars available")

    indicators = (
        db.query(models.IndicatorDef)
        .filter(models.IndicatorDef.stock_id == stock.id, models.IndicatorDef.rule_plan_id == plan.id)
        .all()
    )

    rule_plan = json.loads(plan.rules_json)
    result = rule_engine.evaluate_with_bars(
        rule_plan,
        bars,
        indicators,
        position_state,
        current_price=current_price,
    )

    decision_payload = {
        "decision": result.decision,
        "action": result.action,
        "state_key": result.state_key,
        "reasons": result.reasons,
    }
    changed = crud.upsert_decision_state(
        db, stock.id, result.state_key, json.dumps(decision_payload)
    )
    db.commit()

    ingestion.record_audit(
        db,
        stock.id,
        "RULE_EVALUATED",
        decision_payload,
    )

    if changed:
        notifications.send_decision_change(db, stock, decision_payload)

    return decision_payload, changed


def market_monitor(db: Session, stock: models.Stock, client: TwelveDataClient, position_state: str):
    price = client.fetch_intraday_price(stock.ticker)
    ingestion.record_audit(
        db,
        stock.id,
        "INTRADAY_PRICE_FETCHED",
        {"price": price},
    )
    decision_payload, changed = evaluate_rules(
        db,
        stock,
        position_state,
        current_price=price,
    )
    return decision_payload, changed
