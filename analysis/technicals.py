from dataclasses import dataclass
from typing import Optional
import numpy as np
import pandas as pd
from config import TECHNICAL_PARAMS


@dataclass
class TechnicalSnapshot:
    spot: float
    rsi_daily: Optional[float] = None
    rsi_weekly: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    pct_above_sma50: Optional[float] = None
    pct_above_sma200: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_mid: Optional[float] = None
    bb_lower: Optional[float] = None
    bb_pct_b: Optional[float] = None       # (price - lower) / (upper - lower)
    bb_bandwidth: Optional[float] = None   # (upper - lower) / mid
    atr_14: Optional[float] = None
    atr_90d_avg: Optional[float] = None
    atr_elevated: bool = False


def _rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff().dropna()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean().iloc[-1]
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, prev_close = df["High"], df["Low"], df["Close"].shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(com=period - 1, min_periods=period).mean()


def _weekly_rsi(df: pd.DataFrame, period: int = 14) -> Optional[float]:
    weekly = df["Close"].resample("W").last().dropna()
    if len(weekly) < period + 5:
        return None
    return _rsi(weekly, period)


def compute_technicals(df: pd.DataFrame) -> TechnicalSnapshot:
    p = TECHNICAL_PARAMS
    close = df["Close"]
    spot = float(close.iloc[-1])

    sma50 = float(close.rolling(p["sma_fast"]).mean().iloc[-1])
    sma200 = float(close.rolling(p["sma_slow"]).mean().iloc[-1])

    bb_mid = float(close.rolling(p["bb_period"]).mean().iloc[-1])
    bb_std = float(close.rolling(p["bb_period"]).std().iloc[-1])
    bb_upper = bb_mid + p["bb_std"] * bb_std
    bb_lower = bb_mid - p["bb_std"] * bb_std
    bb_pct_b = (spot - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5
    bb_bw = (bb_upper - bb_lower) / bb_mid if bb_mid else 0

    atr_series = _atr(df, p["atr_period"])
    atr_now = float(atr_series.iloc[-1])
    atr_90d = float(atr_series.iloc[-p["atr_lookback_days"]:].mean())

    return TechnicalSnapshot(
        spot=spot,
        rsi_daily=_rsi(close, p["rsi_period"]),
        rsi_weekly=_weekly_rsi(df, p["rsi_period"]),
        sma_50=round(sma50, 4),
        sma_200=round(sma200, 4),
        pct_above_sma50=round((spot - sma50) / sma50 * 100, 2),
        pct_above_sma200=round((spot - sma200) / sma200 * 100, 2),
        bb_upper=round(bb_upper, 4),
        bb_mid=round(bb_mid, 4),
        bb_lower=round(bb_lower, 4),
        bb_pct_b=round(bb_pct_b, 3),
        bb_bandwidth=round(bb_bw * 100, 2),
        atr_14=round(atr_now, 4),
        atr_90d_avg=round(atr_90d, 4),
        atr_elevated=atr_now > atr_90d * 1.25,
    )
