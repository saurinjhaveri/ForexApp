import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from data.price_fetcher import PriceData
from data.macro_scraper import MacroData
from data.rbi_scraper import RBIData
from data.nse_scraper import FuturesData
from analysis.technicals import compute_technicals
from analysis.levels import compute_levels, KeyLevel
from analysis.signals import generate_signals
from analysis.decision_engine import make_decision

def make_test_df(n=260, start=94.0):
    np.random.seed(7)
    prices = [start]
    for _ in range(n - 1):
        prices.append(prices[-1] * (1 + np.random.normal(0.0002, 0.003)))
    dates = pd.date_range("2024-06-01", periods=n, freq="B")
    return pd.DataFrame({
        "Open":   [p * 0.999 for p in prices],
        "High":   [p * 1.002 for p in prices],
        "Low":    [p * 0.998 for p in prices],
        "Close":  prices,
        "Volume": [1_000_000] * n,
    }, index=dates)

def test_full_pipeline_runs_without_error():
    df = make_test_df()
    tech = compute_technicals(df)
    price = PriceData(usdinr_spot=tech.spot, dxy=104.2, brent=82.5, us_10y_yield=4.35, us_vix=17.5)
    macro = MacroData(india_10y_yield=7.05, india_vix=14.0, fii_equity_net_crore=1200)
    levels = compute_levels(df, tech.spot, sma_200=tech.sma_200)
    signals = generate_signals(tech, price, macro, [], dxy_5d_change=-0.8, brent_5d_change=1.5, levels=levels)
    decision = make_decision(signals)
    assert decision.recommendation in ("HOLD — Let It Run", "SELL 25% FORWARD", "SELL 50% FORWARD", "SELL 75% FORWARD", "SELL ALL FORWARD")
    assert 0 <= decision.hedge_ratio <= 100
    assert len(decision.rationale) > 5


def test_compute_levels():
    df = make_test_df(n=260)
    tech = compute_technicals(df)
    levels = compute_levels(df, tech.spot, sma_200=tech.sma_200)

    assert len(levels) > 0, "Should produce at least one level"
    for lvl in levels:
        assert isinstance(lvl, KeyLevel)
        assert lvl.level_type in ("resistance", "support", "pivot")
        assert lvl.source in ("weekly_pivot", "monthly_pivot", "swing", "200dma")
        assert 1 <= lvl.strength <= 3
        # All levels within ±8% of spot
        assert abs(lvl.price - tech.spot) / tech.spot <= 0.08

    prices = [l.price for l in levels]
    assert len(prices) == len(set(prices)), "No duplicate prices after dedup"

    # Levels should be sorted descending by price
    assert prices == sorted(prices, reverse=True)

def test_chart_import():
    from ui.charts import build_usdinr_chart
    assert callable(build_usdinr_chart)

def test_db_round_trip():
    from storage.db import init_db, save_snapshot, get_history
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = f.name
    try:
        init_db(db)
        save_snapshot({
            "date": "2026-05-03", "usdinr_spot": 94.95, "rsi_daily": 68.0,
            "dxy": 104.2, "brent": 82.5, "recommendation": "COVER PARTIAL",
            "hedge_ratio": 50, "confidence": "Medium",
            "rationale": "Test", "score": 5, "raw_json": "{}",
        }, db_path=db)
        hist = get_history(5, db_path=db)
        assert hist[0]["hedge_ratio"] == 50
    finally:
        os.unlink(db)
