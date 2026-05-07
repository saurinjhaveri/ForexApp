from dataclasses import dataclass
from typing import List, Optional
from analysis.technicals import TechnicalSnapshot
from analysis.levels import KeyLevel
from data.price_fetcher import PriceData
from data.macro_scraper import MacroData
from data.news_fetcher import NewsItem
from data.nse_scraper import FuturesData
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
    levels: Optional[List[KeyLevel]] = None,
    futures: Optional[FuturesData] = None,
    oi_pct_above_avg: Optional[float] = None,
    inr_em_divergence: Optional[float] = None,
    forward_premium_pctile_rank: Optional[float] = None,
    reserves_7d_change: Optional[float] = None,
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
        elif tech.rsi_daily > 55:
            add("rsi_moderately_high",
                f"Daily RSI = {tech.rsi_daily:.1f} — elevated; aggressive hedger should start reducing exposure")
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

    # ── EM basket relative divergence ────────────────────────────────────────────
    # inr_em_divergence = usdinr_5d_change - em_basket_5d_avg
    # Positive = INR weaker than EM peers → India-specific weakness (higher conviction to sell)
    if inr_em_divergence is not None:
        if inr_em_divergence > 0.5:
            add("inr_em_divergence_strong",
                f"INR is underperforming EM peers by {inr_em_divergence:+.2f}% (5d) — "
                f"weakness is India-specific, not dollar-driven; historically snaps back faster. "
                f"Highest-conviction signal to lock in the forward rate now.")
        elif inr_em_divergence < -0.5:
            add("inr_em_outperforming",
                f"INR outperforming EM basket by {abs(inr_em_divergence):.2f}% (5d) — "
                f"USD/INR move is part of broad EM dollar strength, not India-specific. "
                f"Lower urgency to hedge; wait for EM trend to confirm.")

    # ── Forward premium / carry ───────────────────────────────────────────────────
    # For exporters: high premium = better forward rate locked in = MORE reason to hedge
    if forward_premium_pctile_rank is not None and futures and futures.annualized_premium_pct is not None:
        ann = futures.annualized_premium_pct
        if forward_premium_pctile_rank >= 90:
            add("forward_premium_extreme",
                f"Annualized forward premium = {ann:.1f}% (>90th pctile of 90d history) — "
                f"market is pricing aggressive INR depreciation; you lock in an exceptional carry benefit by hedging now.")
        elif forward_premium_pctile_rank >= 75:
            add("forward_premium_high_pctile",
                f"Annualized forward premium = {ann:.1f}% (>75th pctile of 90d history) — "
                f"above-average carry; favorable time to sell forward.")
        elif forward_premium_pctile_rank <= 25:
            add("forward_premium_collapsed",
                f"Annualized forward premium = {ann:.1f}% (<25th pctile of 90d history) — "
                f"carry benefit is thin; the market is not pricing much INR weakness. "
                f"Reduce hedging urgency unless technical signals are strong.")

    # ── RBI intervention zones ────────────────────────────────────────────────────
    if tech.spot >= 95.0:
        add("rbi_intervention_active",
            f"Spot {tech.spot:.4f} — above 95.00, historically the hardest RBI defence level. "
            f"Intervention is near-certain; INR reversal risk is very high. Sell forward urgently.")
    elif tech.spot >= 94.5:
        add("rbi_intervention_zone",
            f"Spot {tech.spot:.4f} — entering RBI's known intervention zone (94.50–95.00). "
            f"RBI has historically defended these levels; expect USD selling pressure.")

    # ── FX reserves confirmation (gated on EM divergence) ────────────────────────
    # Reserves falling alone can be valuation noise. Only signal if INR is also
    # underperforming EM peers — that combination indicates active RBI deployment.
    if (reserves_7d_change is not None and reserves_7d_change < -2.0
            and inr_em_divergence is not None and inr_em_divergence > 0.3):
        add("fx_reserves_falling_confirmed",
            f"FX reserves fell USD {abs(reserves_7d_change):.1f}bn in 7 days AND INR is "
            f"underperforming EM basket — RBI is actively deploying reserves to cap INR weakness; "
            f"reversal likely once intervention is complete.")

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

    # ── Key level proximity & breakout signals ────────────────────────────────────
    if levels:
        near_res_fired = False
        near_sup_fired = False

        for lvl in sorted(levels, key=lambda l: abs(l.price - tech.spot)):
            dist_pct = (lvl.price - tech.spot) / tech.spot * 100

            # Spot approaching resistance from below (within 0.35%)
            if not near_res_fired and lvl.level_type == "resistance" and -0.35 <= dist_pct <= 0:
                add("near_key_resistance",
                    f"Spot {tech.spot:.4f} is {abs(dist_pct):.2f}% below {lvl.name} "
                    f"resistance ({lvl.price:.4f}) — classic zone to sell forward")
                near_res_fired = True

            # Spot resting just above support (within 0.35%) — bounce expected
            elif not near_sup_fired and lvl.level_type == "support" and 0 <= dist_pct <= 0.35:
                add("near_key_support",
                    f"Spot {tech.spot:.4f} is {dist_pct:.2f}% above {lvl.name} "
                    f"support ({lvl.price:.4f}) — hold, bounce likely")
                near_sup_fired = True

        # Breakout detection using 5-day high/low range
        if tech.high_5d and tech.low_5d:
            for lvl in levels:
                if lvl.level_type == "resistance" and tech.low_5d < lvl.price <= tech.spot:
                    add("broke_above_resistance",
                        f"Spot broke above {lvl.name} ({lvl.price:.4f}) within 5 days "
                        f"— momentum continuation, hold for now")
                    break
                if lvl.level_type == "support" and tech.high_5d > lvl.price >= tech.spot:
                    add("broke_below_support",
                        f"Spot broke below {lvl.name} support ({lvl.price:.4f}) within 5 days "
                        f"— INR weakness accelerating, sell forward urgently")
                    break

    # ── Futures open interest positioning ────────────────────────────────────────
    if futures and futures.near_month_oi and futures.near_month_oi_change is not None:
        oi_up    = futures.near_month_oi_change > 0
        price_up = (usdinr_5d_change or 0) > 0

        if oi_up and price_up:
            add("oi_longs_building",
                f"OI +{futures.near_month_oi_change:,.0f} contracts as price rises — "
                f"new longs entering at highs; crowded trade, fragile")
        elif not oi_up and price_up:
            add("oi_short_covering",
                f"OI falling ({futures.near_month_oi_change:+,.0f}) while price rises — "
                f"short covering only, not fresh longs; move lacks conviction")
        elif not oi_up and not price_up:
            add("oi_longs_unwinding",
                f"OI falling ({futures.near_month_oi_change:+,.0f}) as price falls — "
                f"longs exiting under water; reversal underway, sell urgently")

    # Crowded buildup: current OI significantly above recent average
    if oi_pct_above_avg is not None and oi_pct_above_avg > 15:
        add("oi_crowded_buildup",
            f"Near-month OI is {oi_pct_above_avg:.0f}% above its 20-day average — "
            f"structurally crowded long positioning; sharp unwind risk")

    # ── MACD (12/26/9) ────────────────────────────────────────────────────────────
    if tech.macd_bearish_cross:
        hist_str = f", histogram {tech.macd_histogram:+.4f}" if tech.macd_histogram is not None else ""
        add("macd_bearish_cross",
            f"MACD ({tech.macd_line:.4f}) crossed below signal ({tech.macd_signal_line:.4f}){hist_str} "
            f"— short-term momentum has turned down; confirms SELL setup")
    elif tech.macd_bullish_cross:
        add("macd_bullish_cross",
            f"MACD ({tech.macd_line:.4f}) crossed above signal ({tech.macd_signal_line:.4f}) "
            f"— short-term momentum turning up; wait for pullback")

    # ── ADX (14) ─────────────────────────────────────────────────────────────────
    if tech.adx is not None:
        if tech.adx > 25 and tech.adx_minus_di is not None and tech.adx_plus_di is not None:
            if tech.adx_minus_di > tech.adx_plus_di:
                add("adx_trending_bearish",
                    f"ADX = {tech.adx:.1f} (trending) with -DI ({tech.adx_minus_di:.1f}) > +DI ({tech.adx_plus_di:.1f}) "
                    f"— strong downtrend confirmed; sell into strength")
            else:
                add("adx_trending_bullish",
                    f"ADX = {tech.adx:.1f} (trending) with +DI ({tech.adx_plus_di:.1f}) > -DI ({tech.adx_minus_di:.1f}) "
                    f"— uptrend has momentum; hold open for now")
        elif tech.adx < 20:
            add("adx_ranging",
                f"ADX = {tech.adx:.1f} — market in ranging/consolidation mode; "
                f"breakouts unreliable, mean-reversion favoured")

    # ── Stochastic RSI (14,14,3,3) ───────────────────────────────────────────────
    if tech.stoch_rsi_k is not None and tech.stoch_rsi_d is not None:
        if tech.stoch_rsi_k > 80 and tech.stoch_rsi_k < tech.stoch_rsi_d:
            add("stochrsi_overbought_bearish",
                f"StochRSI K = {tech.stoch_rsi_k:.1f} > 80 and crossing below D ({tech.stoch_rsi_d:.1f}) "
                f"— overbought and momentum decelerating; precision entry for sellers")
        elif tech.stoch_rsi_k < 20:
            add("stochrsi_oversold",
                f"StochRSI K = {tech.stoch_rsi_k:.1f} < 20 — oversold; "
                f"short-term bounce likely, reduce hedging urgency")

    # ── EMA 9 / 21 crossover ─────────────────────────────────────────────────────
    if tech.ema_bearish_cross:
        add("ema_bearish_cross",
            f"EMA 9 ({tech.ema_9:.4f}) crossed below EMA 21 ({tech.ema_21:.4f}) within 3 days "
            f"— short-term momentum has turned bearish for USD/INR")
    elif tech.ema_bullish_cross:
        add("ema_bullish_cross",
            f"EMA 9 ({tech.ema_9:.4f}) crossed above EMA 21 ({tech.ema_21:.4f}) within 3 days "
            f"— short-term momentum turning bullish; wait for confirmation")
    elif (tech.ema_9 is not None and tech.ema_21 is not None
          and tech.spot < tech.ema_9 < tech.ema_21):
        add("ema_bearish_stack",
            f"Price ({tech.spot:.4f}) < EMA 9 ({tech.ema_9:.4f}) < EMA 21 ({tech.ema_21:.4f}) "
            f"— short-term EMAs fully stacked bearish; downward pressure intact")

    return signals
