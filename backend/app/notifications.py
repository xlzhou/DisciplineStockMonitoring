import os

from sqlalchemy.orm import Session

from . import ingestion, models


def _apns_settings():
    return {
        "auth_key": os.getenv("APNS_AUTH_KEY"),
        "key_id": os.getenv("APNS_KEY_ID"),
        "team_id": os.getenv("APNS_TEAM_ID"),
        "topic": os.getenv("APNS_TOPIC"),
        "use_sandbox": os.getenv("APNS_USE_SANDBOX", "true").lower() == "true",
    }


def _build_payload(decision_payload: dict):
    from apns2.payload import Payload

    decision = decision_payload.get("decision")
    action = decision_payload.get("action")
    reasons = decision_payload.get("reasons", [])
    reason_text = reasons[0].get("message") if reasons else None
    title = f"{decision} {action}" if action and action != "NONE" else decision
    body = reason_text or "Decision state changed."
    return Payload(alert={"title": title, "body": body}, sound="default", badge=1)


def send_decision_change(db: Session, stock: models.Stock, decision_payload: dict):
    settings = _apns_settings()
    if not all([settings["auth_key"], settings["key_id"], settings["team_id"], settings["topic"]]):
        ingestion.record_audit(
            db,
            stock.id,
            "APNS_SKIPPED",
            {"reason": "missing_credentials"},
        )
        return

    from apns2.client import APNsClient

    devices = (
        db.query(models.Device).filter(models.Device.is_active.is_(True)).all()
    )
    if not devices:
        return

    payload = _build_payload(decision_payload)

    with APNsClient(
        settings["auth_key"],
        use_sandbox=settings["use_sandbox"],
        team_id=settings["team_id"],
        key_id=settings["key_id"],
    ) as client:
        for device in devices:
            try:
                client.send_notification(device.apns_token, payload, settings["topic"])
            except Exception as exc:  # noqa: BLE001
                ingestion.record_audit(
                    db,
                    stock.id,
                    "APNS_ERROR",
                    {"token": device.apns_token, "error": str(exc)},
                )
                continue

    ingestion.record_audit(
        db,
        stock.id,
        "APNS_SENT",
        {"device_count": len(devices)},
    )
