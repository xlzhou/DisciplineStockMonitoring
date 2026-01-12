# Discipline-First Stock Monitoring System  
## Detailed Programming Specification (v1.6)

## 0. Purpose
Most investors do not fail because of missing information; they fail because they:
- React emotionally to price movement
- Violate pre-defined rules (chasing, averaging down, holding losers)
- Over-monitor intraday noise

The app should act as a “discipline firewall,” not a trading terminal.

Key design principle:

The system should tell you when to act — and explicitly tell you when not to act.
---

## 1. Product Definition

### 1.1 Core Purpose
Build a system that **enforces trading discipline**, not prediction.

The system:
- Continuously monitors market data on a backend
- Maintains user-defined indicators (e.g. MA20, MA120, MA250, arbitrary periods)
- Evaluates explicit rule plans
- Emits **unambiguous decisions**: `ALLOW / BLOCK`
- Notifies the user **only when the decision state changes**


The iOS app is a **decision console**, not a trading terminal.

---

## 2. System Architecture

### 2.1 High-Level Components

```
Market Data -> Indicator Engine -> Rule Engine -> Decision State Machine -> APNs
                                      |
                                      V
                                 Persistence
                                      |
                                      V
                                    iOS App
                      (Status | Actions | Portfolio | Review)
```
- Backend: Small cron job (every 5–15 min)
- Data: Alpha Vantage or Twelve Data
- iOS: Push notifications on rule state change

## 2.2 API to fetch delayed intraday market data
Alpha Vantage (Strong Recommendation)

Website: alphavantage.co
Cost: Free tier available (API key required)

What you get (Free)
- US stocks
- Daily, weekly, monthly OHLC
- Intraday data (1–5 min) — delayed
- Adjusted prices (splits/dividends)

Limits
- 5 API calls / minute
- 500 calls / day

---

## 3. Core Design Principles

1. **Data-driven indicators** (no hard-coded MA20/MA200)
2. **Rule-first**: missing or ambiguous rules -> BLOCK
3. **State-change notifications only**
4. **Deterministic evaluation**
5. **Auditability over convenience**

### 3.1 Mandatory Rule Categories
Each tracked stock should have:

A. Entry rules
- Buy price or range
- Position size (% of portfolio)
- Trigger condition (price, indicator, event)

B. Exit rules
- Hard stop-loss
- Trailing stop
- Take-profit levels (partial exits allowed)

C. Time rules
- Max holding period
- Cool-down after selling (no re-entry for X days)

D. Risk rules
- Max loss per position
- Max loss per day/week
- Max concurrent positions

### 3.2 Core Functional Modules (MVP Architecture)
#### 3.2.1 Watchlist ≠ Portfolio

Separate them strictly.
- Watchlist: ideas, no capital
- Portfolio: positions with enforceable rules

Never allow “soft positions.”
#### 3.2.2 Rule Engine (This Is the Heart)

A deterministic engine that evaluates:
Market Data -> Rule Set -> Action / No Action
Outputs:
- Action allowed (BUY / SELL )
Note: "ALLOW" refers to the decision, while BUY/SELL refers to the action type.
- Action blocked (with reason)

Example:
“SELL blocked: stop-loss not triggered and profit target not reached.”

BLOCKED implies no actionable BUY or SELL and corresponds to a HOLD state by implication.

#### 3.2.3 Alerting, Not Streaming

Avoid real-time charts by default.

Preferred:
- Event-based alerts
- Scheduled checks (e.g., every 15 min or end-of-day)

Alert types:
- Rule triggered
- Rule violation attempt
- Risk threshold breached
- Over-monitoring warning (excessive checking)
Over-monitoring warnings are advisory only and never block actions.

#### 3.2.4 Anti-Overtrading Controls (Very Important)

Add behavioral friction:
- Trade confirmation delay (e.g., 60 seconds)
- “Explain your reason” input before manual override
- Daily action limit

Log everything.
 

---

## 4. Backend Data Model

### 4.1 stocks
| Field | Type | Notes |
|---|---|---|
| id | PK | |
| ticker | TEXT | unique |
| market | TEXT | e.g. US |
| currency | TEXT | USD |
| status | TEXT | active / archived |
| created_at | DATETIME | 

Stocks in WATCHLIST state may exist without position state or capital allocation.
---

### 4.2 rule_plans
| Field | Type |
|---|---|
| id | PK |
| stock_id | FK |
| version | INTEGER |
| is_active | BOOLEAN |
| rules_json | TEXT |
| created_at | DATETIME |
| notes | TEXT |

Constraint: only one active rule plan per stock.

---

### 4.3 daily_bars
| Field | Type |
|---|---|
| stock_id | FK |
| bar_date | DATE |
| open | REAL |
| high | REAL |
| low | REAL |
| close | REAL |
| adjusted_close | REAL nullable |
| volume | INTEGER |
| source | TEXT |

Unique: `(stock_id, bar_date)`

---

