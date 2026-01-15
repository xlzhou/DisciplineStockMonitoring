from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class StockBase(BaseModel):
    ticker: str = Field(min_length=1)
    market: str
    currency: str
    status: str = "active"
    position_state: str = "flat"
    avg_entry_price: Optional[float] = None
    position_qty: Optional[int] = None


class StockCreate(StockBase):
    pass


class StockUpdate(BaseModel):
    market: Optional[str] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    position_state: Optional[str] = None
    avg_entry_price: Optional[float] = None
    position_qty: Optional[int] = None


class StockOut(StockBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class StockPriceOut(StockOut):
    price: float | None = None


class StockPriceOnly(BaseModel):
    id: int
    ticker: str
    price: float | None


class RulePlanBase(BaseModel):
    version: int
    is_active: bool = True
    rules: dict[str, Any]
    notes: Optional[str] = None


class RulePlanCreate(RulePlanBase):
    pass


class RulePlanUpdate(BaseModel):
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class RulePlanOut(RulePlanBase):
    id: int
    stock_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DeviceBase(BaseModel):
    apns_token: str = Field(min_length=1)
    platform: str = "ios"
    is_active: bool = True


class DeviceCreate(DeviceBase):
    pass


class DeviceOut(DeviceBase):
    id: int
    last_seen_at: datetime

    model_config = {"from_attributes": True}
