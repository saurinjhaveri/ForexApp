from dataclasses import dataclass
from typing import List, Optional

from analysis.technicals import TechnicalSnapshot
from analysis.levels import KeyLevel
from analysis.signals import Signal


@dataclass
class TradeSetup:
    direction: str              # "LONG" | "SHORT" | "WAIT"
    signal_strength: str        # "Strong" | "Moderate" | "Weak"
    entry: float
    stop_loss: float
    stop_distance_pct: float
    target_1: Optional[float]
    target_2: Optional[float]
    rr_ratio: Optional[float]
    confidence: str
    key_reasons: List[str]      # top 3 signal descriptions for the direction


def _supports_below(entry: float, levels: List[KeyLevel]) -> List[KeyLevel]:
    return sorted(
        [l for l in levels if l.level_type == "support" and l.price < entry],
        key=lambda l: l.price,
        reverse=True,
    )


def _resistances_above(entry: float, levels: List[KeyLevel]) -> List[KeyLevel]:
    return sorted(
        [l for l in levels if l.level_type == "resistance" and l.price > entry],
        key=lambda l: l.price,
    )


def _stop_loss(direction: str, entry: float, atr_14: Optional[float], levels: List[KeyLevel]) -> float:
    atr_mult = 1.5
    if atr_14 is not None:
        raw = atr_14 * atr_mult
    else:
        raw = entry * 0.015

    if direction == "SHORT":
        atr_stop = entry + raw
        resistances = _resistances_above(entry, levels)
        if resistances:
            level_stop = resistances[0].price * 1.002
            return max(atr_stop, level_stop)
        return atr_stop
    else:
        atr_stop = entry - raw
        supports = _supports_below(entry, levels)
        if supports:
            level_stop = supports[0].price * 0.998
            return min(atr_stop, level_stop)
        return atr_stop


def _targets(direction: str, entry: float, levels: List[KeyLevel]):
    if direction == "SHORT":
        supports = _supports_below(entry, levels)
        t1 = supports[0].price if len(supports) >= 1 else entry * 0.97
        t2 = supports[1].price if len(supports) >= 2 else entry * 0.95
    elif direction == "LONG":
        resistances = _resistances_above(entry, levels)
        t1 = resistances[0].price if len(resistances) >= 1 else entry * 1.03
        t2 = resistances[1].price if len(resistances) >= 2 else entry * 1.05
    else:
        return None, None
    return t1, t2


def _key_reasons(direction: str, signals: List[Signal]) -> List[str]:
    if direction == "SHORT":
        relevant = [s for s in signals if s.weight > 0]
        relevant.sort(key=lambda s: -s.weight)
    elif direction == "LONG":
        relevant = [s for s in signals if s.weight < 0]
        relevant.sort(key=lambda s: s.weight)
    else:
        relevant = sorted(signals, key=lambda s: -abs(s.weight))
    return [s.description for s in relevant[:3]]


def compute_trade_setup(
    score: float,
    tech: TechnicalSnapshot,
    levels: List[KeyLevel],
    signals: List[Signal],
    confidence: str,
) -> TradeSetup:
    if score >= 6:
        direction = "SHORT"
        signal_strength = "Strong" if score >= 12 else "Moderate"
    elif score >= 3:
        direction = "SHORT"
        signal_strength = "Weak"
    elif score <= -12:
        direction = "LONG"
        signal_strength = "Strong"
    elif score <= -6:
        direction = "LONG"
        signal_strength = "Moderate"
    elif score <= -3:
        direction = "LONG"
        signal_strength = "Weak"
    else:
        direction = "WAIT"
        signal_strength = "Weak"

    entry = tech.spot

    if direction == "WAIT":
        stop_loss = entry
        stop_distance_pct = 0.0
        target_1 = None
        target_2 = None
        rr_ratio = None
    else:
        stop_loss = _stop_loss(direction, entry, tech.atr_14, levels)
        stop_distance_pct = round(abs(stop_loss - entry) / entry * 100, 3)
        target_1, target_2 = _targets(direction, entry, levels)
        stop_dist = abs(stop_loss - entry)
        rr_ratio = round(abs(target_1 - entry) / stop_dist, 1) if stop_dist != 0 else None

    return TradeSetup(
        direction=direction,
        signal_strength=signal_strength,
        entry=entry,
        stop_loss=round(stop_loss, 4),
        stop_distance_pct=stop_distance_pct,
        target_1=round(target_1, 4) if target_1 is not None else None,
        target_2=round(target_2, 4) if target_2 is not None else None,
        rr_ratio=rr_ratio,
        confidence=confidence,
        key_reasons=_key_reasons(direction, signals),
    )
