import json
from datetime import datetime
from sqlalchemy.orm import Session

from . import models, schemas


def get_stock(db: Session, stock_id: int):
    return db.query(models.Stock).filter(models.Stock.id == stock_id).first()


def list_stocks(db: Session):
    return db.query(models.Stock).order_by(models.Stock.ticker).all()


def create_stock(db: Session, stock_in: schemas.StockCreate):
    existing = db.query(models.Stock).filter(models.Stock.ticker == stock_in.ticker).first()
    if existing:
        data = stock_in.model_dump()
        for key, value in data.items():
            setattr(existing, key, value)
        existing.status = "active"
        db.commit()
        db.refresh(existing)
        return existing

    stock = models.Stock(**stock_in.model_dump())
    db.add(stock)
    db.commit()
    db.refresh(stock)
    return stock


def update_stock(db: Session, stock: models.Stock, stock_in: schemas.StockUpdate):
    data = stock_in.model_dump(exclude_unset=True)
    if "position_qty" in data:
        qty = data.get("position_qty")
        if qty is not None:
            data["position_state"] = "holding" if qty > 0 else "flat"
    for key, value in data.items():
        setattr(stock, key, value)
    db.commit()
    db.refresh(stock)
    return stock


def upsert_device(db: Session, device_in: schemas.DeviceCreate):
    existing = (
        db.query(models.Device)
        .filter(models.Device.apns_token == device_in.apns_token)
        .first()
    )
    if existing:
        existing.platform = device_in.platform
        existing.is_active = device_in.is_active
        existing.last_seen_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    device = models.Device(
        apns_token=device_in.apns_token,
        platform=device_in.platform,
        is_active=device_in.is_active,
        last_seen_at=datetime.utcnow(),
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def list_devices(db: Session):
    return db.query(models.Device).order_by(models.Device.last_seen_at.desc()).all()


def deactivate_device(db: Session, token: str):
    device = db.query(models.Device).filter(models.Device.apns_token == token).first()
    if not device:
        return None
    device.is_active = False
    device.last_seen_at = datetime.utcnow()
    db.commit()
    db.refresh(device)
    return device


def list_rule_plans(db: Session, stock_id: int):
    return (
        db.query(models.RulePlan)
        .filter(models.RulePlan.stock_id == stock_id)
        .order_by(models.RulePlan.version.desc())
        .all()
    )


def get_active_rule_plan(db: Session, stock_id: int):
    return (
        db.query(models.RulePlan)
        .filter(models.RulePlan.stock_id == stock_id, models.RulePlan.is_active.is_(True))
        .first()
    )


def get_rule_plan(db: Session, rule_plan_id: int):
    return db.query(models.RulePlan).filter(models.RulePlan.id == rule_plan_id).first()


def create_rule_plan(db: Session, stock: models.Stock, plan_in: schemas.RulePlanCreate):
    if plan_in.is_active:
        (
            db.query(models.RulePlan)
            .filter(models.RulePlan.stock_id == stock.id, models.RulePlan.is_active.is_(True))
            .update({"is_active": False})
        )

    plan = models.RulePlan(
        stock_id=stock.id,
        version=plan_in.version,
        is_active=plan_in.is_active,
        rules_json=json.dumps(plan_in.rules),
        notes=plan_in.notes,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    sync_indicator_defs(db, stock, plan)
    return plan


def update_rule_plan(db: Session, plan: models.RulePlan, plan_in: schemas.RulePlanUpdate):
    data = plan_in.model_dump(exclude_unset=True)
    if "is_active" in data and data["is_active"] is True:
        (
            db.query(models.RulePlan)
            .filter(
                models.RulePlan.stock_id == plan.stock_id,
                models.RulePlan.is_active.is_(True),
                models.RulePlan.id != plan.id,
            )
            .update({"is_active": False})
        )

    for key, value in data.items():
        setattr(plan, key, value)

    db.commit()
    db.refresh(plan)
    return plan


def serialize_rule_plan(plan: models.RulePlan) -> schemas.RulePlanOut:
    payload = json.loads(plan.rules_json)
    return schemas.RulePlanOut(
        id=plan.id,
        stock_id=plan.stock_id,
        version=plan.version,
        is_active=plan.is_active,
        rules=payload,
        notes=plan.notes,
        created_at=plan.created_at,
    )


def upsert_decision_state(db: Session, stock_id: int, state_key: str, decision_json: str) -> bool:
    existing = (
        db.query(models.DecisionState).filter(models.DecisionState.stock_id == stock_id).first()
    )
    if existing:
        changed = existing.state_key != state_key
        existing.state_key = state_key
        existing.decision_json = decision_json
        return changed

    record = models.DecisionState(
        stock_id=stock_id,
        state_key=state_key,
        decision_json=decision_json,
    )
    db.add(record)
    return True


def sync_indicator_defs(db: Session, stock: models.Stock, plan: models.RulePlan):
    rules = json.loads(plan.rules_json)
    indicator_policy = rules.get("indicator_policy", {})
    indicators = rules.get("indicators", [])

    for indicator in indicators:
        params = indicator.copy()
        indicator_id = params.pop("id", "")
        indicator_type = params.pop("type", "")
        if not indicator_id or not indicator_type:
            continue

        existing = (
            db.query(models.IndicatorDef)
            .filter(
                models.IndicatorDef.stock_id == stock.id,
                models.IndicatorDef.rule_plan_id == plan.id,
                models.IndicatorDef.indicator_id == indicator_id,
            )
            .first()
        )
        if existing:
            existing.indicator_type = indicator_type
            existing.params_json = json.dumps(params)
            existing.timeframe = indicator_policy.get("timeframe", "1D")
            existing.price_field = indicator_policy.get("price_field", "close")
            existing.use_eod_only = indicator_policy.get("use_eod_only", True)
            continue

        record = models.IndicatorDef(
            stock_id=stock.id,
            rule_plan_id=plan.id,
            indicator_id=indicator_id,
            indicator_type=indicator_type,
            params_json=json.dumps(params),
            timeframe=indicator_policy.get("timeframe", "1D"),
            price_field=indicator_policy.get("price_field", "close"),
            use_eod_only=indicator_policy.get("use_eod_only", True),
        )
        db.add(record)

    db.commit()
