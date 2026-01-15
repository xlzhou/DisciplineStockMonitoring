# Backend Test Plan

## Local test suites
- Unit tests: rule expressions, indicators, schema validation
- Integration tests: API CRUD, ingestion, indicators, evaluation
- Live smoke test: Alpha Vantage (requires API key)

## Run all tests
```
python3 -m pytest -q
```

## Run without live smoke test
```
ALPHAVANTAGE_API_KEY= python3 -m pytest -q
```

## Run live Twelve Data smoke test
```
export TWELVEDATA_API_KEY=YOUR_KEY
python3 -m pytest -q backend/tests/test_live_alphavantage.py
```

## Manual E2E checklist
1. Start API: `uvicorn app.main:app --reload`
2. Create stock and rule plan (use `rule_plan.example.json`).
3. Trigger ingestion: `POST /jobs/ingest-daily/{stock_id}`
4. Trigger indicator compute: `POST /jobs/compute-indicators/{stock_id}`
5. Trigger evaluate: `POST /jobs/evaluate/{stock_id}`
6. Start scheduler: `python3 run_scheduler.py`
7. Verify `decision_states` changed and `audit_logs` entries.
