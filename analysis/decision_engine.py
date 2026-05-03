from dataclasses import dataclass, field
from typing import List, Optional
from analysis.signals import Signal
from analysis.levels import KeyLevel
from config import HEDGE_THRESHOLDS, DECISION_COLORS


@dataclass
class Decision:
    recommendation: str
    hedge_ratio: int
    confidence: str
    rationale: str          # one-sentence headline
    key_reasons: List[str]  # top 3 signal descriptions for the decision box
    score: float
    signals: List[Signal]
    color: str
    regime: str = "neutral"               # "mean_reversion" | "trend" | "neutral"
    tranche_trigger: Optional[str] = None # conditional next-tranche description
    budget_rate: Optional[float] = None
    spot: Optional[float] = None


def _compute_regime(signals: List[Signal], inr_em_divergence: Optional[float] = None) -> str:
    """
    Score the market regime from active signals.
    Positive = mean-reversion conditions (extended, India-specific, RBI likely).
    Negative = trend conditions (momentum, broad dollar, OI building).
    """
    fired = {s.name for s in signals}
    score = 0

    # Mean-reversion evidence
    if "weekly_rsi_overbought"    in fired: score += 3
    if "rsi_overbought"           in fired: score += 2
    if "dxy_usdinr_divergence"    in fired: score += 2
    if "inr_em_divergence_strong" in fired: score += 2
    if "rbi_intervention_active"  in fired: score += 3
    if "rbi_intervention_zone"    in fired: score += 1
    if "bb_upper_breach"          in fired: score += 1
    if "extreme_above_200sma"     in fired: score += 1
    if "broke_below_support"      in fired: score += 2

    # Trend / momentum evidence (reduces mean-reversion confidence)
    if "usdinr_momentum_strong"   in fired: score -= 2
    if "dxy_rising"               in fired: score -= 1
    if "dxy_strong_level"         in fired: score -= 1
    if "oi_longs_building"        in fired: score -= 1
    if "broke_above_resistance"   in fired: score -= 2

    if score >= 4:
        return "mean_reversion"
    if score <= -3:
        return "trend"
    return "neutral"


def _build_tranche_trigger(
    hedge_ratio: int,
    signals: List[Signal],
    levels: Optional[List["KeyLevel"]] = None,
    spot: Optional[float] = None,
) -> Optional[str]:
    """Generate a 'what would push to the next tranche' description."""
    if hedge_ratio >= 100:
        return None

    fired = {s.name for s in signals}

    # Find nearest resistance above spot for a concrete price target
    next_res = None
    if levels and spot:
        res_above = [l for l in levels if l.level_type == "resistance" and l.price > spot]
        if res_above:
            next_res = min(res_above, key=lambda l: l.price)

    next_tranche = hedge_ratio + 25

    if hedge_ratio == 0:
        if next_res:
            return (f"Sell {next_tranche}% forward if spot breaks above "
                    f"{next_res.name} ({next_res.price:.4f}) or daily RSI exceeds 65.")
        return f"Sell {next_tranche}% forward if daily RSI exceeds 65 or DXY divergence appears."

    if "weekly_rsi_overbought" not in fired and "rsi_overbought" not in fired:
        return f"Add {next_tranche - hedge_ratio}% more if weekly RSI crosses 70 (currently in mean-reversion watch zone)."

    if next_res:
        return (f"Add remaining {100 - hedge_ratio}% if spot closes above "
                f"{next_res.name} ({next_res.price:.4f}) for 2 consecutive days — confirms breakout, sell into it.")

    return f"Add remaining {100 - hedge_ratio}% on a daily close above spot + 0.5% — momentum confirmation."


def make_decision(
    signals: List[Signal],
    budget_rate: Optional[float] = None,
    spot: Optional[float] = None,
    levels: Optional[List["KeyLevel"]] = None,
    inr_em_divergence: Optional[float] = None,
) -> Decision:
    score = sum(s.weight for s in signals)

    recommendation = "HOLD — Let It Run"
    hedge_ratio = 0
    confidence = "Low"
    for threshold, rec, ratio, conf in reversed(HEDGE_THRESHOLDS):
        if score >= threshold:
            recommendation = rec
            hedge_ratio = ratio
            confidence = conf
            break

    sell_signals = sorted([s for s in signals if s.weight > 0], key=lambda s: s.weight, reverse=True)
    hold_signals = sorted([s for s in signals if s.weight < 0], key=lambda s: abs(s.weight), reverse=True)

    # Top reasons: leading signals for the recommended direction
    if hedge_ratio > 0:
        top_signals = sell_signals[:3]
        headline_sig = sell_signals[0] if sell_signals else None
    else:
        top_signals = hold_signals[:3]
        headline_sig = hold_signals[0] if hold_signals else None

    key_reasons = [s.description for s in top_signals]

    if headline_sig:
        rationale = headline_sig.description.split(" — ")[-1] if " — " in headline_sig.description else headline_sig.description
        # Cap at one clear sentence
        rationale = rationale.split(". ")[0] + "."
    else:
        rationale = "No strong directional signals — neutral conditions."

    if len(signals) < 3:
        confidence = "Low"

    regime = _compute_regime(signals, inr_em_divergence)
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
        budget_rate=budget_rate,
        spot=spot,
    )
