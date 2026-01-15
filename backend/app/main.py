from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import crud, jobs, models, schemas, validation
from .market_data import TwelveDataClient, get_cached_price, set_cached_price
from .config import load_env
from .db import Base, engine, get_db

load_env()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Discipline Stock Monitoring API")


@app.post("/stocks", response_model=schemas.StockOut, status_code=status.HTTP_201_CREATED)
def create_stock(stock_in: schemas.StockCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_stock(db, stock_in)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ticker already exists")


@app.get("/stocks", response_model=list[schemas.StockOut])
def list_stocks(db: Session = Depends(get_db)):
    return crud.list_stocks(db)


@app.get("/stocks/with-prices", response_model=list[schemas.StockPriceOut])
def list_stocks_with_prices(db: Session = Depends(get_db)):
    client = TwelveDataClient()
    stocks = crud.list_stocks(db)
    results: list[schemas.StockPriceOut] = []
    for stock in stocks:
        price = None
        try:
            if stock.status != "archived" and stock.market.upper() == "US":
                price = client.fetch_intraday_price_cached(stock.ticker)
        except Exception:
            price = None
        results.append(
            schemas.StockPriceOut(
                id=stock.id,
                ticker=stock.ticker,
                market=stock.market,
                currency=stock.currency,
                status=stock.status,
                position_state=stock.position_state,
                created_at=stock.created_at,
                price=price,
            )
        )
    return results


@app.get("/stocks/prices", response_model=list[schemas.StockPriceOnly])
def list_stock_prices(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    client = TwelveDataClient()
    stocks = crud.list_stocks(db)
    results: list[schemas.StockPriceOnly] = []
    to_fetch: list[str] = []

    for stock in stocks:
        price = None
        if stock.status != "archived" and stock.market.upper() == "US":
            cached = get_cached_price(stock.ticker, ttl_seconds=60)
            if cached is not None:
                price = cached
            else:
                to_fetch.append(stock.ticker)
        results.append(schemas.StockPriceOnly(id=stock.id, ticker=stock.ticker, price=price))

    if to_fetch:
        background_tasks.add_task(_refresh_prices, to_fetch, client)

    return results


def _refresh_prices(symbols: list[str], client: TwelveDataClient):
    for symbol in symbols:
        try:
            price = client.fetch_intraday_price(symbol)
            set_cached_price(symbol, price)
        except Exception:
            continue


@app.get("/debug/price/{ticker}")
def debug_price(ticker: str):
    client = TwelveDataClient()
    try:
        price = client.fetch_intraday_price(ticker)
        return {"ticker": ticker.upper(), "price": price}
    except Exception as exc:
        return {"ticker": ticker.upper(), "error": str(exc)}


@app.get("/stocks/validate/{ticker}")
def validate_ticker(ticker: str, market: str = "US"):
    if market.upper() != "US":
        return {"ticker": ticker.upper(), "valid": True}

    client = TwelveDataClient()
    try:
        price = client.fetch_intraday_price_cached(ticker)
    except Exception as exc:
        message = str(exc).lower()
        if "rate limit" in message or "limit" in message:
            return {"ticker": ticker.upper(), "valid": True, "status": "unverified"}
        if "symbol" in message and "not" in message:
            return {"ticker": ticker.upper(), "valid": False, "status": "invalid"}
        return {"ticker": ticker.upper(), "valid": True, "status": "unverified"}
    return {"ticker": ticker.upper(), "valid": price > 0}


@app.get("/stocks/{stock_id}", response_model=schemas.StockOut)
def get_stock(stock_id: int, db: Session = Depends(get_db)):
    stock = crud.get_stock(db, stock_id)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    return stock


@app.patch("/stocks/{stock_id}", response_model=schemas.StockOut)
def update_stock(stock_id: int, stock_in: schemas.StockUpdate, db: Session = Depends(get_db)):
    stock = crud.get_stock(db, stock_id)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    return crud.update_stock(db, stock, stock_in)


@app.delete("/stocks/{stock_id}", response_model=schemas.StockOut)
def archive_stock(stock_id: int, db: Session = Depends(get_db)):
    stock = crud.get_stock(db, stock_id)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    stock_in = schemas.StockUpdate(status="archived")
    return crud.update_stock(db, stock, stock_in)


@app.post(
    "/stocks/{stock_id}/rule-plans",
    response_model=schemas.RulePlanOut,
    status_code=status.HTTP_201_CREATED,
)
def create_rule_plan(stock_id: int, plan_in: schemas.RulePlanCreate, db: Session = Depends(get_db)):
    stock = crud.get_stock(db, stock_id)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    errors = validation.validate_rule_plan(plan_in.rules)
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})

    try:
        plan = crud.create_rule_plan(db, stock, plan_in)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Version already exists for this stock")

    return crud.serialize_rule_plan(plan)


