import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import numpy as np
import pandas as pd
import pytest
from analysis.technicals import compute_technicals, TechnicalSnapshot

def make_price_series(n=260, start=90.0, trend=0.01):
    np.random.seed(42)
    prices = [start]
    for _ in range(n - 1):
        prices.append(prices[-1] * (1 + trend / 100 + np.random.normal(0, 0.003)))
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    return pd.DataFrame({
        "Open":   [p * 0.999 for p in prices],
        "High":   [p * 1.003 for p in prices],
        "Low":    [p * 0.997 for p in prices],
        "Close":  prices,
        "Volume": [1_000_000] * n,
    }, index=dates)

def test_compute_technicals_returns_snapshot():
    df = make_price_series(260, start=90.0, trend=0.02)
    snap = compute_technicals(df)
    assert isinstance(snap, TechnicalSnapshot)
    assert 0 <= snap.rsi_daily <= 100
    assert snap.sma_50 > 0
    assert snap.sma_200 > 0
    assert snap.atr_14 > 0
    assert snap.bb_upper > snap.bb_mid > snap.bb_lower

def test_rsi_overbought_on_rising_prices():
    df = make_price_series(260, start=90.0, trend=0.15)
    snap = compute_technicals(df)
    assert snap.rsi_daily > 60

def test_rsi_oversold_on_falling_prices():
    df = make_price_series(260, start=95.0, trend=-0.15)
    snap = compute_technicals(df)
    assert snap.rsi_daily < 40

def test_distance_from_sma():
    df = make_price_series(260, start=90.0, trend=0.02)
    snap = compute_technicals(df)
    spot = df["Close"].iloc[-1]
    expected_dist_50 = (spot - snap.sma_50) / snap.sma_50 * 100
    assert abs(snap.pct_above_sma50 - expected_dist_50) < 0.01
