from dataclasses import dataclass, field
from typing import List, Optional
from analysis.signals import Signal
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
    budget_rate: Optional[float] = None
    spot: Optional[float] = None


def make_decision(signals: List[Signal], budget_rate: Optional[float] = None, spot: Optional[float] = None) -> Decision:
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

    return Decision(
        recommendation=recommendation,
        hedge_ratio=hedge_ratio,
        confidence=confidence,
        rationale=rationale,
        key_reasons=key_reasons,
        score=score,
        signals=signals,
        color=DECISION_COLORS.get(recommendation, "#6b7280"),
        budget_rate=budget_rate,
        spot=spot,
    )
