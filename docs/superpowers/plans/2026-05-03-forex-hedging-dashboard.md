# USD-INR Hedging Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Streamlit dashboard that aggregates USD-INR price data, macro fundamentals, India-specific indicators, and news sentiment into a single daily hedging decision for an exporter with USD receivables.

**Architecture:** Data fetching is modular (one file per source group); analysis separates technical calculations from signal generation and the final decision engine; SQLite persists daily snapshots; Streamlit dashboard wires everything together in a single-page layout with sidebar controls.

**Tech Stack:** Python 3.11+, Streamlit, yfinance, pandas, numpy, plotly, requests, BeautifulSoup4, SQLite3, python-dotenv

---

## File Map

```
ForexApp/
├── dashboard.py                  # Main entry point — layout + wiring
├── requirements.txt
├── .env.example
├── config.py                     # Constants: default levels, thresholds, ticker map
├── data/
│   ├── __init__.py
│   ├── price_fetcher.py          # yfinance: spot, DXY, crude, yields, Nifty, VIX
│   ├── nse_scraper.py            # NSE USD-INR futures (current + next month)
│   ├── rbi_scraper.py            # RBI repo rate + FX reserves + press releases
│   ├── macro_scraper.py          # India 10Y yield, FII flows, India VIX
│   └── news_fetcher.py           # Reuters India RSS + keyword flagging
├── analysis/
│   ├── __init__.py
│   ├── technicals.py             # RSI, Bollinger Bands, ATR, SMA, level distances
│   ├── signals.py                # Convert readings → directional signals (+1/0/-1)
│   └── decision_engine.py        # Aggregate signals → recommendation + rationale
├── storage/
│   ├── __init__.py
│   └── db.py                     # SQLite schema, snapshot write, history read
└── ui/
    ├── __init__.py
    ├── charts.py                  # Plotly candlestick + indicators chart
    └── components.py             # Decision box, key levels table, macro grid, news feed
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `config.py`
- Create: `data/__init__.py`, `analysis/__init__.py`, `storage/__init__.py`, `ui/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
streamlit>=1.35.0
yfinance>=0.2.40
pandas>=2.2.0
numpy>=1.26.0
plotly>=5.20.0
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=5.1.0
python-dotenv>=1.0.0
feedparser>=6.0.11
```

- [ ] **Step 2: Create .env.example**

```
# Optional: FRED API key for more reliable macro data
FRED_API_KEY=your_fred_api_key_here
```

- [ ] **Step 3: Create config.py**

```python
from dataclasses import dataclass, field
from typing import List

TICKERS = {
    "usdinr_spot": "INR=X",
    "dxy": "DX-Y.NYB",
    "eurusd": "EURUSD=X",
    "brent": "BZ=F",
    "wti": "CL=F",
    "us_10y": "^TNX",
    "nifty": "^NSEI",
    "us_vix": "^VIX",
}

TECHNICAL_PARAMS = {
    "rsi_period": 14,
    "bb_period": 20,
    "bb_std": 2,
    "atr_period": 14,
    "atr_lookback_days": 90,
    "sma_fast": 50,
    "sma_slow": 200,
    "chart_lookback_months": 6,
}

DEFAULT_LEVELS = [
    {"name": "All-time High", "price": 95.20, "type": "resistance"},
    {"name": "Resistance 1", "price": 94.50, "type": "resistance"},
    {"name": "Support 1",    "price": 93.50, "type": "support"},
    {"name": "Support 2",    "price": 92.00, "type": "support"},
    {"name": "200 DMA",      "price": 0.0,   "type": "dynamic"},  # filled at runtime
]

SIGNAL_WEIGHTS = {
    "rsi_overbought":           +2,
    "rsi_moderately_high":      +1,
    "rsi_oversold":             -2,
    "bb_upper_breach":          +2,
    "bb_lower_breach":          -1,
    "dxy_falling":              +2,
    "dxy_rising":               -2,
    "oil_falling":              +1,
    "oil_rising":               -1,
    "high_volatility":          +1,
    "fii_inflow_strong":        +2,
    "fii_outflow_strong":       -2,
    "us_yield_falling":         +1,
    "us_yield_rising":          -1,
    "rbi_intervention_signal":  +2,
    "spot_above_200sma":        -1,
}

HEDGE_THRESHOLDS = [
    (0,   "WAIT",             0,   "Low"),
    (2,   "WAIT WITH ALERT",  25,  "Low"),
    (4,   "COVER PARTIAL",    50,  "Medium"),
    (6,   "COVER PARTIAL",    75,  "Medium"),
    (9,   "COVER NOW",        100, "High"),
]

DECISION_COLORS = {
    "WAIT":             "#1a7f37",
    "WAIT WITH ALERT":  "#bf8700",
    "COVER PARTIAL":    "#d97706",
    "COVER NOW":        "#dc2626",
}

RBI_PRESS_RELEASE_URL = "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx"
REUTERS_INDIA_RSS = "https://feeds.reuters.com/reuters/INbusinessNews"
NSE_CURRENCY_URL = "https://www.nseindia.com/api/quote-derivative?symbol=USDINR"
WORLDGOVBONDS_INDIA = "https://worldgovernmentbonds.com/country/india/"

FLAG_KEYWORDS = [
    "rbi intervention", "rate cut", "fii outflow", "fii inflow",
    "trade deal", "tariff", "fed", "iran", "oil sanctions",
    "rupee", "dollar", "forex", "foreign exchange", "intervention",
]

DB_PATH = "forex_dashboard.db"
```

- [ ] **Step 4: Create empty __init__.py files**

```bash
touch data/__init__.py analysis/__init__.py storage/__init__.py ui/__init__.py
```

- [ ] **Step 5: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages install without errors.

- [ ] **Step 6: Commit**

```bash
git init
git add requirements.txt .env.example config.py data/__init__.py analysis/__init__.py storage/__init__.py ui/__init__.py
git commit -m "feat: project scaffold with config and dependencies"
```

---

## Task 2: SQLite Storage Layer

**Files:**
- Create: `storage/db.py`

- [ ] **Step 1: Write the failing test**

Create `tests/storage/test_db.py`:

```python
import os, sys, sqlite3, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from storage.db import init_db, save_snapshot, get_history, DB_PATH

TEST_DB = "test_forex.db"

