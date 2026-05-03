from dataclasses import dataclass
from typing import List
from analysis.signals import Signal
from config import HEDGE_THRESHOLDS, DECISION_COLORS


@dataclass
class Decision:
    recommendation: str
    hedge_ratio: int
    confidence: str
    rationale: str
    score: float
    signals: List[Signal]
    color: str


def make_decision(signals: List[Signal]) -> Decision:
    score = sum(s.weight for s in signals)

    recommendation = "WAIT"
    hedge_ratio = 0
    confidence = "Low"
    for threshold, rec, ratio, conf in reversed(HEDGE_THRESHOLDS):
        if score >= threshold:
            recommendation = rec
            hedge_ratio = ratio
            confidence = conf
            break

    cover_signals = [s for s in signals if s.weight > 0]
    wait_signals  = [s for s in signals if s.weight < 0]

    if cover_signals:
        top = sorted(cover_signals, key=lambda s: abs(s.weight), reverse=True)[0]
        rationale = f"{top.description}"
    elif wait_signals:
        top = sorted(wait_signals, key=lambda s: abs(s.weight), reverse=True)[0]
        rationale = f"{top.description}"
    else:
        rationale = "No strong directional signals — neutral market conditions"

    if len(signals) < 3:
        confidence = "Low"

    return Decision(
        recommendation=recommendation,
        hedge_ratio=hedge_ratio,
        confidence=confidence,
        rationale=rationale,
        score=score,
        signals=signals,
        color=DECISION_COLORS.get(recommendation, "#6b7280"),
    )
