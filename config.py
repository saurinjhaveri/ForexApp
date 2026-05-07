TICKERS = {
    "usdinr_spot": "INR=X",
    "dxy": "DX-Y.NYB",
    "eurusd": "EURUSD=X",
    "brent": "BZ=F",
    "wti": "CL=F",
    "us_10y": "^TNX",
    "nifty": "^NSEI",
    "us_vix": "^VIX",
    # EM basket for relative INR divergence
    "usdbrl": "BRL=X",
    "usdzar": "ZAR=X",
    "usdidr": "IDR=X",
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

    # ── EM basket relative divergence ────────────────────────────────────────────
    # If INR underperforms EM peers, the weakness is India-specific — snaps back faster
    "inr_em_divergence_strong": +3,   # INR weaker than EM basket >0.5% in 5d — India-specific weakness
    "inr_em_outperforming":     -1,   # INR outperforming EM basket — broad USD move, not India-specific

    # ── Forward premium / carry ───────────────────────────────────────────────────
    # Exporter EARNS the premium — high premium = better forward rate = MORE reason to hedge
    "forward_premium_extreme":      +3,   # Annualized premium >90th pctile of 90d history — market screaming INR weakness
    "forward_premium_high_pctile":  +2,   # Premium >75th pctile — above-average carry confirms hedging attractive
    "forward_premium_collapsed":    -1,   # Premium near zero / below 25th pctile — carry benefit thin; less urgency

    # ── India macro ───────────────────────────────────────────────────────────────
    "oil_falling":              +1,   # Oil down → INR can strengthen
    "oil_rising":               -1,   # Oil up → USD/INR stays bid
    "fii_inflow_strong":        +2,   # FII buying India equities → INR demand
    "fii_outflow_strong":       -2,   # FII selling → INR under pressure
    "us_yield_falling":         +1,   # US yields down — USD softening
    "us_yield_rising":          -1,   # US yields up — USD supported

    # ── RBI intervention ─────────────────────────────────────────────────────────
    "rbi_intervention_signal":  +3,   # RBI selling USD (news-based) — explicit cap; high-conviction
    "rbi_intervention_zone":    +2,   # Spot in known RBI intervention zone (94.50–95.00) — defence expected
    "rbi_intervention_active":  +4,   # Spot above 95.00 — RBI historically defends hard; reversal imminent
    "fx_reserves_falling_confirmed": +2,  # Reserves falling AND INR underperforming EM — confirmed deployment

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

    # ── MACD (12/26/9) ────────────────────────────────────────────────────────────
    "macd_bearish_cross":          +2,   # MACD line crossed below signal — momentum turning down
    "macd_bullish_cross":          -2,   # MACD line crossed above signal — momentum turning up

    # ── ADX (14) ─────────────────────────────────────────────────────────────────
    "adx_trending_bearish":        +2,   # ADX > 25 AND -DI > +DI — strong downtrend confirmed
    "adx_trending_bullish":        -2,   # ADX > 25 AND +DI > -DI — strong uptrend confirmed
    "adx_ranging":                 +1,   # ADX < 20 — no clear trend; reversal-prone zone

    # ── Stochastic RSI (14,14,3,3) ───────────────────────────────────────────────
    "stochrsi_overbought_bearish": +2,   # StochRSI K > 80 and K < D (topping) — precision short entry
    "stochrsi_oversold":           -1,   # StochRSI K < 20 — oversold, bounce likely

    # ── EMA 9 / 21 crossover ─────────────────────────────────────────────────────
    "ema_bearish_cross":           +2,   # EMA 9 crossed below EMA 21 — short-term momentum turned down
    "ema_bullish_cross":           -2,   # EMA 9 crossed above EMA 21 — short-term momentum turned up
    "ema_bearish_stack":           +1,   # Price < EMA9 < EMA21 — bearish short-term stack
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

GOLD_TICKERS = {
    "xauusd":  "GC=F",    # COMEX gold futures (most liquid spot proxy)
    "silver":  "SI=F",    # Silver futures (for Gold/Silver ratio)
}

GOLD_SIGNAL_WEIGHTS = {
    # Design principle: same tier hierarchy as USD/INR.
    # Positive = SELL forward (lock in gold price). Negative = HOLD.

    # ── Technical exhaustion ──────────────────────────────────────────────────────
    "gold_weekly_rsi_overbought":  +4,   # Weekly RSI > 70 — strongest reversal warning
    "gold_rsi_overbought":         +2,   # Daily RSI > 70
    "gold_rsi_moderately_high":    +1,   # Daily RSI 55–70 — background context
    "gold_rsi_oversold":           -2,   # RSI < 40 — bounce likely, hold
    "gold_bb_upper_breach":        +2,   # Near upper Bollinger Band — stretched
    "gold_bb_lower_breach":        -1,   # Near lower band — oversold bounce
    "gold_extreme_above_200sma":   +2,   # >5% above 200 DMA — historically extended
    "gold_moderate_above_200sma":  +1,   # 2–5% above 200 DMA — elevated context

    # ── Momentum ──────────────────────────────────────────────────────────────────
    "gold_momentum_strong":        -2,   # 5d > +1% — trend intact, wait
    "gold_momentum_fading":        +2,   # 5d ≈ 0% — move losing steam, hedge
    "gold_momentum_negative":      +3,   # 5d negative — reversal underway

    # ── Macro headwinds / tailwinds ───────────────────────────────────────────────
    "gold_dxy_strong_rising":      +2,   # DXY > 104 AND rising — USD strength headwind
    "gold_dxy_rising":             +1,   # DXY 5d up — mild USD headwind
    "gold_dxy_weak_falling":       -2,   # DXY < 100 AND falling — tailwind for gold
    "gold_dxy_falling":            -1,   # DXY 5d down — mild tailwind
    "gold_real_yield_rising":      +2,   # 10Y rising fast (>15bps / 5d) — gold headwind
    "gold_real_yield_falling":     -2,   # 10Y falling fast — gold tailwind
    "gold_vix_elevated":           -1,   # VIX > 25 — safe-haven demand supports gold

    # ── Relative value ────────────────────────────────────────────────────────────
    "gold_silver_ratio_extreme":   +2,   # GSR > 85 — gold expensive vs silver, mean-reversion risk
    "gold_silver_ratio_low":       -1,   # GSR < 70 — silver leading, gold has more room

    # ── Key level proximity ───────────────────────────────────────────────────────
    "gold_near_key_resistance":    +2,   # Approaching resistance — sell zone
    "gold_broke_above_resistance": -2,   # Broke above — momentum intact
    "gold_near_key_support":       -1,   # Near support — bounce risk
    "gold_broke_below_support":    +4,   # Broke below support — sell urgently

    # ── MACD (12/26/9) ────────────────────────────────────────────────────────────
    "gold_macd_bearish_cross":          +2,   # MACD crossed below signal — momentum turning down
    "gold_macd_bullish_cross":          -2,   # MACD crossed above signal — momentum turning up

    # ── ADX (14) ─────────────────────────────────────────────────────────────────
    "gold_adx_trending_bearish":        +2,   # ADX > 25 AND -DI > +DI — strong downtrend confirmed
    "gold_adx_trending_bullish":        -2,   # ADX > 25 AND +DI > -DI — strong uptrend confirmed
    "gold_adx_ranging":                 +1,   # ADX < 20 — no clear trend; reversal-prone zone

    # ── Stochastic RSI (14,14,3,3) ───────────────────────────────────────────────
    "gold_stochrsi_overbought_bearish": +2,   # StochRSI K > 80 and K < D (topping) — precision short entry
    "gold_stochrsi_oversold":           -1,   # StochRSI K < 20 — oversold bounce likely

    # ── EMA 9 / 21 crossover ─────────────────────────────────────────────────────
    "gold_ema_bearish_cross":           +2,   # EMA 9 crossed below EMA 21 — short-term momentum turned down
    "gold_ema_bullish_cross":           -2,   # EMA 9 crossed above EMA 21 — short-term momentum turned up
    "gold_ema_bearish_stack":           +1,   # Price < EMA9 < EMA21 — bearish short-term stack
}

GOLD_HEDGE_THRESHOLDS = [
    (0,  "HOLD — Let It Run",   0,  "Low"),
    (3,  "SELL 25% FORWARD",   25,  "Medium"),
    (6,  "SELL 50% FORWARD",   50,  "Medium"),
    (12, "SELL 75% FORWARD",   75,  "High"),
    (20, "SELL ALL FORWARD",  100,  "High"),
]

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