@pytest.fixture(autouse=True)
def use_test_db(monkeypatch):
    monkeypatch.setattr("storage.db.DB_PATH", TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_init_creates_tables():
    init_db()
    conn = sqlite3.connect(TEST_DB)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    assert "snapshots" in tables
    assert "decisions" in tables

def test_save_and_read_snapshot():
    init_db()
    snapshot = {
        "date": "2026-05-03",
        "usdinr_spot": 94.95,
        "rsi_daily": 68.5,
        "dxy": 104.2,
        "brent": 82.5,
        "recommendation": "COVER PARTIAL",
        "hedge_ratio": 50,
        "confidence": "Medium",
        "rationale": "RSI moderately high with DXY falling",
        "score": 5,
        "raw_json": '{"test": true}',
    }
    save_snapshot(snapshot)
    history = get_history(n=10)
    assert len(history) == 1
    assert history[0]["usdinr_spot"] == 94.95
    assert history[0]["recommendation"] == "COVER PARTIAL"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/storage/test_db.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'storage.db'`

- [ ] **Step 3: Implement storage/db.py**

```python
import sqlite3
import json
from typing import List, Dict, Any
from config import DB_PATH


def init_db(db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT NOT NULL,
            usdinr_spot REAL,
            rsi_daily   REAL,
            dxy         REAL,
            brent       REAL,
            recommendation TEXT,
            hedge_ratio INTEGER,
            confidence  TEXT,
            rationale   TEXT,
            score       REAL,
            raw_json    TEXT,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS decisions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT NOT NULL,
            action_taken TEXT,
            hedge_pct   INTEGER,
            notes       TEXT,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_snapshots_date ON snapshots(date);
    """)
    conn.commit()
    conn.close()


def save_snapshot(snapshot: Dict[str, Any], db_path: str = DB_PATH) -> None:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        INSERT OR REPLACE INTO snapshots
            (date, usdinr_spot, rsi_daily, dxy, brent, recommendation,
             hedge_ratio, confidence, rationale, score, raw_json)
        VALUES (:date, :usdinr_spot, :rsi_daily, :dxy, :brent, :recommendation,
                :hedge_ratio, :confidence, :rationale, :score, :raw_json)
    """, snapshot)
    conn.commit()
    conn.close()


def get_history(n: int = 30, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM snapshots ORDER BY date DESC LIMIT ?", (n,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_decision(decision: Dict[str, Any], db_path: str = DB_PATH) -> None:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        INSERT INTO decisions (date, action_taken, hedge_pct, notes)
        VALUES (:date, :action_taken, :hedge_pct, :notes)
    """, decision)
    conn.commit()
    conn.close()


def get_decisions(n: int = 30, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM decisions ORDER BY date DESC LIMIT ?", (n,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/storage/test_db.py -v
```

Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add storage/db.py tests/storage/test_db.py
git commit -m "feat: SQLite storage layer with snapshots and decisions tables"
```

---

## Task 3: Price Data Fetcher (yfinance)

**Files:**
- Create: `data/price_fetcher.py`

- [ ] **Step 1: Write the failing test**

Create `tests/data/test_price_fetcher.py`:

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from data.price_fetcher import fetch_price_data, PriceData

def make_mock_ticker(current_price: float, hist_rows: int = 260):
    ticker = MagicMock()
    ticker.info = {"regularMarketPrice": current_price}
    dates = pd.date_range("2025-06-01", periods=hist_rows, freq="B")
    ticker.history.return_value = pd.DataFrame({
        "Open":   [current_price * 0.999] * hist_rows,
        "High":   [current_price * 1.002] * hist_rows,
        "Low":    [current_price * 0.997] * hist_rows,
        "Close":  [current_price] * hist_rows,
        "Volume": [100000] * hist_rows,
    }, index=dates)
    return ticker

def test_fetch_price_data_returns_price_data():
    mock_tickers = {
        "INR=X": make_mock_ticker(94.95),
        "DX-Y.NYB": make_mock_ticker(104.2),
        "EURUSD=X": make_mock_ticker(1.082),
        "BZ=F": make_mock_ticker(82.5),
        "CL=F": make_mock_ticker(78.3),
        "^TNX": make_mock_ticker(4.35),
        "^NSEI": make_mock_ticker(22500.0),
        "^VIX": make_mock_ticker(17.5),
    }
    with patch("data.price_fetcher.yf.Ticker", side_effect=lambda sym: mock_tickers[sym]):
        result = fetch_price_data()
    assert isinstance(result, PriceData)
    assert result.usdinr_spot == pytest.approx(94.95)
    assert result.dxy == pytest.approx(104.2)
    assert len(result.usdinr_history) >= 250
    assert "Close" in result.usdinr_history.columns

def test_fetch_price_data_handles_missing_ticker():
    mock_tickers = {
        "INR=X": make_mock_ticker(94.95),
        "DX-Y.NYB": make_mock_ticker(104.2),
        "EURUSD=X": make_mock_ticker(1.082),
        "BZ=F": make_mock_ticker(82.5),
        "CL=F": make_mock_ticker(78.3),
        "^TNX": make_mock_ticker(4.35),
        "^NSEI": make_mock_ticker(22500.0),
        "^VIX": make_mock_ticker(17.5),
    }
    broken = MagicMock()
    broken.info = {}
    broken.history.return_value = pd.DataFrame()
    mock_tickers["^VIX"] = broken
    with patch("data.price_fetcher.yf.Ticker", side_effect=lambda sym: mock_tickers[sym]):
        result = fetch_price_data()
    assert result.us_vix is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/data/test_price_fetcher.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'data.price_fetcher'`

- [ ] **Step 3: Implement data/price_fetcher.py**

```python
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd
import yfinance as yf
from config import TICKERS


@dataclass
class PriceData:
    usdinr_spot: Optional[float] = None
    dxy: Optional[float] = None
    eurusd: Optional[float] = None
    brent: Optional[float] = None
    wti: Optional[float] = None
    us_10y_yield: Optional[float] = None
    nifty: Optional[float] = None
    us_vix: Optional[float] = None
    usdinr_history: pd.DataFrame = field(default_factory=pd.DataFrame)
    dxy_history: pd.DataFrame = field(default_factory=pd.DataFrame)
    brent_history: pd.DataFrame = field(default_factory=pd.DataFrame)


def _safe_price(ticker_obj) -> Optional[float]:
    try:
        price = ticker_obj.info.get("regularMarketPrice")
        if price:
            return float(price)
        hist = ticker_obj.history(period="2d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None


def _safe_history(ticker_obj, period: str = "1y") -> pd.DataFrame:
    try:
        hist = ticker_obj.history(period=period)
        if hist.empty:
            return pd.DataFrame()
        hist.index = pd.to_datetime(hist.index).tz_localize(None)
        return hist[["Open", "High", "Low", "Close", "Volume"]]
    except Exception:
        return pd.DataFrame()


def fetch_price_data() -> PriceData:
    result = PriceData()
    for attr, sym in [
        ("_usdinr", TICKERS["usdinr_spot"]),
        ("_dxy",    TICKERS["dxy"]),
        ("_eurusd", TICKERS["eurusd"]),
        ("_brent",  TICKERS["brent"]),
        ("_wti",    TICKERS["wti"]),
        ("_us10y",  TICKERS["us_10y"]),
        ("_nifty",  TICKERS["nifty"]),
        ("_usvix",  TICKERS["us_vix"]),
    ]:
        t = yf.Ticker(sym)
        if attr == "_usdinr":
            result.usdinr_spot = _safe_price(t)
            result.usdinr_history = _safe_history(t, "2y")
        elif attr == "_dxy":
            result.dxy = _safe_price(t)
            result.dxy_history = _safe_history(t, "1y")
        elif attr == "_eurusd":
            result.eurusd = _safe_price(t)
        elif attr == "_brent":
            result.brent = _safe_price(t)
            result.brent_history = _safe_history(t, "1y")
        elif attr == "_wti":
            result.wti = _safe_price(t)
        elif attr == "_us10y":
            result.us_10y_yield = _safe_price(t)
        elif attr == "_nifty":
            result.nifty = _safe_price(t)
        elif attr == "_usvix":
            result.us_vix = _safe_price(t)
    return result
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/data/test_price_fetcher.py -v
```

Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add data/price_fetcher.py tests/data/test_price_fetcher.py
git commit -m "feat: yfinance price data fetcher with PriceData dataclass"
```

---

## Task 4: NSE Futures Scraper

**Files:**
- Create: `data/nse_scraper.py`

- [ ] **Step 1: Write the failing test**

Create `tests/data/test_nse_scraper.py`:

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
from unittest.mock import patch, MagicMock
from data.nse_scraper import fetch_nse_futures, FuturesData

MOCK_NSE_RESPONSE = {
    "stocks": [
        {
            "metadata": {
                "expiryDate": "29-May-2026",
                "instrumentType": "Currency Futures",
            },
            "marketDeptOrderBook": {
                "tradeInfo": {"lastPrice": 95.10}
            }
        },
        {
            "metadata": {
                "expiryDate": "26-Jun-2026",
                "instrumentType": "Currency Futures",
            },
            "marketDeptOrderBook": {
                "tradeInfo": {"lastPrice": 95.45}
            }
        },
    ]
}

def test_fetch_nse_futures_parses_correctly():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_NSE_RESPONSE

    with patch("data.nse_scraper.requests.Session") as mock_session_cls:
        session = MagicMock()
        mock_session_cls.return_value = session
        session.get.return_value = mock_resp

        result = fetch_nse_futures(spot_price=94.95)

    assert isinstance(result, FuturesData)
    assert result.near_month_price == pytest.approx(95.10)
    assert result.next_month_price == pytest.approx(95.45)
    assert result.near_month_basis == pytest.approx(95.10 - 94.95)

def test_fetch_nse_futures_falls_back_on_error():
    with patch("data.nse_scraper.requests.Session") as mock_session_cls:
        session = MagicMock()
        mock_session_cls.return_value = session
        session.get.side_effect = Exception("connection refused")
        result = fetch_nse_futures(spot_price=94.95)

    assert isinstance(result, FuturesData)
    assert result.near_month_price is None
    assert result.error is not None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/data/test_nse_scraper.py -v
```

Expected: FAIL — module not found

- [ ] **Step 3: Implement data/nse_scraper.py**

```python
from dataclasses import dataclass
from typing import Optional
import requests


@dataclass
class FuturesData:
    near_month_price: Optional[float] = None
    near_month_expiry: Optional[str] = None
    next_month_price: Optional[float] = None
    next_month_expiry: Optional[str] = None
    near_month_basis: Optional[float] = None   # futures - spot
    error: Optional[str] = None


NSE_API_URL = "https://www.nseindia.com/api/quote-derivative?symbol=USDINR"
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}


def fetch_nse_futures(spot_price: Optional[float] = None) -> FuturesData:
    try:
        session = requests.Session()
        # Prime cookies
        session.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=10)
        resp = session.get(NSE_API_URL, headers=NSE_HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        futures = [
            s for s in data.get("stocks", [])
            if "Futures" in s.get("metadata", {}).get("instrumentType", "")
        ]
        futures.sort(key=lambda s: s["metadata"]["expiryDate"])

        result = FuturesData()
        if len(futures) >= 1:
            near = futures[0]
            result.near_month_price = float(
                near["marketDeptOrderBook"]["tradeInfo"]["lastPrice"]
            )
            result.near_month_expiry = near["metadata"]["expiryDate"]
            if spot_price and result.near_month_price:
                result.near_month_basis = round(result.near_month_price - spot_price, 4)
        if len(futures) >= 2:
            nxt = futures[1]
            result.next_month_price = float(
                nxt["marketDeptOrderBook"]["tradeInfo"]["lastPrice"]
            )
            result.next_month_expiry = nxt["metadata"]["expiryDate"]
        return result

    except Exception as e:
        return FuturesData(error=str(e))
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/data/test_nse_scraper.py -v
```

Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add data/nse_scraper.py tests/data/test_nse_scraper.py
git commit -m "feat: NSE futures scraper with graceful fallback on failure"
```

---

## Task 5: RBI + Macro Scraper

**Files:**
- Create: `data/rbi_scraper.py`
- Create: `data/macro_scraper.py`

- [ ] **Step 1: Write the failing test**

Create `tests/data/test_scrapers.py`:

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from unittest.mock import patch, MagicMock
from data.rbi_scraper import fetch_rbi_data, RBIData
from data.macro_scraper import fetch_macro_data, MacroData

RBI_HTML = """
<html><body>
<table class="tablebg">
<tr><td>Repo Rate</td><td>6.25%</td></tr>
</table>
<p>Foreign Exchange Reserves as on April 25, 2026: USD 688.5 billion</p>
</body></html>
"""

def test_fetch_rbi_data_parses_repo_rate():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = RBI_HTML
    with patch("data.rbi_scraper.requests.get", return_value=mock_resp):
        result = fetch_rbi_data()
    assert isinstance(result, RBIData)
    assert result.repo_rate == 6.25

def test_fetch_rbi_data_returns_defaults_on_error():
    with patch("data.rbi_scraper.requests.get", side_effect=Exception("timeout")):
        result = fetch_rbi_data()
    assert isinstance(result, RBIData)
    assert result.repo_rate is None
    assert result.error is not None

WORLDGOVBONDS_HTML = """
<html><body>
<div class="country-flag-container">
<span class="yield10y">7.05%</span>
</div>
</body></html>
"""

def test_fetch_macro_data_returns_macro_data():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = WORLDGOVBONDS_HTML
    with patch("data.macro_scraper.requests.get", return_value=mock_resp):
        result = fetch_macro_data()
    assert isinstance(result, MacroData)

def test_fetch_macro_data_handles_error():
    with patch("data.macro_scraper.requests.get", side_effect=Exception("timeout")):
        result = fetch_macro_data()
    assert isinstance(result, MacroData)
    assert result.india_10y_yield is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/data/test_scrapers.py -v
```

Expected: FAIL — modules not found

- [ ] **Step 3: Implement data/rbi_scraper.py**

```python
import re
from dataclasses import dataclass
from typing import Optional, List
import requests
from bs4 import BeautifulSoup

RBI_MONETARY_URL = "https://www.rbi.org.in/Scripts/BS_ViewMastersiteMap.aspx"
RBI_PRESS_URL    = "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx"


@dataclass
class RBIData:
    repo_rate: Optional[float] = None
    fx_reserves_usd_bn: Optional[float] = None
    press_releases: List[dict] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.press_releases is None:
            self.press_releases = []


_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ForexDashbot/1.0)"}


def _parse_repo_rate(html: str) -> Optional[float]:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ")
    match = re.search(r"Repo\s+Rate[^\d]*(\d+\.?\d*)\s*%", text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def _parse_fx_reserves(html: str) -> Optional[float]:
    match = re.search(
        r"Foreign Exchange Reserves[^\d]*([\d,]+\.?\d*)\s*(billion|USD bn|USD)",
        html, re.IGNORECASE
    )
    if match:
        val = float(match.group(1).replace(",", ""))
        return val
    return None


def _fetch_press_releases() -> List[dict]:
    try:
        resp = requests.get(RBI_PRESS_URL, headers=_HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        items = []
        for row in soup.select("table tr")[1:11]:
            cols = row.find_all("td")
            if len(cols) >= 2:
                items.append({
                    "date": cols[0].get_text(strip=True),
                    "title": cols[1].get_text(strip=True),
                    "url": "https://www.rbi.org.in" + (cols[1].find("a") or {}).get("href", ""),
                })
        return items
    except Exception:
        return []


def fetch_rbi_data() -> RBIData:
    try:
        resp = requests.get(RBI_MONETARY_URL, headers=_HEADERS, timeout=10)
        repo = _parse_repo_rate(resp.text)
        fx = _parse_fx_reserves(resp.text)
        releases = _fetch_press_releases()
        return RBIData(repo_rate=repo, fx_reserves_usd_bn=fx, press_releases=releases)
    except Exception as e:
        try:
            FALLBACK = "https://www.rbi.org.in/home.aspx"
            resp = requests.get(FALLBACK, headers=_HEADERS, timeout=10)
            return RBIData(
                repo_rate=_parse_repo_rate(resp.text),
                fx_reserves_usd_bn=None,
                press_releases=_fetch_press_releases(),
            )
        except Exception as e2:
            return RBIData(error=str(e2))
```

- [ ] **Step 4: Implement data/macro_scraper.py**

```python
import re
from dataclasses import dataclass
from typing import Optional
import requests
from bs4 import BeautifulSoup

WORLDGOVBONDS_INDIA = "https://worldgovernmentbonds.com/country/india/"
NSE_INDICES_URL = "https://www.nseindia.com/api/allIndices"
NSDL_FII_URL = "https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx"

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ForexDashbot/1.0)"}
_NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.nseindia.com/",
}


@dataclass
class MacroData:
    india_10y_yield: Optional[float] = None
    india_vix: Optional[float] = None
    fii_equity_net_crore: Optional[float] = None
    error: Optional[str] = None


def _fetch_india_10y() -> Optional[float]:
    try:
        resp = requests.get(WORLDGOVBONDS_INDIA, headers=_HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        text = soup.get_text(" ")
        match = re.search(r"10\s*Year[^\d]*([\d]+\.[\d]+)\s*%", text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        match = re.search(r"([\d]+\.[\d]+)\s*%", text)
        if match:
            return float(match.group(1))
    except Exception:
        pass
    return None


def _fetch_india_vix() -> Optional[float]:
    try:
        import requests as req
        session = req.Session()
        session.get("https://www.nseindia.com", headers=_NSE_HEADERS, timeout=10)
        resp = session.get(NSE_INDICES_URL, headers=_NSE_HEADERS, timeout=10)
        data = resp.json()
        for idx in data.get("data", []):
            if "INDIA VIX" in idx.get("index", "").upper():
                return float(idx["last"])
    except Exception:
        pass
    return None


def _fetch_fii_flows() -> Optional[float]:
    try:
        resp = requests.get(NSDL_FII_URL, headers=_HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        text = soup.get_text(" ")
        match = re.search(
            r"(?:Equity|Equities)[^\d\-]*([\-\d,]+\.?\d*)\s*(?:Cr|crore)",
            text, re.IGNORECASE
        )
        if match:
            return float(match.group(1).replace(",", ""))
    except Exception:
        pass
    return None


def fetch_macro_data() -> MacroData:
    errors = []
    india_10y = None
    india_vix = None
    fii = None
    try:
        india_10y = _fetch_india_10y()
    except Exception as e:
        errors.append(str(e))
    try:
        india_vix = _fetch_india_vix()
    except Exception as e:
        errors.append(str(e))
    try:
        fii = _fetch_fii_flows()
    except Exception as e:
        errors.append(str(e))
    return MacroData(
        india_10y_yield=india_10y,
        india_vix=india_vix,
        fii_equity_net_crore=fii,
        error="; ".join(errors) if errors else None,
    )
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/data/test_scrapers.py -v
```

Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add data/rbi_scraper.py data/macro_scraper.py tests/data/test_scrapers.py
git commit -m "feat: RBI and macro data scrapers with graceful fallbacks"
```

---

## Task 6: News Fetcher

**Files:**
- Create: `data/news_fetcher.py`

- [ ] **Step 1: Write the failing test**

Create `tests/data/test_news_fetcher.py`:

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from unittest.mock import patch
from data.news_fetcher import fetch_news, NewsItem, flag_keywords

MOCK_FEED = {
    "entries": [
        {
            "title": "RBI intervention in forex market caps rupee fall",
            "link": "https://reuters.com/article/1",
            "published": "Sat, 03 May 2026 08:00:00 +0000",
            "summary": "RBI sold dollars to cap rupee depreciation.",
        },
        {
            "title": "India Nifty hits record high",
            "link": "https://reuters.com/article/2",
            "published": "Sat, 03 May 2026 07:00:00 +0000",
            "summary": "Equity rally continues.",
        },
    ]
}

def test_fetch_news_returns_news_items():
    with patch("data.news_fetcher.feedparser.parse", return_value=MOCK_FEED):
        items = fetch_news()
    assert len(items) == 2
    assert all(isinstance(i, NewsItem) for i in items)

def test_flag_keywords_detects_rbi_intervention():
    with patch("data.news_fetcher.feedparser.parse", return_value=MOCK_FEED):
        items = fetch_news()
    flagged = [i for i in items if i.flagged]
    assert len(flagged) == 1
    assert "rbi intervention" in flagged[0].matched_keywords

def test_flag_keywords_standalone():
    assert "fed" in flag_keywords("Fed raises rates by 25 bps")
    assert "tariff" in flag_keywords("New tariff on Indian steel exports")
    assert flag_keywords("Nifty closes flat") == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/data/test_news_fetcher.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement data/news_fetcher.py**

```python
from dataclasses import dataclass, field
from typing import List
import feedparser
from config import REUTERS_INDIA_RSS, FLAG_KEYWORDS


@dataclass
class NewsItem:
    title: str
    url: str
    published: str
    summary: str
    flagged: bool = False
    matched_keywords: List[str] = field(default_factory=list)


def flag_keywords(text: str) -> List[str]:
    text_lower = text.lower()
    return [kw for kw in FLAG_KEYWORDS if kw in text_lower]


def fetch_news(max_items: int = 20) -> List[NewsItem]:
    feed = feedparser.parse(REUTERS_INDIA_RSS)
    items = []
    for entry in feed.get("entries", [])[:max_items]:
        title   = entry.get("title", "")
        summary = entry.get("summary", "")
        combined = f"{title} {summary}"
        matched = flag_keywords(combined)
        items.append(NewsItem(
            title=title,
            url=entry.get("link", ""),
            published=entry.get("published", ""),
            summary=summary,
            flagged=len(matched) > 0,
            matched_keywords=matched,
        ))
    return items
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/data/test_news_fetcher.py -v
```

Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add data/news_fetcher.py tests/data/test_news_fetcher.py
git commit -m "feat: Reuters RSS news fetcher with keyword flagging"
```

---

## Task 7: Technical Analysis

**Files:**
- Create: `analysis/technicals.py`

- [ ] **Step 1: Write the failing test**

Create `tests/analysis/test_technicals.py`:

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import numpy as np
import pandas as pd
import pytest
from analysis.technicals import compute_technicals, TechnicalSnapshot

def make_price_series(n=260, start=90.0, trend=0.01):
    np.random.seed(42)
    prices = [start]
    for _ in range(n - 1):
        prices.append(prices[-1] * (1 + trend / 100 + np.random.normal(0, 0.003)))
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.DataFrame({
        "Open":   [p * 0.999 for p in prices],
        "High":   [p * 1.003 for p in prices],
        "Low":    [p * 0.997 for p in prices],
        "Close":  prices,
        "Volume": [1_000_000] * n,
    }, index=dates)

def test_compute_technicals_returns_snapshot():
    df = make_price_series(260, start=90.0, trend=0.02)
    snap = compute_technicals(df)
    assert isinstance(snap, TechnicalSnapshot)
    assert 0 <= snap.rsi_daily <= 100
    assert snap.sma_50 > 0
    assert snap.sma_200 > 0
    assert snap.atr_14 > 0
    assert snap.bb_upper > snap.bb_mid > snap.bb_lower

def test_rsi_overbought_on_rising_prices():
    df = make_price_series(260, start=90.0, trend=0.15)
    snap = compute_technicals(df)
    assert snap.rsi_daily > 60

def test_rsi_oversold_on_falling_prices():
    df = make_price_series(260, start=95.0, trend=-0.15)
    snap = compute_technicals(df)
    assert snap.rsi_daily < 40

def test_distance_from_sma():
    df = make_price_series(260, start=90.0, trend=0.02)
    snap = compute_technicals(df)
    spot = df["Close"].iloc[-1]
    expected_dist_50 = (spot - snap.sma_50) / snap.sma_50 * 100
    assert abs(snap.pct_above_sma50 - expected_dist_50) < 0.01
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/analysis/test_technicals.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement analysis/technicals.py**

```python
from dataclasses import dataclass
from typing import Optional
import numpy as np
import pandas as pd
from config import TECHNICAL_PARAMS


@dataclass
class TechnicalSnapshot:
    spot: float
    rsi_daily: Optional[float] = None
    rsi_weekly: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    pct_above_sma50: Optional[float] = None
    pct_above_sma200: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_mid: Optional[float] = None
    bb_lower: Optional[float] = None
    bb_pct_b: Optional[float] = None       # (price - lower) / (upper - lower)
    bb_bandwidth: Optional[float] = None   # (upper - lower) / mid
    atr_14: Optional[float] = None
    atr_90d_avg: Optional[float] = None
    atr_elevated: bool = False


def _rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff().dropna()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean().iloc[-1]
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, prev_close = df["High"], df["Low"], df["Close"].shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(com=period - 1, min_periods=period).mean()


def _weekly_rsi(df: pd.DataFrame, period: int = 14) -> Optional[float]:
    weekly = df["Close"].resample("W").last().dropna()
    if len(weekly) < period + 5:
        return None
    return _rsi(weekly, period)


def compute_technicals(df: pd.DataFrame) -> TechnicalSnapshot:
    p = TECHNICAL_PARAMS
    close = df["Close"]
    spot = float(close.iloc[-1])

    sma50 = float(close.rolling(p["sma_fast"]).mean().iloc[-1])
    sma200 = float(close.rolling(p["sma_slow"]).mean().iloc[-1])

    bb_mid = float(close.rolling(p["bb_period"]).mean().iloc[-1])
    bb_std = float(close.rolling(p["bb_period"]).std().iloc[-1])
    bb_upper = bb_mid + p["bb_std"] * bb_std
    bb_lower = bb_mid - p["bb_std"] * bb_std
    bb_pct_b = (spot - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5
    bb_bw = (bb_upper - bb_lower) / bb_mid if bb_mid else 0

    atr_series = _atr(df, p["atr_period"])
    atr_now = float(atr_series.iloc[-1])
    atr_90d = float(atr_series.iloc[-p["atr_lookback_days"]:].mean())

    return TechnicalSnapshot(
        spot=spot,
        rsi_daily=_rsi(close, p["rsi_period"]),
        rsi_weekly=_weekly_rsi(df, p["rsi_period"]),
        sma_50=round(sma50, 4),
        sma_200=round(sma200, 4),
        pct_above_sma50=round((spot - sma50) / sma50 * 100, 2),
        pct_above_sma200=round((spot - sma200) / sma200 * 100, 2),
        bb_upper=round(bb_upper, 4),
        bb_mid=round(bb_mid, 4),
        bb_lower=round(bb_lower, 4),
        bb_pct_b=round(bb_pct_b, 3),
        bb_bandwidth=round(bb_bw * 100, 2),
        atr_14=round(atr_now, 4),
        atr_90d_avg=round(atr_90d, 4),
        atr_elevated=atr_now > atr_90d * 1.25,
    )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/analysis/test_technicals.py -v
```

Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add analysis/technicals.py tests/analysis/test_technicals.py
git commit -m "feat: technical analysis — RSI, Bollinger Bands, ATR, SMA"
```

---

## Task 8: Signal Generation + Decision Engine

**Files:**
- Create: `analysis/signals.py`
- Create: `analysis/decision_engine.py`

- [ ] **Step 1: Write the failing test**

Create `tests/analysis/test_decision_engine.py`:

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
from analysis.technicals import TechnicalSnapshot
from analysis.signals import generate_signals
from analysis.decision_engine import make_decision, Decision
from data.price_fetcher import PriceData
from data.macro_scraper import MacroData
from data.news_fetcher import NewsItem

def base_tech() -> TechnicalSnapshot:
    return TechnicalSnapshot(
        spot=94.95, rsi_daily=55.0, rsi_weekly=52.0,
        sma_50=93.5, sma_200=91.0,
        pct_above_sma50=1.55, pct_above_sma200=4.34,
        bb_upper=96.0, bb_mid=94.0, bb_lower=92.0,
        bb_pct_b=0.55, bb_bandwidth=4.25,
        atr_14=0.42, atr_90d_avg=0.38, atr_elevated=False,
    )

def base_price() -> PriceData:
    p = PriceData()
    p.dxy = 104.2; p.brent = 82.5; p.us_10y_yield = 4.35
    p.us_vix = 17.5
    return p

def test_cover_now_on_overbought_dxy_falling():
    tech = base_tech()
    tech.rsi_daily = 74.0
    tech.bb_pct_b = 0.95
    tech.atr_elevated = True
    price = base_price()
    price.dxy = 101.5  # falling (need history context, signals use snapshot only)
    macro = MacroData(india_10y_yield=7.05, india_vix=13.5, fii_equity_net_crore=2500)
    signals = generate_signals(tech, price, macro, [], dxy_5d_change=-1.5)
    decision = make_decision(signals)
    assert isinstance(decision, Decision)
    assert decision.hedge_ratio >= 50

def test_wait_on_low_rsi_strong_dxy():
    tech = base_tech()
    tech.rsi_daily = 38.0
    tech.bb_pct_b = 0.15
    price = base_price()
    macro = MacroData(india_10y_yield=7.05, india_vix=22.0, fii_equity_net_crore=-1500)
    signals = generate_signals(tech, price, macro, [], dxy_5d_change=+1.2)
    decision = make_decision(signals)
    assert decision.hedge_ratio <= 25

def test_decision_has_rationale():
    tech = base_tech()
    price = base_price()
    macro = MacroData()
    signals = generate_signals(tech, price, macro, [], dxy_5d_change=0)
    decision = make_decision(signals)
    assert len(decision.rationale) > 10
    assert decision.confidence in ("Low", "Medium", "High")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/analysis/test_decision_engine.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement analysis/signals.py**

```python
from dataclasses import dataclass
from typing import List, Optional
from analysis.technicals import TechnicalSnapshot
from data.price_fetcher import PriceData
from data.macro_scraper import MacroData
from data.news_fetcher import NewsItem
from config import SIGNAL_WEIGHTS


@dataclass
class Signal:
    name: str
    weight: int
    description: str
    direction: str  # "COVER" if weight > 0, "WAIT" if weight < 0


def generate_signals(
    tech: TechnicalSnapshot,
    price: PriceData,
    macro: MacroData,
    news: List[NewsItem],
    dxy_5d_change: Optional[float] = None,
    brent_5d_change: Optional[float] = None,
    us_yield_5d_change: Optional[float] = None,
) -> List[Signal]:
    signals: List[Signal] = []

    def add(name: str, description: str):
        w = SIGNAL_WEIGHTS.get(name, 0)
        if w != 0:
            signals.append(Signal(
                name=name, weight=w, description=description,
                direction="COVER" if w > 0 else "WAIT",
            ))

    # RSI signals
    if tech.rsi_daily and tech.rsi_daily > 70:
        add("rsi_overbought", f"RSI(14) daily = {tech.rsi_daily:.1f} — overbought, reversal risk")
    elif tech.rsi_daily and tech.rsi_daily > 60:
        add("rsi_moderately_high", f"RSI(14) daily = {tech.rsi_daily:.1f} — elevated momentum")
    elif tech.rsi_daily and tech.rsi_daily < 40:
        add("rsi_oversold", f"RSI(14) daily = {tech.rsi_daily:.1f} — oversold, bounce risk")

    # Bollinger Band signals
    if tech.bb_pct_b and tech.bb_pct_b > 0.85:
        add("bb_upper_breach", f"Price at {tech.bb_pct_b*100:.0f}% of Bollinger Band — stretched upper")
    elif tech.bb_pct_b and tech.bb_pct_b < 0.20:
        add("bb_lower_breach", f"Price at {tech.bb_pct_b*100:.0f}% of Bollinger Band — near lower band")

    # Volatility
    if tech.atr_elevated:
        add("high_volatility", f"ATR ({tech.atr_14:.3f}) > 125% of 90d avg ({tech.atr_90d_avg:.3f})")

    # DXY momentum
    if dxy_5d_change is not None:
        if dxy_5d_change < -0.5:
            add("dxy_falling", f"DXY 5d change = {dxy_5d_change:+.2f}% — dollar weakening globally")
        elif dxy_5d_change > 0.5:
            add("dxy_rising", f"DXY 5d change = {dxy_5d_change:+.2f}% — dollar strengthening globally")

    # Oil momentum
    if brent_5d_change is not None:
        if brent_5d_change < -2.0:
            add("oil_falling", f"Brent 5d change = {brent_5d_change:+.2f}% — lower oil pressure on INR")
        elif brent_5d_change > 2.0:
            add("oil_rising", f"Brent 5d change = {brent_5d_change:+.2f}% — rising oil pressure on INR")

    # US yield momentum
    if us_yield_5d_change is not None:
        if us_yield_5d_change < -0.05:
            add("us_yield_falling", f"US 10Y yield 5d change = {us_yield_5d_change:+.3f}% — USD softening")
        elif us_yield_5d_change > 0.05:
            add("us_yield_rising", f"US 10Y yield 5d change = {us_yield_5d_change:+.3f}% — USD strengthening")

    # SMA position
    if tech.pct_above_sma200 and tech.pct_above_sma200 > 0:
        add("spot_above_200sma", f"Spot is {tech.pct_above_sma200:+.2f}% above 200 SMA — uptrend intact")

    # FII flows
    if macro.fii_equity_net_crore is not None:
        if macro.fii_equity_net_crore > 1000:
            add("fii_inflow_strong", f"FII net equity inflow ₹{macro.fii_equity_net_crore:,.0f} Cr — INR demand")
        elif macro.fii_equity_net_crore < -1000:
            add("fii_outflow_strong", f"FII net equity outflow ₹{macro.fii_equity_net_crore:,.0f} Cr — INR selling")

    # News keyword flags
    rbi_kw = ["rbi intervention", "intervention"]
    flagged_news = [n for n in news if n.flagged]
    for item in flagged_news:
        if any(kw in item.matched_keywords for kw in rbi_kw):
            add("rbi_intervention_signal", f"News: '{item.title[:60]}...'")
            break

    return signals
```

- [ ] **Step 4: Implement analysis/decision_engine.py**

```python
from dataclasses import dataclass
from typing import List
from analysis.signals import Signal
from config import HEDGE_THRESHOLDS, DECISION_COLORS


@dataclass
class Decision:
    recommendation: str
    hedge_ratio: int
    confidence: str
    rationale: str
    score: float
    signals: List[Signal]
    color: str


def make_decision(signals: List[Signal]) -> Decision:
    score = sum(s.weight for s in signals)

    recommendation = "WAIT"
    hedge_ratio = 0
    confidence = "Low"
    for threshold, rec, ratio, conf in reversed(HEDGE_THRESHOLDS):
        if score >= threshold:
            recommendation = rec
            hedge_ratio = ratio
            confidence = conf
            break

    cover_signals = [s for s in signals if s.weight > 0]
    wait_signals  = [s for s in signals if s.weight < 0]

    if cover_signals:
        top = sorted(cover_signals, key=lambda s: abs(s.weight), reverse=True)[0]
        rationale = f"{top.description}"
    elif wait_signals:
        top = sorted(wait_signals, key=lambda s: abs(s.weight), reverse=True)[0]
        rationale = f"{top.description}"
    else:
        rationale = "No strong directional signals — neutral market conditions"

    if len(signals) < 3:
        confidence = "Low"

    return Decision(
        recommendation=recommendation,
        hedge_ratio=hedge_ratio,
        confidence=confidence,
        rationale=rationale,
        score=score,
        signals=signals,
        color=DECISION_COLORS.get(recommendation, "#6b7280"),
    )
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/analysis/test_decision_engine.py -v
```

Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add analysis/signals.py analysis/decision_engine.py tests/analysis/test_decision_engine.py
git commit -m "feat: signal generation and decision engine with hedge ratio scoring"
```

---

## Task 9: Plotly Charts

**Files:**
- Create: `ui/charts.py`

- [ ] **Step 1: Implement ui/charts.py**

No unit tests needed for chart rendering — test visually in the browser.

```python
from typing import List, Optional
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from analysis.technicals import TechnicalSnapshot
from config import TECHNICAL_PARAMS


def build_usdinr_chart(
    df: pd.DataFrame,
    tech: TechnicalSnapshot,
    levels: List[dict],
    lookback_months: int = 6,
) -> go.Figure:
    cutoff = pd.Timestamp.now() - pd.DateOffset(months=lookback_months)
    df = df[df.index >= cutoff].copy()
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No price data available", showarrow=False)
        return fig

    p = TECHNICAL_PARAMS
    close = df["Close"]
    sma50  = close.rolling(p["sma_fast"]).mean()
    sma200 = close.rolling(p["sma_slow"]).mean()
    bb_mid = close.rolling(p["bb_period"]).mean()
    bb_std = close.rolling(p["bb_period"]).std()
    bb_upper = bb_mid + p["bb_std"] * bb_std
    bb_lower = bb_mid - p["bb_std"] * bb_std

    # RSI sub-chart
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=p["rsi_period"] - 1, min_periods=p["rsi_period"]).mean()
    avg_loss = loss.ewm(com=p["rsi_period"] - 1, min_periods=p["rsi_period"]).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.03,
    )

    # Candlesticks
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        name="USD/INR", increasing_line_color="#22c55e",
        decreasing_line_color="#ef4444",
    ), row=1, col=1)

    # Bollinger Bands
    fig.add_trace(go.Scatter(
        x=df.index, y=bb_upper, name="BB Upper",
        line=dict(color="rgba(99,102,241,0.5)", width=1, dash="dot"),
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=bb_lower, name="BB Lower",
        fill="tonexty", fillcolor="rgba(99,102,241,0.05)",
        line=dict(color="rgba(99,102,241,0.5)", width=1, dash="dot"),
    ), row=1, col=1)

    # SMAs
    fig.add_trace(go.Scatter(
        x=df.index, y=sma50, name=f"SMA {p['sma_fast']}",
        line=dict(color="#f59e0b", width=1.5),
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=sma200, name=f"SMA {p['sma_slow']}",
        line=dict(color="#8b5cf6", width=1.5),
    ), row=1, col=1)

    # Key levels (horizontal lines)
    colors = {"resistance": "#ef4444", "support": "#22c55e", "dynamic": "#6b7280"}
    for lvl in levels:
        price = lvl["price"]
        if price <= 0:
            continue
        ltype = lvl.get("type", "support")
        fig.add_hline(
            y=price, line_dash="dash",
            line_color=colors.get(ltype, "#6b7280"),
            annotation_text=f"{lvl['name']} ({price:.2f})",
            annotation_position="right",
            row=1, col=1,
        )

    # RSI subplot
    fig.add_trace(go.Scatter(
        x=df.index, y=rsi, name="RSI(14)",
        line=dict(color="#06b6d4", width=1.5),
    ), row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#ef4444", row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#22c55e", row=2, col=1)

    fig.update_layout(
        height=550,
        margin=dict(l=0, r=10, t=30, b=0),
        paper_bgcolor="#0f172a",
        plot_bgcolor="#1e293b",
        font=dict(color="#cbd5e1"),
        legend=dict(orientation="h", yanchor="bottom", y=1.01),
        xaxis_rangeslider_visible=False,
    )
    fig.update_xaxes(gridcolor="#334155", showgrid=True)
    fig.update_yaxes(gridcolor="#334155", showgrid=True)
    return fig
```

- [ ] **Step 2: Commit**

```bash
git add ui/charts.py
git commit -m "feat: Plotly candlestick chart with SMAs, Bollinger Bands, RSI, and key levels"
```

---

## Task 10: UI Components

**Files:**
- Create: `ui/components.py`

- [ ] **Step 1: Implement ui/components.py**

```python
from typing import List, Optional
import streamlit as st
import pandas as pd
from analysis.decision_engine import Decision
from analysis.technicals import TechnicalSnapshot
from data.price_fetcher import PriceData
from data.macro_scraper import MacroData
from data.rbi_scraper import RBIData
from data.news_fetcher import NewsItem


def render_decision_box(decision: Decision, spot: Optional[float]) -> None:
    color = decision.color
    st.markdown(f"""
    <div style="
        background: {color}22;
        border: 2px solid {color};
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 20px;
    ">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
            <div>
                <div style="font-size:0.85rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.1em;">
                    Hedge Recommendation
                </div>
                <div style="font-size:2rem; font-weight:800; color:{color}; line-height:1.2;">
                    {decision.recommendation}
                </div>
                <div style="font-size:0.95rem; color:#e2e8f0; margin-top:6px;">
                    {decision.rationale}
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:1.5rem; font-weight:700; color:#f8fafc;">
                    {decision.hedge_ratio}% hedge
                </div>
                <div style="font-size:0.85rem; color:#94a3b8;">
                    Confidence: <span style="color:{color}; font-weight:600;">{decision.confidence}</span>
                </div>
                <div style="font-size:0.85rem; color:#94a3b8; margin-top:4px;">
                    Signal score: {decision.score:+.0f}
                </div>
            </div>
        </div>
        <div style="margin-top:12px; border-top:1px solid {color}44; padding-top:10px;">
            <div style="font-size:0.8rem; color:#94a3b8;">Spot: <b style="color:#f1f5f9;">{f"₹{spot:.4f}" if spot else "N/A"}</b></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_signal_breakdown(decision: Decision) -> None:
    with st.expander("Signal Breakdown", expanded=False):
        for sig in sorted(decision.signals, key=lambda s: abs(s.weight), reverse=True):
            icon = "🟢" if sig.weight < 0 else "🔴"
            direction = "→ WAIT" if sig.weight < 0 else "→ COVER"
            st.markdown(
                f"{icon} **[{sig.weight:+d}]** {direction} — {sig.description}"
            )
        if not decision.signals:
            st.info("No active signals generated.")


def render_technical_summary(tech: TechnicalSnapshot, futures_near: Optional[float], futures_basis: Optional[float]) -> None:
    st.subheader("Spot & Technical Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("USD/INR Spot", f"{tech.spot:.4f}")
    c2.metric("RSI (14 Daily)", f"{tech.rsi_daily:.1f}" if tech.rsi_daily else "N/A")
    c3.metric("RSI (14 Weekly)", f"{tech.rsi_weekly:.1f}" if tech.rsi_weekly else "N/A")
    c4.metric("ATR (14)", f"{tech.atr_14:.4f}" if tech.atr_14 else "N/A",
              delta=f"90d avg: {tech.atr_90d_avg:.4f}" if tech.atr_90d_avg else None)

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("SMA 50", f"{tech.sma_50:.4f}" if tech.sma_50 else "N/A",
              delta=f"{tech.pct_above_sma50:+.2f}%" if tech.pct_above_sma50 else None)
    c6.metric("SMA 200", f"{tech.sma_200:.4f}" if tech.sma_200 else "N/A",
              delta=f"{tech.pct_above_sma200:+.2f}%" if tech.pct_above_sma200 else None)
    c7.metric("BB %B", f"{tech.bb_pct_b*100:.1f}%" if tech.bb_pct_b is not None else "N/A")
    near_label = f"{futures_near:.4f}" if futures_near else "N/A"
    basis_label = f"Basis: {futures_basis:+.4f}" if futures_basis else None
    c8.metric("Futures (Near)", near_label, delta=basis_label)


def render_key_levels_table(tech: TechnicalSnapshot, levels: List[dict]) -> None:
    st.subheader("Key Levels")
    spot = tech.spot
    rows = []
    for lvl in levels:
        price = lvl["price"]
        if price <= 0:
            continue
        dist_pct = (spot - price) / price * 100
        if abs(dist_pct) < 0.5:
            traffic = "🔴"
        elif abs(dist_pct) < 2.0:
            traffic = "🟡"
        else:
            traffic = "🟢"
        direction = "▲ Above" if dist_pct > 0 else "▼ Below"
        rows.append({
            "": traffic,
            "Level": lvl["name"],
            "Price": f"{price:.4f}",
            "Type": lvl.get("type", "").capitalize(),
            "Distance": f"{dist_pct:+.2f}%",
            "Position": direction,
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_macro_panel(price: PriceData, macro: MacroData, rbi: RBIData) -> None:
    st.subheader("Macro Dashboard")

    def fmt(val, decimals=2, suffix=""):
        return f"{val:.{decimals}f}{suffix}" if val is not None else "N/A"

    rows = [
        {"Indicator": "DXY (Dollar Index)",     "Value": fmt(price.dxy),         "Hedge Signal": "⬆ WAIT" if price.dxy and price.dxy > 104 else "⬇ COVER"},
        {"Indicator": "Brent Crude ($/bbl)",     "Value": fmt(price.brent),       "Hedge Signal": "⬆ WAIT" if price.brent and price.brent > 85 else "—"},
        {"Indicator": "WTI Crude ($/bbl)",       "Value": fmt(price.wti),         "Hedge Signal": "—"},
        {"Indicator": "US 10Y Yield (%)",        "Value": fmt(price.us_10y_yield),"Hedge Signal": "⬆ WAIT" if price.us_10y_yield and price.us_10y_yield > 4.5 else "—"},
        {"Indicator": "India 10Y Yield (%)",     "Value": fmt(macro.india_10y_yield), "Hedge Signal": "—"},
        {"Indicator": "Yield Diff (IN-US) bps",
            "Value": fmt((macro.india_10y_yield or 0) - (price.us_10y_yield or 0), decimals=0, suffix="bps"), "Hedge Signal": "—"},
        {"Indicator": "Nifty 50",                "Value": fmt(price.nifty, 0),    "Hedge Signal": "—"},
        {"Indicator": "US VIX",                  "Value": fmt(price.us_vix),      "Hedge Signal": "⬆ COVER" if price.us_vix and price.us_vix > 25 else "—"},
        {"Indicator": "India VIX",               "Value": fmt(macro.india_vix),   "Hedge Signal": "⬆ COVER" if macro.india_vix and macro.india_vix < 14 else "—"},
        {"Indicator": "RBI Repo Rate (%)",       "Value": fmt(rbi.repo_rate),     "Hedge Signal": "—"},
        {"Indicator": "FX Reserves (USD bn)",    "Value": fmt(rbi.fx_reserves_usd_bn, 1), "Hedge Signal": "—"},
        {"Indicator": "FII Net Equity (₹Cr)",   "Value": fmt(macro.fii_equity_net_crore, 0),
            "Hedge Signal": "⬆ COVER" if macro.fii_equity_net_crore and macro.fii_equity_net_crore > 1000 else
                            ("⬆ WAIT" if macro.fii_equity_net_crore and macro.fii_equity_net_crore < -1000 else "—")},
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_news_panel(news: List[NewsItem]) -> None:
    st.subheader("News & Sentiment (Last 24h)")
    if not news:
        st.info("No recent news fetched.")
        return
    flagged = [n for n in news if n.flagged]
    if flagged:
        st.warning(f"⚠ {len(flagged)} headline(s) flagged for key terms")
    for item in news:
        prefix = "🚨 " if item.flagged else ""
        tags = " ".join(f"`{kw}`" for kw in item.matched_keywords) if item.flagged else ""
        st.markdown(f"**{prefix}[{item.title}]({item.url})**  {tags}  \n*{item.published}*")
        st.divider()


def render_history_table(history: List[dict]) -> None:
    st.subheader("Decision History")
    if not history:
        st.info("No historical snapshots yet. Check back after the first daily run.")
        return
    df = pd.DataFrame(history)[
        ["date", "usdinr_spot", "recommendation", "hedge_ratio", "confidence", "rsi_daily", "dxy", "score"]
    ].rename(columns={
        "date": "Date", "usdinr_spot": "Spot", "recommendation": "Rec",
        "hedge_ratio": "Hedge %", "confidence": "Conf",
        "rsi_daily": "RSI", "dxy": "DXY", "score": "Score",
    })
    st.dataframe(df, use_container_width=True, hide_index=True)
```

- [ ] **Step 2: Commit**

```bash
git add ui/components.py
git commit -m "feat: Streamlit UI components — decision box, tables, macro panel, news feed"
```

---

## Task 11: Main Dashboard

**Files:**
- Create: `dashboard.py`

- [ ] **Step 1: Implement dashboard.py**

```python
import json
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from config import DEFAULT_LEVELS, DB_PATH
from data.price_fetcher import fetch_price_data
from data.nse_scraper import fetch_nse_futures
from data.rbi_scraper import fetch_rbi_data
from data.macro_scraper import fetch_macro_data
from data.news_fetcher import fetch_news
from analysis.technicals import compute_technicals
from analysis.signals import generate_signals
from analysis.decision_engine import make_decision
from storage.db import init_db, save_snapshot, get_history
from ui.charts import build_usdinr_chart
from ui.components import (
    render_decision_box,
    render_signal_breakdown,
    render_technical_summary,
    render_key_levels_table,
    render_macro_panel,
    render_news_panel,
    render_history_table,
)

st.set_page_config(
    page_title="USD/INR Hedge Dashboard",
    page_icon="💱",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { background-color: #0f172a; color: #e2e8f0; }
    .stMetric { background: #1e293b; border-radius: 8px; padding: 8px; }
    [data-testid="stSidebar"] { background-color: #1e293b; }
    .stDataFrame { font-size: 0.85rem; }
    h1, h2, h3 { color: #f1f5f9; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙ Controls")
    st.markdown("**Exposure Settings**")
    monthly_receivable_usd = st.number_input(
        "Monthly Receivables (USD)", value=500_000, step=50_000, format="%d"
    )
    usdinr_rate_assumed = st.number_input(
        "Assumed INR rate for budgeting", value=93.0, step=0.25
    )

    st.markdown("---")
    st.markdown("**Key Levels (editable)**")
    levels = []
    for i, default in enumerate(DEFAULT_LEVELS):
        if default["type"] == "dynamic":
            continue
        name  = st.text_input(f"Level {i+1} name",  value=default["name"],  key=f"lname_{i}")
        price = st.number_input(f"Level {i+1} price", value=default["price"], step=0.25, key=f"lprice_{i}")
        ltype = st.selectbox(f"Level {i+1} type", ["resistance", "support"], key=f"ltype_{i}",
                             index=0 if default["type"] == "resistance" else 1)
        levels.append({"name": name, "price": price, "type": ltype})

    st.markdown("---")
    st.markdown("**Chart Settings**")
    lookback_months = st.slider("Chart lookback (months)", 1, 24, 6)

    st.markdown("---")
    refresh = st.button("🔄 Refresh Data", use_container_width=True)
    st.caption(f"Last refreshed: {datetime.now().strftime('%d %b %Y, %H:%M IST')}")


# ── Data loading (cached 30 min) ───────────────────────────────────────────────

@st.cache_data(ttl=1800)
def load_all_data():
    price   = fetch_price_data()
    futures = fetch_nse_futures(spot_price=price.usdinr_spot)
    rbi     = fetch_rbi_data()
    macro   = fetch_macro_data()
    news    = fetch_news()
    return price, futures, rbi, macro, news


if refresh:
    st.cache_data.clear()

price, futures, rbi, macro, news = load_all_data()


# ── Technical Analysis ─────────────────────────────────────────────────────────

if price.usdinr_history.empty:
    st.error("Could not load USD/INR price history. Check your internet connection.")
    st.stop()

tech = compute_technicals(price.usdinr_history)

# 5-day momentum calculations
def _5d_change(df: pd.DataFrame) -> float | None:
    if df is None or df.empty or len(df) < 6:
        return None
    return float((df["Close"].iloc[-1] / df["Close"].iloc[-6] - 1) * 100)

dxy_5d   = _5d_change(price.dxy_history)
brent_5d = _5d_change(price.brent_history)

us_yield_5d = None
if price.us_10y_yield is not None and not price.usdinr_history.empty:
    pass  # No history for TNX, rely on snapshot only

# Inject dynamic 200 SMA level
if tech.sma_200:
    levels.append({"name": "200 DMA", "price": round(tech.sma_200, 4), "type": "dynamic"})


# ── Decision Engine ────────────────────────────────────────────────────────────

signals  = generate_signals(tech, price, macro, news, dxy_5d_change=dxy_5d, brent_5d_change=brent_5d)
decision = make_decision(signals)


# ── Persist daily snapshot ─────────────────────────────────────────────────────

init_db()
today = datetime.now().strftime("%Y-%m-%d")
snapshot = {
    "date":           today,
    "usdinr_spot":    tech.spot,
    "rsi_daily":      tech.rsi_daily,
    "dxy":            price.dxy,
    "brent":          price.brent,
    "recommendation": decision.recommendation,
    "hedge_ratio":    decision.hedge_ratio,
    "confidence":     decision.confidence,
    "rationale":      decision.rationale,
    "score":          decision.score,
    "raw_json":       json.dumps({
        "tech": vars(tech),
        "futures": vars(futures),
        "macro":  vars(macro),
    }, default=str),
}
save_snapshot(snapshot)
history = get_history(n=30)


# ── Layout ─────────────────────────────────────────────────────────────────────

st.title("💱 USD/INR Hedging Dashboard")
st.caption(f"For exporters with USD receivables — {datetime.now().strftime('%A, %d %B %Y')}")

# Section 1 — Decision Box
render_decision_box(decision, tech.spot)
render_signal_breakdown(decision)

# P&L at risk callout
if decision.hedge_ratio > 0 and monthly_receivable_usd:
    spot   = tech.spot or usdinr_rate_assumed
    budget = usdinr_rate_assumed
    unhedged_usd = monthly_receivable_usd * (1 - decision.hedge_ratio / 100)
    downside_inr = unhedged_usd * (spot - (spot * 0.97))  # 3% adverse move
    st.info(
        f"**Exposure context:** Monthly receivables ≈ USD {monthly_receivable_usd:,.0f}. "
        f"At {decision.hedge_ratio}% hedge, unhedged exposure = USD {unhedged_usd:,.0f}. "
        f"A 3% adverse move (INR strengthens) on unhedged portion = **₹{downside_inr:,.0f} loss**."
    )

st.divider()

# Section 2 — Technical Summary
render_technical_summary(tech, futures.near_month_price, futures.near_month_basis)
st.plotly_chart(
    build_usdinr_chart(price.usdinr_history, tech, levels, lookback_months),
    use_container_width=True,
)

st.divider()

# Section 3 — Key Levels
render_key_levels_table(tech, levels)

st.divider()

# Section 4 — Macro Dashboard
render_macro_panel(price, macro, rbi)

st.divider()

# Section 5 — News
render_news_panel(news)

st.divider()

# Section 6 — Decision History
render_history_table(history)

st.divider()

# Section 7 — Log manual decision
with st.expander("Log today's actual decision"):
    action = st.selectbox("Action taken", ["WAIT", "Hedged 25%", "Hedged 50%", "Hedged 75%", "Hedged 100%"])
    pct    = st.slider("Hedge %", 0, 100, 0, step=25)
    notes  = st.text_area("Notes (optional)")
    if st.button("Save Decision"):
        from storage.db import save_decision
        save_decision({"date": today, "action_taken": action, "hedge_pct": pct, "notes": notes})
        st.success("Decision logged.")
```

- [ ] **Step 2: Commit**

```bash
git add dashboard.py
git commit -m "feat: main Streamlit dashboard wiring all data, analysis, and UI components"
```

---

## Task 12: Smoke Test + README

**Files:**
- Create: `tests/test_smoke.py`

- [ ] **Step 1: Write smoke test**

Create `tests/test_smoke.py`:

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from data.price_fetcher import PriceData
from data.macro_scraper import MacroData
from data.rbi_scraper import RBIData
from data.nse_scraper import FuturesData
from analysis.technicals import compute_technicals
from analysis.signals import generate_signals
from analysis.decision_engine import make_decision

def make_test_df(n=260, start=94.0):
    np.random.seed(7)
    prices = [start]
    for _ in range(n - 1):
        prices.append(prices[-1] * (1 + np.random.normal(0.0002, 0.003)))
    dates = pd.date_range("2024-06-01", periods=n, freq="B")
    return pd.DataFrame({
        "Open":   [p * 0.999 for p in prices],
        "High":   [p * 1.002 for p in prices],
        "Low":    [p * 0.998 for p in prices],
        "Close":  prices,
        "Volume": [1_000_000] * n,
    }, index=dates)

def test_full_pipeline_runs_without_error():
    df = make_test_df()
    tech = compute_technicals(df)
    price = PriceData(usdinr_spot=tech.spot, dxy=104.2, brent=82.5, us_10y_yield=4.35, us_vix=17.5)
    macro = MacroData(india_10y_yield=7.05, india_vix=14.0, fii_equity_net_crore=1200)
    signals = generate_signals(tech, price, macro, [], dxy_5d_change=-0.8, brent_5d_change=1.5)
    decision = make_decision(signals)
    assert decision.recommendation in ("WAIT", "WAIT WITH ALERT", "COVER PARTIAL", "COVER NOW")
    assert 0 <= decision.hedge_ratio <= 100
    assert len(decision.rationale) > 5

def test_decision_box_import():
    from ui.components import render_decision_box
    assert callable(render_decision_box)

def test_chart_import():
    from ui.charts import build_usdinr_chart
    assert callable(build_usdinr_chart)

def test_db_round_trip():
    from storage.db import init_db, save_snapshot, get_history
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = f.name
    try:
        init_db(db)
        save_snapshot({
            "date": "2026-05-03", "usdinr_spot": 94.95, "rsi_daily": 68.0,
            "dxy": 104.2, "brent": 82.5, "recommendation": "COVER PARTIAL",
            "hedge_ratio": 50, "confidence": "Medium",
            "rationale": "Test", "score": 5, "raw_json": "{}",
        }, db_path=db)
        hist = get_history(5, db_path=db)
        assert hist[0]["hedge_ratio"] == 50
    finally:
        os.unlink(db)
```

- [ ] **Step 2: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: All tests PASS. (Any test that fails due to live network data is acceptable — mock-based tests must all pass.)

- [ ] **Step 3: Verify dashboard starts**

```bash
streamlit run dashboard.py --server.headless true &
sleep 5
curl -s http://localhost:8501 | grep -q "USD/INR" && echo "DASHBOARD OK" || echo "CHECK LOGS"
pkill -f "streamlit run"
```

Expected: `DASHBOARD OK`

- [ ] **Step 4: Final commit**

```bash
git add tests/test_smoke.py
git commit -m "test: smoke tests covering full data → decision pipeline and DB round-trip"
```

---

## Self-Review: Spec Coverage Check

| Spec Requirement | Covered in Task |
|---|---|
| Streamlit single-page, mobile-friendly | Task 11 — `st.set_page_config(layout="wide")` + responsive columns |
| `streamlit run dashboard.py` entrypoint | Task 11 |
| USD/INR spot (yfinance INR=X) | Task 3 |
| DXY, EUR-USD, Brent, WTI, US 10Y, Nifty, VIX | Task 3 |
| NSE current + next month futures | Task 4 |
| Futures basis vs spot | Task 4 |
| India 10Y yield | Task 5 |
| RBI repo rate | Task 5 |
| India VIX | Task 5 |
| FII equity flows | Task 5 |
| FX reserves | Task 5 |
| Reuters RSS + keyword flagging | Task 6 |
| RBI press releases | Task 5 |
| RSI(14) daily + weekly | Task 7 |
| Bollinger Bands + %B | Task 7 |
| ATR(14) vs 90d avg + elevated flag | Task 7 |
| SMA 50/200 + % distance | Task 7 |
| Decision box (color-coded, 4 states) | Task 8 + Task 10 |
| Hedge ratio 0/25/50/75/100% | Task 8 |
| Confidence Low/Medium/High | Task 8 |
| One-sentence rationale | Task 8 |
| Candlestick chart 6M with SMAs + BBs + RSI | Task 9 |
| Configurable support/resistance levels | Tasks 10 + 11 sidebar |
| Key levels table with traffic light | Task 10 |
| Macro dashboard table | Task 10 |
| India fundamentals panel | Task 10 |
| News/sentiment feed + flagged keywords | Task 6 + Task 10 |
| SQLite daily snapshots | Task 2 |
| Decision history view | Tasks 2 + 10 |
| P&L at risk exposure callout | Task 11 |
| Log manual decision | Task 11 |
| `.env` + python-dotenv | Task 1 |
| Mobile-friendly (Streamlit default responsive) | Task 11 |

No gaps found.
