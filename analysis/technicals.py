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
    high_5d: Optional[float] = None
    low_5d: Optional[float] = None

    # MACD (12/26/9)
    macd_line: Optional[float] = None
    macd_signal_line: Optional[float] = None
    macd_histogram: Optional[float] = None
    macd_bearish_cross: bool = False   # macd_line crossed below macd_signal_line in last 3 days
    macd_bullish_cross: bool = False   # macd_line crossed above macd_signal_line in last 3 days

    # ADX (14)
    adx: Optional[float] = None
    adx_plus_di: Optional[float] = None
    adx_minus_di: Optional[float] = None

    # Stochastic RSI (14,14,3,3)
    stoch_rsi_k: Optional[float] = None   # smoothed %K
    stoch_rsi_d: Optional[float] = None   # %D (3-period MA of K)

    # EMA short-term
    ema_9: Optional[float] = None
    ema_21: Optional[float] = None
    ema_bearish_cross: bool = False   # EMA9 crossed below EMA21 in last 3 days
    ema_bullish_cross: bool = False   # EMA9 crossed above EMA21 in last 3 days


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

    recent5 = df.tail(5)
    high_5d = float(recent5["High"].max()) if len(recent5) >= 1 else None
    low_5d  = float(recent5["Low"].min())  if len(recent5) >= 1 else None

    rsi = close.copy()  # compute full RSI series for StochRSI
    delta = rsi.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain_s = gain.ewm(com=p["rsi_period"] - 1, min_periods=p["rsi_period"]).mean()
    avg_loss_s = loss.ewm(com=p["rsi_period"] - 1, min_periods=p["rsi_period"]).mean()
    rsi_series = 100 - (100 / (1 + avg_gain_s / avg_loss_s.replace(0, float('nan'))))

    # ── MACD (12/26/9) ────────────────────────────────────────────────────────
    macd_line_v = macd_signal_v = macd_hist_v = None
    macd_bearish_cross = macd_bullish_cross = False
    try:
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd_series = ema12 - ema26
        macd_sig = macd_series.ewm(span=9, adjust=False).mean()
        macd_hist = macd_series - macd_sig
        macd_line_v = float(macd_series.iloc[-1]) if not np.isnan(macd_series.iloc[-1]) else None
        macd_signal_v = float(macd_sig.iloc[-1]) if not np.isnan(macd_sig.iloc[-1]) else None
        macd_hist_v = float(macd_hist.iloc[-1]) if not np.isnan(macd_hist.iloc[-1]) else None
        macd_above = (macd_series > macd_sig)
        macd_bearish_cross = bool(len(macd_above) > 3 and macd_above.iloc[-4] and not macd_above.iloc[-1])
        macd_bullish_cross = bool(len(macd_above) > 3 and not macd_above.iloc[-4] and macd_above.iloc[-1])
    except Exception:
        pass

    # ── ADX (14) ──────────────────────────────────────────────────────────────
    adx_v = adx_plus_di_v = adx_minus_di_v = None
    try:
        high, low = df["High"], df["Low"]
        tr = pd.concat([(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
        up_move = high.diff()
        down_move = -low.diff()
        plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
        minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
        period = 14
        tr_s = tr.ewm(alpha=1/period, adjust=False).mean()
        plus_di_s = 100 * plus_dm.ewm(alpha=1/period, adjust=False).mean() / tr_s.replace(0, float('nan'))
        minus_di_s = 100 * minus_dm.ewm(alpha=1/period, adjust=False).mean() / tr_s.replace(0, float('nan'))
        dx = 100 * (plus_di_s - minus_di_s).abs() / (plus_di_s + minus_di_s).replace(0, float('nan'))
        adx_series = dx.ewm(alpha=1/period, adjust=False).mean()
        adx_v = float(adx_series.iloc[-1]) if not np.isnan(adx_series.iloc[-1]) else None
        adx_plus_di_v = float(plus_di_s.iloc[-1]) if not np.isnan(plus_di_s.iloc[-1]) else None
        adx_minus_di_v = float(minus_di_s.iloc[-1]) if not np.isnan(minus_di_s.iloc[-1]) else None
    except Exception:
        pass

    # ── Stochastic RSI (14,14,3,3) ────────────────────────────────────────────
    stoch_k_v = stoch_d_v = None
    try:
        stoch_period = 14
        rsi_min = rsi_series.rolling(stoch_period).min()
        rsi_max = rsi_series.rolling(stoch_period).max()
        stoch_raw = 100 * (rsi_series - rsi_min) / (rsi_max - rsi_min).replace(0, float('nan'))
        stoch_k_s = stoch_raw.rolling(3).mean()
        stoch_d_s = stoch_k_s.rolling(3).mean()
        stoch_k_v = float(stoch_k_s.iloc[-1]) if not np.isnan(stoch_k_s.iloc[-1]) else None
        stoch_d_v = float(stoch_d_s.iloc[-1]) if not np.isnan(stoch_d_s.iloc[-1]) else None
    except Exception:
        pass

    # ── EMA 9 / 21 ────────────────────────────────────────────────────────────
    ema9_v = ema21_v = None
    ema_bearish_cross = ema_bullish_cross = False
    try:
        ema9_s = close.ewm(span=9, adjust=False).mean()
        ema21_s = close.ewm(span=21, adjust=False).mean()
        ema9_v = float(ema9_s.iloc[-1]) if not np.isnan(ema9_s.iloc[-1]) else None
        ema21_v = float(ema21_s.iloc[-1]) if not np.isnan(ema21_s.iloc[-1]) else None
        ema9_above = (ema9_s > ema21_s)
        ema_bearish_cross = bool(len(ema9_above) > 3 and ema9_above.iloc[-4] and not ema9_above.iloc[-1])
        ema_bullish_cross = bool(len(ema9_above) > 3 and not ema9_above.iloc[-4] and ema9_above.iloc[-1])
    except Exception:
        pass

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
        high_5d=round(high_5d, 4) if high_5d else None,
        low_5d=round(low_5d, 4)   if low_5d  else None,
        macd_line=round(macd_line_v, 5) if macd_line_v is not None else None,
        macd_signal_line=round(macd_signal_v, 5) if macd_signal_v is not None else None,
        macd_histogram=round(macd_hist_v, 5) if macd_hist_v is not None else None,
        macd_bearish_cross=macd_bearish_cross,
        macd_bullish_cross=macd_bullish_cross,
        adx=round(adx_v, 2) if adx_v is not None else None,
        adx_plus_di=round(adx_plus_di_v, 2) if adx_plus_di_v is not None else None,
        adx_minus_di=round(adx_minus_di_v, 2) if adx_minus_di_v is not None else None,
        stoch_rsi_k=round(stoch_k_v, 2) if stoch_k_v is not None else None,
        stoch_rsi_d=round(stoch_d_v, 2) if stoch_d_v is not None else None,
        ema_9=round(ema9_v, 4) if ema9_v is not None else None,
        ema_21=round(ema21_v, 4) if ema21_v is not None else None,
        ema_bearish_cross=ema_bearish_cross,
        ema_bullish_cross=ema_bullish_cross,
    )
