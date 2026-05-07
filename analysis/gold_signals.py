from dataclasses import dataclass
from typing import List, Optional
from analysis.technicals import TechnicalSnapshot
from analysis.levels import KeyLevel
from analysis.signals import Signal
from data.gold_fetcher import GoldData
from config import GOLD_SIGNAL_WEIGHTS, GOLD_HEDGE_THRESHOLDS, DECISION_COLORS


def generate_gold_signals(
    tech: TechnicalSnapshot,
    gold: GoldData,
    dxy: Optional[float] = None,
    dxy_5d_change: Optional[float] = None,
    us_yield_5d_change: Optional[float] = None,
    us_vix: Optional[float] = None,
    gold_5d_change: Optional[float] = None,
    levels: Optional[List[KeyLevel]] = None,
) -> List[Signal]:
    signals: List[Signal] = []

    def add(name: str, description: str):
        w = GOLD_SIGNAL_WEIGHTS.get(name, 0)
        if w != 0:
            signals.append(Signal(
                name=name, weight=w, description=description,
                direction="SELL" if w > 0 else "HOLD",
            ))

    # ── Weekly RSI ────────────────────────────────────────────────────────────────
    if tech.rsi_weekly and tech.rsi_weekly > 70:
        add("gold_weekly_rsi_overbought",
            f"Weekly RSI = {tech.rsi_weekly:.1f} — gold overbought on weekly timeframe; "
            f"historically precedes 3–6% corrections within 4–8 weeks. Strongest sell signal.")

    # ── Daily RSI ─────────────────────────────────────────────────────────────────
    if tech.rsi_daily:
        if tech.rsi_daily > 70:
            add("gold_rsi_overbought",
                f"Daily RSI = {tech.rsi_daily:.1f} — overbought; short-term reversal risk")
        elif tech.rsi_daily > 55:
            add("gold_rsi_moderately_high",
                f"Daily RSI = {tech.rsi_daily:.1f} — elevated; start reducing exposure")
        elif tech.rsi_daily < 40:
            add("gold_rsi_oversold",
                f"Daily RSI = {tech.rsi_daily:.1f} — oversold, bounce likely; hold open")

    # ── Bollinger Bands ───────────────────────────────────────────────────────────
    if tech.bb_pct_b is not None:
        if tech.bb_pct_b > 0.80:
            add("gold_bb_upper_breach",
                f"Gold at {tech.bb_pct_b*100:.0f}% of Bollinger Band — upper band territory, move stretched")
        elif tech.bb_pct_b < 0.20:
            add("gold_bb_lower_breach",
                f"Gold at {tech.bb_pct_b*100:.0f}% of Bollinger Band — near lower band, bounce likely")

    # ── Distance from 200 DMA ─────────────────────────────────────────────────────
    if tech.pct_above_sma200 is not None:
        if tech.pct_above_sma200 > 5.0:
            add("gold_extreme_above_200sma",
                f"Gold spot {tech.pct_above_sma200:+.2f}% above 200 DMA ({tech.sma_200:.0f}) — "
                f"historically extended; sharp pullbacks common >5% above 200 DMA")
        elif tech.pct_above_sma200 > 2.0:
            add("gold_moderate_above_200sma",
                f"Gold {tech.pct_above_sma200:+.2f}% above 200 DMA — elevated but not extreme")

    # ── Momentum ──────────────────────────────────────────────────────────────────
    if gold_5d_change is not None:
        if gold_5d_change > 1.0:
            add("gold_momentum_strong",
                f"Gold 5d change = {gold_5d_change:+.2f}% — trend intact, momentum strong; wait for turn")
        elif abs(gold_5d_change) < 0.3:
            add("gold_momentum_fading",
                f"Gold 5d change = {gold_5d_change:+.2f}% — momentum fading; hedge before reversal confirms")
        elif gold_5d_change < 0:
            add("gold_momentum_negative",
                f"Gold 5d change = {gold_5d_change:+.2f}% — reversal already underway; sell forward now")

    # ── DXY (inverse relationship with gold) ─────────────────────────────────────
    if dxy is not None and dxy_5d_change is not None:
        if dxy > 104 and dxy_5d_change > 0.5:
            add("gold_dxy_strong_rising",
                f"DXY = {dxy:.2f} and rising ({dxy_5d_change:+.2f}% in 5d) — "
                f"broad USD strength is the biggest headwind for gold; sell forward to lock in current price")
        elif dxy_5d_change > 0.5:
            add("gold_dxy_rising",
                f"DXY 5d change = {dxy_5d_change:+.2f}% — dollar strengthening; mild headwind for gold")
        elif dxy < 100 and dxy_5d_change < -0.5:
            add("gold_dxy_weak_falling",
                f"DXY = {dxy:.2f} and falling ({dxy_5d_change:+.2f}% in 5d) — "
                f"weak USD is a strong tailwind; gold rally likely has more room")
        elif dxy_5d_change < -0.5:
            add("gold_dxy_falling",
                f"DXY 5d change = {dxy_5d_change:+.2f}% — dollar weakening; mild tailwind for gold")

    # ── US 10Y yield (key gold driver) ───────────────────────────────────────────
    if us_yield_5d_change is not None:
        if us_yield_5d_change > 0.15:
            add("gold_real_yield_rising",
                f"US 10Y yield +{us_yield_5d_change:.2f}% in 5d — rising yields increase opportunity cost "
                f"of holding gold; historically the strongest bearish signal for gold")
        elif us_yield_5d_change < -0.15:
            add("gold_real_yield_falling",
                f"US 10Y yield {us_yield_5d_change:.2f}% in 5d — falling yields reduce opportunity cost; "
                f"supportive environment for gold to continue higher")

    # ── VIX (safe-haven demand) ───────────────────────────────────────────────────
    if us_vix is not None and us_vix > 25:
        add("gold_vix_elevated",
            f"VIX = {us_vix:.1f} — elevated fear; safe-haven demand is supporting gold. "
            f"Panic-driven rallies often reverse once VIX normalises — don't over-hedge.")

    # ── Gold/Silver ratio ─────────────────────────────────────────────────────────
    if gold.gold_silver_ratio is not None:
        if gold.gold_silver_ratio > 85:
            add("gold_silver_ratio_extreme",
                f"Gold/Silver ratio = {gold.gold_silver_ratio:.0f} — gold is extremely expensive "
                f"relative to silver (historical avg ~70). Mean-reversion risk elevated.")
        elif gold.gold_silver_ratio < 70:
            add("gold_silver_ratio_low",
                f"Gold/Silver ratio = {gold.gold_silver_ratio:.0f} — silver outperforming; "
                f"gold still has room in this metals rally.")

    # ── Key level proximity ───────────────────────────────────────────────────────
    if levels:
        near_res_fired = near_sup_fired = False
        for lvl in sorted(levels, key=lambda l: abs(l.price - tech.spot)):
            dist_pct = (lvl.price - tech.spot) / tech.spot * 100
            if not near_res_fired and lvl.level_type == "resistance" and -0.5 <= dist_pct <= 0:
                add("gold_near_key_resistance",
                    f"Gold {tech.spot:.0f} approaching resistance at {lvl.name} ({lvl.price:.0f}) — "
                    f"classic zone to sell forward")
                near_res_fired = True
            elif not near_sup_fired and lvl.level_type == "support" and 0 <= dist_pct <= 0.5:
                add("gold_near_key_support",
                    f"Gold {tech.spot:.0f} just above support at {lvl.name} ({lvl.price:.0f}) — "
                    f"hold, bounce likely")
                near_sup_fired = True

        if tech.high_5d and tech.low_5d:
            for lvl in levels:
                if lvl.level_type == "resistance" and tech.low_5d < lvl.price <= tech.spot:
                    add("gold_broke_above_resistance",
                        f"Gold broke above {lvl.name} ({lvl.price:.0f}) within 5 days — momentum intact")
                    break
                if lvl.level_type == "support" and tech.high_5d > lvl.price >= tech.spot:
                    add("gold_broke_below_support",
                        f"Gold broke below {lvl.name} support ({lvl.price:.0f}) — sell forward urgently")
                    break

    # ── MACD (12/26/9) ────────────────────────────────────────────────────────────
    if tech.macd_bearish_cross:
        hist_str = f", histogram {tech.macd_histogram:+.4f}" if tech.macd_histogram is not None else ""
        add("gold_macd_bearish_cross",
            f"MACD ({tech.macd_line:.2f}) crossed below signal ({tech.macd_signal_line:.2f}){hist_str} "
            f"— gold short-term momentum has turned down; confirms sell setup")
    elif tech.macd_bullish_cross:
        add("gold_macd_bullish_cross",
            f"MACD ({tech.macd_line:.2f}) crossed above signal ({tech.macd_signal_line:.2f}) "
            f"— gold short-term momentum turning up; trend likely resuming")

    # ── ADX (14) ─────────────────────────────────────────────────────────────────
    if tech.adx is not None:
        if tech.adx > 25 and tech.adx_minus_di is not None and tech.adx_plus_di is not None:
            if tech.adx_minus_di > tech.adx_plus_di:
                add("gold_adx_trending_bearish",
                    f"ADX = {tech.adx:.1f} with -DI ({tech.adx_minus_di:.1f}) > +DI ({tech.adx_plus_di:.1f}) "
                    f"— strong gold downtrend confirmed; sell forward now")
            else:
                add("gold_adx_trending_bullish",
                    f"ADX = {tech.adx:.1f} with +DI ({tech.adx_plus_di:.1f}) > -DI ({tech.adx_minus_di:.1f}) "
                    f"— gold uptrend has momentum; hold open, let it run")
        elif tech.adx < 20:
            add("gold_adx_ranging",
                f"ADX = {tech.adx:.1f} — gold in consolidation; "
                f"range-bound price action, mean-reversion favoured")

    # ── Stochastic RSI (14,14,3,3) ───────────────────────────────────────────────
    if tech.stoch_rsi_k is not None and tech.stoch_rsi_d is not None:
        if tech.stoch_rsi_k > 80 and tech.stoch_rsi_k < tech.stoch_rsi_d:
            add("gold_stochrsi_overbought_bearish",
                f"StochRSI K = {tech.stoch_rsi_k:.1f} > 80 and crossing below D ({tech.stoch_rsi_d:.1f}) "
                f"— gold overbought momentum decelerating; precision sell entry")
        elif tech.stoch_rsi_k < 20:
            add("gold_stochrsi_oversold",
                f"StochRSI K = {tech.stoch_rsi_k:.1f} < 20 — gold oversold; "
                f"bounce likely, hold open position")

    # ── EMA 9 / 21 crossover ─────────────────────────────────────────────────────
    if tech.ema_bearish_cross:
        add("gold_ema_bearish_cross",
            f"EMA 9 ({tech.ema_9:.0f}) crossed below EMA 21 ({tech.ema_21:.0f}) within 3 days "
            f"— gold short-term momentum has turned bearish")
    elif tech.ema_bullish_cross:
        add("gold_ema_bullish_cross",
            f"EMA 9 ({tech.ema_9:.0f}) crossed above EMA 21 ({tech.ema_21:.0f}) within 3 days "
            f"— gold short-term momentum turning bullish; trend resuming")
    elif (tech.ema_9 is not None and tech.ema_21 is not None
          and tech.spot < tech.ema_9 < tech.ema_21):
        add("gold_ema_bearish_stack",
            f"Price (${tech.spot:.0f}) < EMA 9 (${tech.ema_9:.0f}) < EMA 21 (${tech.ema_21:.0f}) "
            f"— short-term EMAs stacked bearish; gold under pressure")

    return signals


