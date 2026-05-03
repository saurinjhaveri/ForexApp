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
    # ── Resistance: levels above spot where USD/INR tends to stall/reverse ──────
    # RBI has historically defended ~95.20; a break higher = strong USD rally
    {"name": "RBI Defence / ATH",  "price": 95.20, "type": "resistance"},
    # Round-number psychological barrier; often acts as near-term cap
    {"name": "Psych Resistance",   "price": 95.00, "type": "resistance"},

    # ── Support: levels below spot where INR tends to stabilise ─────────────────
    # Typical FY26-27 export budget rate; below this you're booking a loss
    # vs your assumed rate — the most important level for an exporter
    {"name": "Budget / Hedge Rate","price": 93.00, "type": "support"},
    # Strong technical support — multiple bounces in 2024-25; break = trend change
    {"name": "Strong Support",     "price": 91.50, "type": "support"},
    # Major psychological floor; breach signals rupee crisis territory
    {"name": "Danger Zone",        "price": 90.00, "type": "support"},

    # ── Dynamic: computed at runtime from live price data ────────────────────────
    {"name": "200 DMA",            "price": 0.0,   "type": "dynamic"},
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
REUTERS_INDIA_RSS     = "https://feeds.reuters.com/reuters/INbusinessNews"
NSE_CURRENCY_URL      = "https://www.nseindia.com/api/quote-derivative?symbol=USDINR"
WORLDGOVBONDS_INDIA   = "https://worldgovernmentbonds.com/country/india/"

FLAG_KEYWORDS = [
    "rbi intervention", "rate cut", "fii outflow", "fii inflow",
    "trade deal", "tariff", "fed", "iran", "oil sanctions",
    "rupee", "dollar", "forex", "foreign exchange", "intervention",
]

DB_PATH = "forex_dashboard.db"
