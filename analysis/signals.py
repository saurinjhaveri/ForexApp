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
    direction: str  # "SELL" if weight > 0 (lock in bonus), "HOLD" if weight < 0


def generate_signals(
    tech: TechnicalSnapshot,
    price: PriceData,
    macro: MacroData,
    news: List[NewsItem],
    dxy_5d_change: Optional[float] = None,
    brent_5d_change: Optional[float] = None,
    us_yield_5d_change: Optional[float] = None,
    usdinr_5d_change: Optional[float] = None,
) -> List[Signal]:
    signals: List[Signal] = []

    def add(name: str, description: str):
        w = SIGNAL_WEIGHTS.get(name, 0)
        if w != 0:
            signals.append(Signal(
                name=name, weight=w, description=description,
                direction="SELL" if w > 0 else "HOLD",
            ))

    # ── Weekly RSI — most predictive for sustained reversals ─────────────────────
    if tech.rsi_weekly and tech.rsi_weekly > 70:
        add("weekly_rsi_overbought",
            f"Weekly RSI = {tech.rsi_weekly:.1f} — overbought on weekly timeframe, "
            f"historically precedes 2–4% USD/INR pullbacks within 4–8 weeks")

    # ── Daily RSI ────────────────────────────────────────────────────────────────
    if tech.rsi_daily:
        if tech.rsi_daily > 70:
            add("rsi_overbought",
                f"Daily RSI = {tech.rsi_daily:.1f} — overbought, short-term reversal risk")
        elif tech.rsi_daily > 60:
            add("rsi_moderately_high",
                f"Daily RSI = {tech.rsi_daily:.1f} — elevated but has room; trend intact short-term")
        elif tech.rsi_daily < 40:
            add("rsi_oversold",
                f"Daily RSI = {tech.rsi_daily:.1f} — oversold, USD/INR likely to bounce; hold open")

    # ── Bollinger Bands ───────────────────────────────────────────────────────────
    if tech.bb_pct_b is not None:
        if tech.bb_pct_b > 0.80:
            add("bb_upper_breach",
                f"Price at {tech.bb_pct_b*100:.0f}% of Bollinger Band — upper band territory, move is stretched")
        elif tech.bb_pct_b < 0.20:
            add("bb_lower_breach",
                f"Price at {tech.bb_pct_b*100:.0f}% of Bollinger Band — near lower band, bounce likely")

    # ── Distance from 200 DMA ─────────────────────────────────────────────────────
    if tech.pct_above_sma200 is not None:
        if tech.pct_above_sma200 > 5.0:
            add("extreme_above_200sma",
                f"Spot is {tech.pct_above_sma200:+.2f}% above 200 DMA ({tech.sma_200:.2f}) — "
                f"historically extended; USD/INR rarely sustains >5% above 200 DMA")
        elif tech.pct_above_sma200 > 2.0:
            add("moderately_above_200sma",
                f"Spot is {tech.pct_above_sma200:+.2f}% above 200 DMA — elevated but not extreme")

    # ── Volatility ────────────────────────────────────────────────────────────────
    if tech.atr_elevated:
        add("high_volatility",
            f"ATR {tech.atr_14:.4f} > 125% of 90d avg {tech.atr_90d_avg:.4f} — "
            f"heightened volatility means moves in either direction are larger")

    # ── DXY level: is the dollar globally strong or weak? ─────────────────────────
    if price.dxy is not None:
        if price.dxy < 100:
            add("dxy_weak_level",
                f"DXY = {price.dxy:.2f} — dollar is SOFT globally (below 100); "
                f"USD/INR at highs driven by India-specific INR weakness, not broad USD strength. "
                f"India-specific weakness snaps back faster.")
        elif price.dxy > 104:
            add("dxy_strong_level",
                f"DXY = {price.dxy:.2f} — broad dollar strength; USD/INR high has global backing")

    # ── DXY momentum ─────────────────────────────────────────────────────────────
    if dxy_5d_change is not None:
        if dxy_5d_change < -0.5:
            add("dxy_falling",
                f"DXY 5d change = {dxy_5d_change:+.2f}% — dollar weakening globally")
        elif dxy_5d_change > 0.5:
            add("dxy_rising",
                f"DXY 5d change = {dxy_5d_change:+.2f}% — dollar strengthening globally; USD/INR has tailwind")

    # ── DXY / USD-INR divergence (key signal) ────────────────────────────────────
    if dxy_5d_change is not None and usdinr_5d_change is not None:
        if dxy_5d_change < -0.2 and usdinr_5d_change > 0.2:
            add("dxy_usdinr_divergence",
                f"DIVERGENCE: DXY falling ({dxy_5d_change:+.2f}% in 5d) while USD/INR is rising "
                f"({usdinr_5d_change:+.2f}% in 5d) — INR weakness is India-specific, not dollar-driven. "
                f"This divergence historically reverses sharply.")

    # ── USD/INR price momentum ────────────────────────────────────────────────────
    if usdinr_5d_change is not None:
        if usdinr_5d_change > 0.5:
            add("usdinr_momentum_strong",
                f"USD/INR 5d change = {usdinr_5d_change:+.2f}% — trend still up, daily momentum intact")
        elif abs(usdinr_5d_change) < 0.2:
            add("usdinr_momentum_fading",
                f"USD/INR 5d change = {usdinr_5d_change:+.2f}% — momentum fading, move losing steam")
        elif usdinr_5d_change < 0:
            add("usdinr_momentum_negative",
                f"USD/INR 5d change = {usdinr_5d_change:+.2f}% — reversal already underway")

    # ── Oil ───────────────────────────────────────────────────────────────────────
    if brent_5d_change is not None:
        if brent_5d_change < -2.0:
            add("oil_falling",
                f"Brent {brent_5d_change:+.1f}% in 5d — lower oil reduces India's import bill, INR can strengthen")
        elif brent_5d_change > 2.0:
            add("oil_rising",
                f"Brent {brent_5d_change:+.1f}% in 5d — rising oil pressures INR via import costs; USD/INR stays bid")

    # ── US yields ─────────────────────────────────────────────────────────────────
    if us_yield_5d_change is not None:
        if us_yield_5d_change < -0.05:
            add("us_yield_falling",
                f"US 10Y yield 5d change = {us_yield_5d_change:+.3f}% — softening yields weaken USD")
        elif us_yield_5d_change > 0.05:
            add("us_yield_rising",
                f"US 10Y yield 5d change = {us_yield_5d_change:+.3f}% — rising yields support USD")

    # ── FII flows ─────────────────────────────────────────────────────────────────
    if macro.fii_equity_net_crore is not None:
        if macro.fii_equity_net_crore > 1000:
            add("fii_inflow_strong",
                f"FII net inflow ₹{macro.fii_equity_net_crore:,.0f} Cr — foreign buying INR assets; sell USD at these levels")
        elif macro.fii_equity_net_crore < -1000:
            add("fii_outflow_strong",
                f"FII net outflow ₹{macro.fii_equity_net_crore:,.0f} Cr — selling INR; USD/INR has support")

    # ── RBI intervention news ─────────────────────────────────────────────────────
    for item in [n for n in news if n.flagged]:
        if any(kw in item.matched_keywords for kw in ["rbi intervention", "intervention"]):
            add("rbi_intervention_signal",
                f"News flag: RBI intervention signal — '{item.title[:55]}...'")
            break

    return signals