def make_gold_decision(signals: List[Signal], spot: Optional[float] = None, levels=None):
    """Reuses the generic decision engine with gold-specific thresholds."""
    from analysis.decision_engine import _compute_regime, _build_tranche_trigger, Decision

    score = sum(s.weight for s in signals)

    recommendation = "HOLD — Let It Run"
    hedge_ratio = 0
    confidence = "Low"
    for threshold, rec, ratio, conf in reversed(GOLD_HEDGE_THRESHOLDS):
        if score >= threshold:
            recommendation = rec
            hedge_ratio = ratio
            confidence = conf
            break

    sell_sigs = sorted([s for s in signals if s.weight > 0], key=lambda s: s.weight, reverse=True)
    hold_sigs = sorted([s for s in signals if s.weight < 0], key=lambda s: abs(s.weight), reverse=True)
    top = sell_sigs[:3] if hedge_ratio > 0 else hold_sigs[:3]
    key_reasons = [s.description for s in top]

    head = top[0] if top else None
    if head:
        rationale = head.description.split(" — ")[-1] if " — " in head.description else head.description
        rationale = rationale.split(". ")[0] + "."
    else:
        rationale = "No strong directional signals — neutral conditions."

    if len(signals) < 3:
        confidence = "Low"

    # Regime: map gold signal names to generic regime scoring
    fired = {s.name for s in signals}
    regime_score = 0
    if "gold_weekly_rsi_overbought" in fired: regime_score += 3
    if "gold_rsi_overbought"        in fired: regime_score += 2
    if "gold_bb_upper_breach"       in fired: regime_score += 1
    if "gold_extreme_above_200sma"  in fired: regime_score += 1
    if "gold_momentum_strong"       in fired: regime_score -= 2
    if "gold_dxy_strong_rising"     in fired: regime_score += 2
    if "gold_broke_below_support"   in fired: regime_score += 2
    regime = "mean_reversion" if regime_score >= 4 else ("trend" if regime_score <= -3 else "neutral")

    tranche_trigger = _build_tranche_trigger(hedge_ratio, signals, levels, spot)

    return Decision(
        recommendation=recommendation,
        hedge_ratio=hedge_ratio,
        confidence=confidence,
        rationale=rationale,
        key_reasons=key_reasons,
        score=score,
        signals=signals,
        color=DECISION_COLORS.get(recommendation, "#6b7280"),
        regime=regime,
        tranche_trigger=tranche_trigger,
        spot=spot,
    )