### 4.4 indicator_defs
| Field | Type |
|---|---|
| id | PK |
| stock_id | FK |
| rule_plan_id | FK |
| indicator_id | TEXT (e.g. ma250) |
| indicator_type | TEXT (MA) |
| params_json | TEXT |
| timeframe | TEXT (1D) |
| price_field | TEXT |
| use_eod_only | BOOLEAN |
| created_at | DATETIME |

---

### 4.5 indicator_values
| Field | Type |
|---|---|
| stock_id | FK |
| indicator_id | TEXT |
| as_of_date | DATE |
| value | REAL |
| status | TEXT |
| lookback_used | INTEGER |
| computed_at | DATETIME |
| source | TEXT |

- indicator_values: unique (stock_id, indicator_id, as_of_date)

Indicator Status Definition
| Status | Meaning | Rule Engine Behavior |
|---|---|
| OK | Valid value | Use value |
| INSUFFICIENT_HISTORY | Not enough bars | BLOCK + reason |
| STALE | Data older than policy | BLOCK + reason |
| ERROR | Computation failed | BLOCK + log |

An indicator is considered STALE if its as_of_date is older than
the most recent completed trading day.

- indicator_defs are tied to a rule plan
- indicator_values are tied only to (stock_id, indicator_id)
Indicator values are reused only if indicator_type, params_json, timeframe, and price_field are identical.
---

### 4.6 decision_states
| Field | Type |
|---|---|
| stock_id | FK |
| state_key | TEXT |
| decision_json | TEXT |
| updated_at | DATETIME |
	
- decision_states: unique (stock_id)

state_key must be deterministic and stable for identical decision states to support reliable state-change detection.

---

### 4.7 audit_logs
| Field | Type |
|---|---|
| timestamp | DATETIME |
| stock_id | FK nullable |
| event_type | TEXT |
| payload_json | TEXT |

---

### 4.8 devices
| Field | Type |
|---|---|
| apns_token | TEXT |
| platform | TEXT |
| is_active | BOOLEAN |
| last_seen_at | DATETIME |
- devices: unique (apns_token)
---

## 5. Rule Plan Specification (JSON)

```json
{
  "schema_version": "1.1",
  "ticker": "AAPL",
  "indicator_policy": {
    "timeframe": "1D",
    "price_field": "close",
    "use_eod_only": true
  },
  "indicators": [
    { "id": "ma20",  "type": "MA", "ma_type": "SMA", "period": 20 },
    { "id": "ma120", "type": "MA", "ma_type": "SMA", "period": 120 },
    { "id": "ma250", "type": "MA", "ma_type": "SMA", "period": 250 }
  ]
}
```

---

## 6. Indicator Engine

- Supported: MA (SMA)
- Required bars = period
- Value = mean(last N closes)
- Insufficient data -> BLOCK
- Retain `max(period) + 30` bars

---

## 7. Rule Engine

### 7.1 Operators
- gt, gte, lt, lte, eq
- crosses_above, crosses_below
- all, any, not

crosses_above(a, b) is true iff:
- a[t] > b[t] AND
- a[t-1] <= b[t-1]
The system must retain the immediately previous indicator values
(t−1) to support crosses_above / crosses_below evaluation.


### 7.2 Example Condition
```json
{
  "all": [
    { "op": "gt", "left": "ind.ma20", "right": "ind.ma120" },
    { "op": "gt", "left": "ind.ma120", "right": "ind.ma250" }
  ]
}
```

---

## 8. Decision Output Contract

```json
{
  "decision": "ALLOW",
  "action": "BUY",
  "state_key": "ALLOW_BUY_E1",
  "reasons": [
    {
      "code": "TREND_CONFIRMED",
      "message": "MA20 > MA120 > MA250"
    }
  ]
}
```
```json
{
  "decision": "BLOCK",
  "action": "NONE",
  "state_key": "BLOCK_WAITING_FOR_TRIGGER",
  "reasons": [
    {
      "code": "ENTRY_CONDITION_NOT_MET",
      "message": "Price has not crossed above MA20"
    }
  ]
}
```
---

## 9. Backend Jobs

### Market Monitor (Every N Minutes)
- Fetch price
- Evaluate rules
- Notify on state change

### Daily Indicator Job (Post-Close)
- Ingest daily bar
- Compute indicators
- Re-evaluate rules

---

## 10. iOS App
### 10.1 Top-Level Navigation (Minimal Tabs)
#### Tabs: Recommended: 4 tabs max
- Status
- Portfolio
- Actions
- Review
No “Markets”, no “Charts”, no “News”.

### 10.2 Screen-by-Screen UI Design

### 10.2.1 STATUS (Home / Default Screen)

This is the screen you open 10 times a day.
It must answer one question in <5 seconds:
“Do I need to do anything right now?”

Screen: StatusView

Primary content
- Global status banner:
- “No action required”
- “1 action allowed”
- “Risk block active”
Per-stock status list (read-only)
- Ticker
- Current state:
- BLOCKED
- BUY ALLOWED
- SELL ALLOWED
- Short reason (1 line, truncated)
- “Waiting for price ≤ 180”
- “TP1 triggered (+8.2%)”

