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
