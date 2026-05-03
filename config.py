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
    # ── Exhaustion / reversal risk ────────────────────────────────────────────────
    # Aggressive stance: sell signals hit harder; even mild overbought conditions matter
    "weekly_rsi_overbought":    +4,   # Weekly RSI > 70 — primary mean-reversion signal (was +3)
    "rsi_overbought":           +3,   # Daily RSI > 70 (was +2)
    "rsi_moderately_high":      +2,   # Daily RSI 55-70 — elevated enough to act on aggressively (was +1)
    "rsi_oversold":             -2,   # Daily RSI < 40 — only strong enough to pause, not stop
    "bb_upper_breach":          +3,   # Price in upper Bollinger Band — stretched, lock in (was +2)
    "bb_lower_breach":          -1,   # Near lower band — minor hold signal only
    "extreme_above_200sma":     +3,   # >5% above 200 DMA — historically unsustainable (was +2)
    "moderately_above_200sma":  +2,   # 2-5% above 200 DMA — still elevated, sell into it (was +1)
    "high_volatility":          +1,   # ATR elevated — two-way risk; protect the gain

    # ── DXY: global dollar direction ──────────────────────────────────────────────
    "dxy_weak_level":           +3,   # DXY < 100 — INR weakness is India-specific, snaps back fast (was +2)
    "dxy_usdinr_divergence":    +4,   # DXY falling + USD/INR rising — strongest sell trigger (was +3)
    "dxy_falling":              +3,   # DXY 5d momentum down (was +2)
    "dxy_strong_level":         -1,   # DXY > 104 — some global USD support, minor offset
    "dxy_rising":               -1,   # DXY momentum up — aggressive hedger doesn't let this stop selling (was -2)

    # ── USD/INR price momentum ────────────────────────────────────────────────────
    # Aggressive: short-term uptrend is NOT a reason to hold back — it's a better sell price
    "usdinr_momentum_strong":   -1,   # USD/INR 5d > +0.5% — trend up, but still sell into strength (was -2)
    "usdinr_momentum_fading":   +2,   # Momentum fading — act before reversal is confirmed (was +1)
    "usdinr_momentum_negative": +3,   # Reversal underway — sell urgently (was +2)

    # ── India macro ───────────────────────────────────────────────────────────────
    "oil_falling":              +2,   # Oil down → INR can strengthen; lock in USD now (was +1)
    "oil_rising":               -1,   # Oil up → minor support for USD/INR
    "fii_inflow_strong":        +3,   # FII buying India → INR demand incoming (was +2)
    "fii_outflow_strong":       -1,   # FII selling → still sell, just with less urgency (was -2)
    "us_yield_falling":         +1,   # US yields down — USD softening
    "us_yield_rising":          -1,   # US yields up — USD supported

    # ── Event / intervention ──────────────────────────────────────────────────────
    "rbi_intervention_signal":  +3,   # RBI selling USD — explicit cap, sell alongside RBI (was +2)

    # ── Key level proximity / breakout ────────────────────────────────────────────
    "near_key_resistance":      +3,   # Approaching resistance — prime sell zone (was +2)
    "broke_above_resistance":   -1,   # Broke above — momentum intact, but still lean sell (was -2)
    "near_key_support":         -1,   # Near support — minor caution only
    "broke_below_support":      +4,   # Broke below support — sell urgently (was +3)

    # ── Futures open interest positioning ────────────────────────────────────────
    "oi_longs_building":        +2,   # OI up + price up → new longs; crowded, fragile
    "oi_short_covering":        +1,   # OI down + price up → covering only; weaker move
    "oi_longs_unwinding":       +3,   # OI down + price down → longs exiting; reversal confirmed
    "oi_crowded_buildup":       +3,   # OI >15% above 20d avg → structurally crowded, sell into it
}

HEDGE_THRESHOLDS = [
    # Aggressive on STARTING to hedge (low triggers for 25/50%),
    # but requires clear multi-factor confirmation for 75/100%.
    # "Stretched conditions" = 50%. "Confirmed reversal catalyst" = 75-100%.
    (0,  "HOLD — Let It Run",   0,  "Low"),     # Active hold signals dominate
    (2,  "SELL 25% FORWARD",   25,  "Medium"),  # Any early warning → start locking in
    (5,  "SELL 50% FORWARD",   50,  "Medium"),  # Multiple signals aligned → half hedged
    (11, "SELL 75% FORWARD",   75,  "High"),    # Strong multi-factor case → protect most
    (16, "SELL ALL FORWARD",  100,  "High"),    # All signals + reversal catalyst → full hedge
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