BLOCKED implies no actionable BUY or SELL and corresponds to a HOLD state by implication.

Allowed interactions
- Tap stock -> Action Detail
- Pull-to-refresh (manual only)

Explicitly NOT shown
- Price charts
- Candlesticks
- Intraday noise

### 10.2.2 PORTFOLIO (Stock Entities CRUD)

This is structure maintenance, not daily monitoring.

Screen: PortfolioListView

List of stock entities
- Ticker
- Strategy type (swing / long-term)
- Position status (flat / holding)
- Rule completeness indicator (complete / incomplete)

Actions
- Add Stock
- Tap stock -> StockDetailView

Screen: StockDetailView

Sections:
1.	Identity
  - Ticker (read-only after creation)
  - Market (US / HK / CN)
2.	Position State
  - Flat / Holding
  - Avg entry (if holding)
  - Days held
3.	Rule Summary (read-only)
  - Entry logic (1 line)
  - Exit logic (1 line)
  - Risk limits (1 line)

Actions
- Edit Rules
- View Audit Log
- Archive Stock (soft delete)

Screen: AddStockView (CRUD – Create)

Required fields
- Ticker
- Market
- Strategy style

Hard rule

You cannot save a stock without attaching a rule plan.

---

### 10.2.3 RULES INPUT / EDIT (Most Important Screen)

This screen defines your future behavior.
It should feel like writing a contract with yourself.

Screen: RuleEditorView

Design principle
- Structured form -> generates JSON
- Advanced users can toggle “Raw JSON view”

Rule Sections (Accordion / Step-based)
	1.	Position Intent
- Strategy type
- Max holding days
- Cooldown after exit
	2.	Position Sizing
- Target %
- Max %
- Account size (optional global)
	3.	Entry Rules
- Rule list (E1, E2…)
- Each rule:
- Trigger condition
- Size
- Constraints
	4.	Exit Rules
- Hard stop
- Take profit(s)
- Trailing stop
- Time stop
  5.	Risk Blocks
- Earnings window
- Max loss limits
	6.	Behavior Controls
- Confirmation delay
- Require reason
- Override limits
Validation behavior
- Missing required rule ->  cannot save
- Conflicting rules -> warning + explanation

---

### 10.2.4 ACTIONS (What You’re Allowed to Do)

This tab should usually be empty.

Screen: ActionListView

List only shows
- Actions that are currently ALLOWED

Each item:
- Ticker
- Action type (BUY / SELL)
    MVP assumption: execution is manual; user confirms execution in-app, which updates position state and audit logs.
- Triggered rule
- Time since trigger

If empty:

“No actions allowed. Staying disciplined is a decision.”
Screen: ActionDetailView

This is the “point of no return” screen.

Shows
- Action summary (what + why)
- Rule that triggered
- Price snapshot (single number, no chart)

Buttons
- Execute (or mark as executed)
- Dismiss
- Override (secondary, visually de-emphasized)

---

Override Flow (Mandatory Friction)
	1.	Confirmation countdown (e.g., 60s)
	2.	Reason input (required)
	3.	“This will be logged” warning

### 10.2.5 REVIEW (Behavior & Discipline)

This is where the app actually improves you.

Screen: ReviewDashboardView

Metrics
- Rule-follow rate
- Overrides this week
- Avg holding vs planned
- Best / worst deviations

No P&L focus by default.
Screen: AuditLogView

Immutable log
- Timestamp
- Event type:
- Rule evaluated
- Action allowed
- Override
- Alert sent
- Explanation

Filterable by ticker / date.
## 10.3 CRUD Responsibility Map (Clear Ownership)
| Entity          | Screen |
|---|---|
| Stock entity    | PortfolioList / StockDetail |
| Rule plan       | RuleEditor |
| Action          | ActionList / ActionDetail |
| Override        | ActionDetail |
| Logs            | Review / AuditLog |

## 10.4 Typical Daily User Flow (Ideal)
	1.	Open app -> Status
	2.	See “No action required”
	3.	Close app (success)

Occasionally:
	1.	Notification arrives
	2.	Open app -> ActionDetail
	3.	Execute or consciously override
	4.	Log is written

### Key UX Rules
- No charts by default
- No auto-refresh
- Overrides require delay + reason
- Logs are immutable

---

## 11 Time & Calendar Context

This system relies on market hours and trading days as defined below.

- Trading calendar source (NYSE calendar)
- Market open/close logic
- Weekend / holiday behavior
- EOD definition (e.g., after official close + buffer)


---

## 12. Non-Goals
- No prediction
- No alpha generation
- No news-based triggers
- No auto-trading in MVP

---

## 13. Error Handling

| Condition | Result |
|---|---|
| Missing data | BLOCK |
| Indicator insufficient history | BLOCK |
| Rule conflict | BLOCK |
| API failure | BLOCK + log |

---

## 14. Deployment (MVP)

- Single VPS
- SQLite
- Scheduled jobs
- Daily backups

---

## 15. Design Guarantee

This system ensures:
- Extensible indicators
- Explicit rules
- Explainable decisions
- Auditable behavior
- Minimal noise
