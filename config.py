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
    # Design principle:
    #   Background / structural signals  → weight +1  (context, not action triggers)
    #   Momentum / confirmation signals   → weight +2  (adds to case)
    #   High-conviction reversal triggers → weight +3/+4  (rare, specific, actionable)
    # Prevents correlated signals (e.g. DXY weak + DXY falling + DXY divergence) from
    # stacking into extreme scores.

    # ── Exhaustion / reversal risk ────────────────────────────────────────────────
    "weekly_rsi_overbought":    +4,   # Weekly RSI > 70 — strongest mean-reversion signal; rare + predictive
    "rsi_overbought":           +2,   # Daily RSI > 70 — overbought short-term
    "rsi_moderately_high":      +1,   # Daily RSI 55-70 — background context
    "rsi_oversold":             -2,   # Daily RSI < 40 — bounce likely
    "bb_upper_breach":          +2,   # Price near upper Bollinger Band — stretched
    "bb_lower_breach":          -1,   # Near lower band — bounce risk
    "extreme_above_200sma":     +2,   # >5% above 200 DMA — historically extended
    "moderately_above_200sma":  +1,   # 2-5% above 200 DMA — context, not trigger alone
    "high_volatility":          +1,   # ATR elevated — two-way risk

    # ── DXY: global dollar direction ──────────────────────────────────────────────
    # dxy_usdinr_divergence is the SPECIFIC trigger; weak_level + falling are background
    "dxy_usdinr_divergence":    +4,   # DXY falling WHILE USD/INR rising — India-specific weakness
    "dxy_weak_level":           +1,   # DXY < 100 — structural context; not an action trigger alone
    "dxy_falling":              +1,   # DXY 5d down — background momentum
    "dxy_strong_level":         -2,   # DXY > 104 — genuine broad USD strength
    "dxy_rising":               -2,   # DXY 5d up — dollar has momentum

    # ── USD/INR price momentum ────────────────────────────────────────────────────
    "usdinr_momentum_strong":   -2,   # USD/INR 5d > +0.5% — trend intact; wait for turn
    "usdinr_momentum_fading":   +2,   # Momentum fading — hedge before reversal confirmed
    "usdinr_momentum_negative": +3,   # Reversal already underway — act now

    # ── India macro ───────────────────────────────────────────────────────────────
    "oil_falling":              +1,   # Oil down → INR can strengthen
    "oil_rising":               -1,   # Oil up → USD/INR stays bid
    "fii_inflow_strong":        +2,   # FII buying India equities → INR demand
    "fii_outflow_strong":       -2,   # FII selling → INR under pressure
    "us_yield_falling":         +1,   # US yields down — USD softening
    "us_yield_rising":          -1,   # US yields up — USD supported

    # ── Event / intervention ──────────────────────────────────────────────────────
    "rbi_intervention_signal":  +3,   # RBI selling USD — explicit cap; high-conviction

    # ── Key level proximity / breakout ────────────────────────────────────────────
    "near_key_resistance":      +2,   # Approaching resistance — sell zone
    "broke_above_resistance":   -2,   # Broke above — momentum intact
    "near_key_support":         -1,   # Near support — bounce risk
    "broke_below_support":      +4,   # Broke below support — reversal confirmed; sell urgently

    # ── Futures open interest positioning ────────────────────────────────────────
    "oi_longs_building":        +2,   # OI up + price up → crowded longs, fragile
    "oi_short_covering":        +1,   # OI down + price up → covering only, weaker
    "oi_longs_unwinding":       +3,   # OI down + price down → reversal confirmed
    "oi_crowded_buildup":       +3,   # OI >15% above avg → structurally crowded
}

HEDGE_THRESHOLDS = [
    # Score guide (typical ranges):
    #   Mildly stretched (RSI 60s, BB elevated):               ~4-6   → SELL 25-50%
    #   Strong case (weekly RSI OB + DXY divergence + FII):    ~12-20 → SELL 50-75%
    #   Reversal confirmed (above + broke support / OI crowd):  22+   → SELL 100%
    (0,  "HOLD — Let It Run",   0,  "Low"),
    (3,  "SELL 25% FORWARD",   25,  "Medium"),
    (6,  "SELL 50% FORWARD",   50,  "Medium"),
    (12, "SELL 75% FORWARD",   75,  "High"),
    (22, "SELL ALL FORWARD",  100,  "High"),
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
