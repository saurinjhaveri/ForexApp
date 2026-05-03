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


SIGNAL_WEIGHTS = {
    # ── Exhaustion / reversal risk (positive = sell forward to lock in bonus) ────
    "weekly_rsi_overbought":    +3,   # Weekly RSI > 70 — strongest mean-reversion signal
    "rsi_overbought":           +2,   # Daily RSI > 70
    "rsi_moderately_high":      +1,   # Daily RSI 60-70 — momentum elevated but not extreme
    "rsi_oversold":             -2,   # Daily RSI < 40 — bounce likely, hold open
    "bb_upper_breach":          +2,   # Price in upper Bollinger Band — stretched
    "bb_lower_breach":          -1,   # Price near lower band — hold, may bounce
    "extreme_above_200sma":     +2,   # >5% above 200 DMA — historically extended, mean-reversion likely
    "moderately_above_200sma":  +1,   # 2-5% above 200 DMA — elevated but not extreme
    "high_volatility":          +1,   # ATR elevated — heightened two-way risk

    # ── DXY: global dollar direction ─────────────────────────────────────────────
    "dxy_weak_level":           +2,   # DXY < 100 — dollar soft globally; INR weakness is India-specific
    "dxy_usdinr_divergence":    +3,   # DXY falling WHILE USD/INR rising — INR-specific weakness snaps back fast
    "dxy_falling":              +2,   # DXY 5d momentum negative
    "dxy_strong_level":         -1,   # DXY > 104 — genuine broad dollar strength
    "dxy_rising":               -2,   # DXY 5d momentum positive — USD strengthening globally

    # ── USD/INR price momentum ────────────────────────────────────────────────────
    "usdinr_momentum_strong":   -2,   # USD/INR 5d > +0.5% — trend intact, wait for more
    "usdinr_momentum_fading":   +1,   # USD/INR 5d between -0.2% and +0.2% — losing steam
    "usdinr_momentum_negative": +2,   # USD/INR 5d negative — reversal underway

    # ── India macro ───────────────────────────────────────────────────────────────
    "oil_falling":              +1,   # Brent falling — less INR import pressure, INR can strengthen
    "oil_rising":               -1,   # Brent rising — imports pressure INR, USD/INR stays bid
    "fii_inflow_strong":        +2,   # FII buying India equities — INR demand, sell USD high
    "fii_outflow_strong":       -2,   # FII selling — INR under pressure, hold
    "us_yield_falling":         +1,   # US yields down — USD softening
    "us_yield_rising":          -1,   # US yields up — USD supported

    # ── Event / intervention ──────────────────────────────────────────────────────
    "rbi_intervention_signal":  +2,   # RBI selling USD — explicit cap, don't fight it

    # ── Key level proximity / breakout ────────────────────────────────────────────
    "near_key_resistance":      +2,   # Spot within 0.35% below a resistance — classic sell zone
    "broke_above_resistance":   -2,   # Spot just broke above resistance — momentum continuation
    "near_key_support":         -1,   # Spot within 0.35% above a support — hold, bounce expected
    "broke_below_support":      +3,   # Spot just broke below support — INR weakness accelerating, sell now
}

HEDGE_THRESHOLDS = [
    # score → action for opportunistic exporter (budget rate ≈ ₹90, spot ≈ ₹94-95)
    (0,   "HOLD — Let It Run",  0,   "Low"),     # no reversal signals — ride the USD strength
    (3,   "SELL 25% FORWARD",  25,  "Low"),      # early warning — take some off the table
    (5,   "SELL 50% FORWARD",  50,  "Medium"),   # mixed signals — lock in half the bonus
    (8,   "SELL 75% FORWARD",  75,  "High"),     # strong reversal risk — protect most of the gain
    (11,  "SELL ALL FORWARD", 100,  "High"),     # all signals flashing — sell everything now
]

DECISION_COLORS = {
    "HOLD — Let It Run":  "#1a7f37",
    "SELL 25% FORWARD":   "#ca8a04",
    "SELL 50% FORWARD":   "#d97706",
    "SELL 75% FORWARD":   "#dc2626",
    "SELL ALL FORWARD":   "#991b1b",
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
