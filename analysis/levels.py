from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np
import pandas as pd


@dataclass
class KeyLevel:
    name: str
    price: float
    level_type: str   # "resistance" | "support" | "pivot"
    source: str       # "weekly_pivot" | "monthly_pivot" | "swing" | "200dma"
    strength: int     # 1 = basic, 2 = tested, 3 = major


def _find_swings(high: pd.Series, low: pd.Series, window: int = 5) -> Tuple[List[float], List[float]]:
    highs, lows = [], []
    # Drop NaNs before processing
    valid = high.notna() & low.notna()
    h = high[valid].values.astype(float)
    l = low[valid].values.astype(float)
    n = len(h)
    for i in range(window, n - window):
        left_h, right_h = h[i - window:i], h[i + 1:i + window + 1]
        left_l, right_l = l[i - window:i], l[i + 1:i + window + 1]
        if len(left_h) == window and len(right_h) == window:
            if h[i] > np.nanmax(left_h) and h[i] > np.nanmax(right_h):
                highs.append(float(h[i]))
        if len(left_l) == window and len(right_l) == window:
            if l[i] < np.nanmin(left_l) and l[i] < np.nanmin(right_l):
                lows.append(float(l[i]))
    return highs, lows


def _cluster(prices: List[float], tolerance_pct: float = 0.4) -> List[Tuple[float, int]]:
    if not prices:
        return []
    prices = sorted(p for p in prices if np.isfinite(p))
    if not prices:
        return []
    clusters: List[Tuple[float, int]] = []
    group = [prices[0]]
    for p in prices[1:]:
        if (p - group[0]) / group[0] * 100 <= tolerance_pct:
            group.append(p)
        else:
            clusters.append((sum(group) / len(group), len(group)))
            group = [p]
    clusters.append((sum(group) / len(group), len(group)))
    return clusters


def _pivot_levels(row: pd.Series, prefix: str) -> List[KeyLevel]:
    try:
        H, L, C = float(row["High"]), float(row["Low"]), float(row["Close"])
        if not all(np.isfinite(x) for x in (H, L, C)):
            return []
        P  = (H + L + C) / 3
        R1 = 2 * P - L
        R2 = P + (H - L)
        S1 = 2 * P - H
        S2 = P - (H - L)
        return [
            KeyLevel(f"{prefix} Pivot", round(P,  4), "pivot",      f"{prefix.lower()}_pivot", 2),
            KeyLevel(f"{prefix} R1",    round(R1, 4), "resistance", f"{prefix.lower()}_pivot", 2),
            KeyLevel(f"{prefix} R2",    round(R2, 4), "resistance", f"{prefix.lower()}_pivot", 1),
            KeyLevel(f"{prefix} S1",    round(S1, 4), "support",    f"{prefix.lower()}_pivot", 2),
            KeyLevel(f"{prefix} S2",    round(S2, 4), "support",    f"{prefix.lower()}_pivot", 1),
        ]
    except (TypeError, ValueError):
        return []


def _resample_ohlc(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    """Resample to OHLC, compatible with pandas ≥1.x and ≥2.2."""
    try:
        return df.resample(freq).agg(
            {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
        ).dropna()
    except Exception:
        return pd.DataFrame()


def compute_levels(df: pd.DataFrame, spot: float, sma_200: Optional[float] = None) -> List[KeyLevel]:
    levels: List[KeyLevel] = []

    try:
        # ── 1. Weekly pivot points (last completed week) ──────────────────────
        weekly = _resample_ohlc(df, "W")
        if len(weekly) >= 2:
            levels += _pivot_levels(weekly.iloc[-2], "Weekly")

        # ── 2. Monthly pivot points (last completed month) ────────────────────
        # "ME" = month-end (pandas ≥ 2.2); fall back to "M" for older versions
        try:
            monthly = _resample_ohlc(df, "ME")
        except Exception:
            monthly = _resample_ohlc(df, "M")
        if len(monthly) >= 2:
            levels += _pivot_levels(monthly.iloc[-2], "Monthly")

        # ── 3. Swing highs / lows (last 252 trading days) ────────────────────
        recent = df.tail(252)
        if len(recent) > 10:
            raw_highs, raw_lows = _find_swings(recent["High"], recent["Low"], window=5)

            for price, count in _cluster(raw_highs, tolerance_pct=0.4):
                strength = 3 if count >= 3 else (2 if count == 2 else 1)
                ltype = "resistance" if price >= spot else "support"
                label = "Swing High" if ltype == "resistance" else "Swing Hi/Lo"
                levels.append(KeyLevel(f"{label} ({count}×)", round(price, 4), ltype, "swing", strength))

            for price, count in _cluster(raw_lows, tolerance_pct=0.4):
                strength = 3 if count >= 3 else (2 if count == 2 else 1)
                ltype = "support" if price <= spot else "resistance"
                levels.append(KeyLevel(f"Swing Low ({count}×)", round(price, 4), ltype, "swing", strength))

        # ── 4. 200 DMA ────────────────────────────────────────────────────────
        if sma_200 and np.isfinite(sma_200):
            ltype = "support" if sma_200 < spot else "resistance"
            levels.append(KeyLevel("200 DMA", round(sma_200, 4), ltype, "200dma", 3))

    except Exception:
        # Graceful degradation — return whatever we've computed so far
        pass

    # ── Deduplicate: keep strongest level within 0.15% bands ─────────────────
    levels_by_strength = sorted(levels, key=lambda l: -l.strength)
    seen: List[float] = []
    unique: List[KeyLevel] = []
    for lvl in levels_by_strength:
        if lvl.price > 0 and not any(abs(lvl.price - s) / s < 0.0015 for s in seen):
            seen.append(lvl.price)
            unique.append(lvl)

    # ── Filter to ±8% of spot, sort price descending ─────────────────────────
    unique = [l for l in unique if abs(l.price - spot) / spot <= 0.08]
    return sorted(unique, key=lambda l: l.price, reverse=True)
