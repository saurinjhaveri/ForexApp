import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from data.price_fetcher import fetch_price_data, PriceData

def make_mock_ticker(current_price: float, hist_rows: int = 260):
    ticker = MagicMock()
    ticker.info = {"regularMarketPrice": current_price}
    dates = pd.date_range("2025-06-01", periods=hist_rows, freq="B")
    ticker.history.return_value = pd.DataFrame({
        "Open":   [current_price * 0.999] * hist_rows,
        "High":   [current_price * 1.002] * hist_rows,
        "Low":    [current_price * 0.997] * hist_rows,
        "Close":  [current_price] * hist_rows,
        "Volume": [100000] * hist_rows,
    }, index=dates)
    return ticker

def _base_mock_tickers():
    return {
        "INR=X":    make_mock_ticker(94.95),
        "DX-Y.NYB": make_mock_ticker(104.2),
        "EURUSD=X": make_mock_ticker(1.082),
        "BZ=F":     make_mock_ticker(82.5),
        "CL=F":     make_mock_ticker(78.3),
        "^TNX":     make_mock_ticker(4.35),
        "^NSEI":    make_mock_ticker(22500.0),
        "^VIX":     make_mock_ticker(17.5),
        # EM basket
        "BRL=X":    make_mock_ticker(5.1),
        "ZAR=X":    make_mock_ticker(18.5),
        "IDR=X":    make_mock_ticker(15800.0),
    }

def test_fetch_price_data_returns_price_data():
    mock_tickers = _base_mock_tickers()
    with patch("data.price_fetcher.yf.Ticker", side_effect=lambda sym: mock_tickers[sym]):
        result = fetch_price_data()
    assert isinstance(result, PriceData)
    assert result.usdinr_spot == pytest.approx(94.95)
    assert result.dxy == pytest.approx(104.2)
    assert len(result.usdinr_history) >= 250
    assert "Close" in result.usdinr_history.columns
    assert not result.usdbrl_history.empty
    assert not result.usdzar_history.empty
    assert not result.usdidr_history.empty

def test_fetch_price_data_handles_missing_ticker():
    mock_tickers = _base_mock_tickers()
    broken = MagicMock()
    broken.info = {}
    broken.history.return_value = pd.DataFrame()
    mock_tickers["^VIX"] = broken
    with patch("data.price_fetcher.yf.Ticker", side_effect=lambda sym: mock_tickers[sym]):
        result = fetch_price_data()
    assert result.us_vix is None
