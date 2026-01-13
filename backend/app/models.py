from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .db import Base


class Stock(Base):
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticker: Mapped[str] = mapped_column(String, unique=True, index=True)
    market: Mapped[str] = mapped_column(String)
    currency: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="active")
    position_state: Mapped[str] = mapped_column(String, default="flat")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    rule_plans = relationship("RulePlan", back_populates="stock")
    daily_bars = relationship("DailyBar", back_populates="stock")
    indicator_defs = relationship("IndicatorDef", back_populates="stock")
    indicator_values = relationship("IndicatorValue", back_populates="stock")
    decision_state = relationship("DecisionState", back_populates="stock", uselist=False)


class RulePlan(Base):
    __tablename__ = "rule_plans"
    __table_args__ = (UniqueConstraint("stock_id", "version", name="uq_rule_plans_stock_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    stock_id: Mapped[int] = mapped_column(Integer, ForeignKey("stocks.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    rules_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    stock = relationship("Stock", back_populates="rule_plans")


class DailyBar(Base):
    __tablename__ = "daily_bars"
    __table_args__ = (UniqueConstraint("stock_id", "bar_date", name="uq_daily_bars_stock_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    stock_id: Mapped[int] = mapped_column(Integer, ForeignKey("stocks.id"), index=True)
    bar_date: Mapped[datetime] = mapped_column(Date)
    open: Mapped[float] = mapped_column()
    high: Mapped[float] = mapped_column()
    low: Mapped[float] = mapped_column()
    close: Mapped[float] = mapped_column()
    adjusted_close: Mapped[float] = mapped_column(nullable=True)
    volume: Mapped[int] = mapped_column()
    source: Mapped[str] = mapped_column(String)

    stock = relationship("Stock", back_populates="daily_bars")


class IndicatorDef(Base):
    __tablename__ = "indicator_defs"
    __table_args__ = (
        UniqueConstraint(
            "stock_id",
            "rule_plan_id",
            "indicator_id",
            name="uq_indicator_defs_stock_plan_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    stock_id: Mapped[int] = mapped_column(Integer, ForeignKey("stocks.id"), index=True)
    rule_plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("rule_plans.id"), index=True)
    indicator_id: Mapped[str] = mapped_column(String)
    indicator_type: Mapped[str] = mapped_column(String)
    params_json: Mapped[str] = mapped_column(Text)
    timeframe: Mapped[str] = mapped_column(String)
    price_field: Mapped[str] = mapped_column(String)
    use_eod_only: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    stock = relationship("Stock", back_populates="indicator_defs")
    rule_plan = relationship("RulePlan")


class IndicatorValue(Base):
    __tablename__ = "indicator_values"
    __table_args__ = (
        UniqueConstraint(
            "stock_id",
            "indicator_id",
            "as_of_date",
            name="uq_indicator_values_stock_id_date",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    stock_id: Mapped[int] = mapped_column(Integer, ForeignKey("stocks.id"), index=True)
    indicator_id: Mapped[str] = mapped_column(String)
    as_of_date: Mapped[datetime] = mapped_column(Date)
    value: Mapped[float] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String)
    lookback_used: Mapped[int] = mapped_column(Integer)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    source: Mapped[str] = mapped_column(String)

    stock = relationship("Stock", back_populates="indicator_values")


class DecisionState(Base):
    __tablename__ = "decision_states"
    __table_args__ = (UniqueConstraint("stock_id", name="uq_decision_states_stock"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    stock_id: Mapped[int] = mapped_column(Integer, ForeignKey("stocks.id"), index=True)
    state_key: Mapped[str] = mapped_column(String)
    decision_json: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    stock = relationship("Stock", back_populates="decision_state")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    stock_id: Mapped[int] = mapped_column(Integer, ForeignKey("stocks.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String)
    payload_json: Mapped[str] = mapped_column(Text)


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (UniqueConstraint("apns_token", name="uq_devices_token"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    apns_token: Mapped[str] = mapped_column(String)
    platform: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
