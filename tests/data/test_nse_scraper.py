import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
from unittest.mock import patch, MagicMock
from data.nse_scraper import fetch_nse_futures, FuturesData

MOCK_NSE_RESPONSE = {
    "stocks": [
        {
            "metadata": {
                "expiryDate": "29-May-2026",
                "instrumentType": "Currency Futures",
            },
            "marketDeptOrderBook": {
                "tradeInfo": {"lastPrice": 95.10}
            }
        },
        {
            "metadata": {
                "expiryDate": "26-Jun-2026",
                "instrumentType": "Currency Futures",
            },
            "marketDeptOrderBook": {
                "tradeInfo": {"lastPrice": 95.45}
            }
        },
    ]
}

def test_fetch_nse_futures_parses_correctly():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_NSE_RESPONSE

    with patch("data.nse_scraper.requests.Session") as mock_session_cls:
        session = MagicMock()
        mock_session_cls.return_value = session
        session.get.return_value = mock_resp

        result = fetch_nse_futures(spot_price=94.95)

    assert isinstance(result, FuturesData)
    assert result.near_month_price == pytest.approx(95.10)
    assert result.next_month_price == pytest.approx(95.45)
    assert result.near_month_basis == pytest.approx(95.10 - 94.95)

def test_fetch_nse_futures_falls_back_on_error():
    with patch("data.nse_scraper.requests.Session") as mock_session_cls:
        session = MagicMock()
        mock_session_cls.return_value = session
        session.get.side_effect = Exception("connection refused")
        result = fetch_nse_futures(spot_price=94.95)

    assert isinstance(result, FuturesData)
    assert result.near_month_price is None
    assert result.error is not None
