from app import crud
from app.schemas import DeviceCreate


def test_device_registration(db_session):
    device = crud.upsert_device(
        db_session,
        DeviceCreate(apns_token="token-1", platform="ios", is_active=True),
    )
    assert device.apns_token == "token-1"

    device = crud.upsert_device(
        db_session,
        DeviceCreate(apns_token="token-1", platform="ios", is_active=False),
    )
    assert device.is_active is False

    devices = crud.list_devices(db_session)
    assert len(devices) == 1

    deactivated = crud.deactivate_device(db_session, "token-1")
    assert deactivated is not None
    assert deactivated.is_active is False
