import os
from datetime import datetime, time
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from .db import SessionLocal
from .jobs import ingest_daily_bars, market_monitor, update_indicators
from .market_calendar import load_holidays
from .market_data import AlphaVantageClient
from .models import Stock


def _market_interval_minutes() -> int:
    return int(os.getenv("MARKET_MONITOR_MINUTES", "15"))


def _daily_job_time() -> time:
    raw = os.getenv("DAILY_JOB_TIME", "21:00")
    hour_str, minute_str = raw.split(":")
    return time(hour=int(hour_str), minute=int(minute_str))

def _market_timezone() -> ZoneInfo:
    return ZoneInfo(os.getenv("MARKET_TZ", "America/New_York"))


def _holiday_dates() -> set[str]:
    raw = os.getenv("MARKET_HOLIDAYS", "")
    file_path = os.getenv("MARKET_CALENDAR_PATH")
    holidays = {item.strip() for item in raw.split(",") if item.strip()}
    if file_path:
        holidays.update(load_holidays(file_path))
    return holidays


def is_trading_day(now: datetime) -> bool:
    if now.weekday() >= 5:
        return False
    if now.strftime("%Y-%m-%d") in _holiday_dates():
        return False
    return True


def run_market_monitor():
    now = datetime.now(_market_timezone())
    if not is_trading_day(now):
        return
    client = AlphaVantageClient()
    with SessionLocal() as db:
        stocks = db.query(Stock).filter(Stock.status == "active").all()
        for stock in stocks:
            market_monitor(db, stock, client, position_state=stock.position_state)


def run_daily_job():
    now = datetime.now(_market_timezone())
    if not is_trading_day(now):
        return
    client = AlphaVantageClient()
    with SessionLocal() as db:
        stocks = db.query(Stock).filter(Stock.status == "active").all()
        for stock in stocks:
            ingest_daily_bars(db, stock, client)
            update_indicators(db, stock)
            market_monitor(db, stock, client, position_state=stock.position_state)


def start_scheduler():
    scheduler = BlockingScheduler(timezone=_market_timezone())
    scheduler.add_job(run_market_monitor, "interval", minutes=_market_interval_minutes())

    daily_time = _daily_job_time()
    scheduler.add_job(
        run_daily_job,
        CronTrigger(hour=daily_time.hour, minute=daily_time.minute),
    )

    scheduler.start()


if __name__ == "__main__":
    start_scheduler()
