import json
from datetime import date

from app import crud, ingestion, jobs, models


def _create_stock(client):
    response = client.post(
        "/stocks",
        json={
            "ticker": "AAPL",
            "market": "US",
            "currency": "USD",
            "status": "active",
            "position_state": "flat",
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_rule_plan(client, stock_id, payload):
    wrapped = {"version": 1, "is_active": True, "rules": payload}
    response = client.post(f"/stocks/{stock_id}/rule-plans", json=wrapped)
    assert response.status_code == 201
    return response.json()


def test_stock_crud(client):
    stock = _create_stock(client)
    response = client.get(f"/stocks/{stock['id']}")
    assert response.status_code == 200

    response = client.patch(f"/stocks/{stock['id']}", json={"status": "archived"})
    assert response.status_code == 200
    assert response.json()["status"] == "archived"


def test_rule_plan_crud(client, rule_plan_payload):
    stock = _create_stock(client)
    plan = _create_rule_plan(client, stock["id"], rule_plan_payload)
    assert plan["is_active"] is True

    response = client.get(f"/stocks/{stock['id']}/rule-plans")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_rule_plan_validation_error(client, rule_plan_payload):
    stock = _create_stock(client)
    payload = dict(rule_plan_payload)
    payload.pop("ticker", None)
    wrapped = {"version": 1, "is_active": True, "rules": payload}
    response = client.post(f"/stocks/{stock['id']}/rule-plans", json=wrapped)
    assert response.status_code == 422


def test_jobs_flow(db_session, client, rule_plan_payload, daily_bars_payload):
    stock = _create_stock(client)
    _create_rule_plan(client, stock["id"], rule_plan_payload)

    ingestion.upsert_daily_bars(
        db_session,
        stock["id"],
        [
            {
                "bar_date": date.fromisoformat(bar["bar_date"]),
                "open": bar["open"],
                "high": bar["high"],
                "low": bar["low"],
                "close": bar["close"],
                "adjusted_close": bar["adjusted_close"],
                "volume": bar["volume"],
            }
            for bar in daily_bars_payload
        ],
        source="fixture",
    )

    stock_obj = crud.get_stock(db_session, stock["id"])
    jobs.update_indicators(db_session, stock_obj)

    indicators = (
        db_session.query(models.IndicatorValue)
        .filter(models.IndicatorValue.stock_id == stock["id"])
        .all()
    )
    assert indicators

    decision, changed = jobs.evaluate_rules(db_session, stock_obj, "flat")
    assert decision["decision"] in {"ALLOW", "BLOCK"}
    assert isinstance(changed, bool)

    stored = (
        db_session.query(models.DecisionState)
        .filter(models.DecisionState.stock_id == stock["id"])
        .first()
    )
    assert stored is not None