@app.get("/stocks/{stock_id}/rule-plans", response_model=list[schemas.RulePlanOut])
def list_rule_plans(stock_id: int, db: Session = Depends(get_db)):
    stock = crud.get_stock(db, stock_id)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    plans = crud.list_rule_plans(db, stock_id)
    return [crud.serialize_rule_plan(plan) for plan in plans]


@app.get("/rule-plans/{rule_plan_id}", response_model=schemas.RulePlanOut)
def get_rule_plan(rule_plan_id: int, db: Session = Depends(get_db)):
    plan = crud.get_rule_plan(db, rule_plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Rule plan not found")
    return crud.serialize_rule_plan(plan)


@app.patch("/rule-plans/{rule_plan_id}", response_model=schemas.RulePlanOut)
def update_rule_plan(
    rule_plan_id: int, plan_in: schemas.RulePlanUpdate, db: Session = Depends(get_db)
):
    plan = crud.get_rule_plan(db, rule_plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Rule plan not found")

    plan = crud.update_rule_plan(db, plan, plan_in)
    return crud.serialize_rule_plan(plan)


@app.post("/jobs/ingest-daily/{stock_id}")
def run_daily_ingestion(stock_id: int, db: Session = Depends(get_db)):
    stock = crud.get_stock(db, stock_id)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    client = jobs.AlphaVantageClient()
    jobs.ingest_daily_bars(db, stock, client)
    return {"status": "ok", "stock_id": stock_id}


@app.post("/jobs/compute-indicators/{stock_id}")
def run_indicator_job(stock_id: int, db: Session = Depends(get_db)):
    stock = crud.get_stock(db, stock_id)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    jobs.update_indicators(db, stock)
    return {"status": "ok", "stock_id": stock_id}


@app.post("/jobs/evaluate/{stock_id}")
def run_rule_evaluation(stock_id: int, position_state: str | None = None, db: Session = Depends(get_db)):
    stock = crud.get_stock(db, stock_id)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    try:
        state = position_state or stock.position_state
        decision, changed = jobs.evaluate_rules(db, stock, state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok", "changed": changed, "decision": decision}


@app.post("/jobs/market-monitor/{stock_id}")
def run_market_monitor(stock_id: int, position_state: str | None = None, db: Session = Depends(get_db)):
    stock = crud.get_stock(db, stock_id)
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    client = jobs.AlphaVantageClient()
    state = position_state or stock.position_state
    decision, changed = jobs.market_monitor(db, stock, client, state)
    return {"status": "ok", "changed": changed, "decision": decision}


@app.post("/devices/register", response_model=schemas.DeviceOut, status_code=status.HTTP_201_CREATED)
def register_device(device_in: schemas.DeviceCreate, db: Session = Depends(get_db)):
    device = crud.upsert_device(db, device_in)
    return device


@app.get("/devices", response_model=list[schemas.DeviceOut])
def list_devices(db: Session = Depends(get_db)):
    return crud.list_devices(db)


@app.post("/devices/{token}/deactivate", response_model=schemas.DeviceOut)
def deactivate_device(token: str, db: Session = Depends(get_db)):
    device = crud.deactivate_device(db, token)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device
