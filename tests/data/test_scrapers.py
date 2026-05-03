import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from unittest.mock import patch, MagicMock
from data.rbi_scraper import fetch_rbi_data, RBIData
from data.macro_scraper import fetch_macro_data, MacroData

RBI_HTML = """
<html><body>
<table class="tablebg">
<tr><td>Repo Rate</td><td>6.25%</td></tr>
</table>
<p>Foreign Exchange Reserves as on April 25, 2026: USD 688.5 billion</p>
</body></html>
"""

def test_fetch_rbi_data_parses_repo_rate():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = RBI_HTML
    with patch("data.rbi_scraper.requests.get", return_value=mock_resp):
        result = fetch_rbi_data()
    assert isinstance(result, RBIData)
    assert result.repo_rate == 6.25

def test_fetch_rbi_data_returns_defaults_on_error():
    with patch("data.rbi_scraper.requests.get", side_effect=Exception("timeout")):
        result = fetch_rbi_data()
    assert isinstance(result, RBIData)
    assert result.repo_rate is None
    assert result.error is not None

WORLDGOVBONDS_HTML = """
<html><body>
<div class="country-flag-container">
<span class="yield10y">7.05%</span>
</div>
</body></html>
"""

def test_fetch_macro_data_returns_macro_data():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = WORLDGOVBONDS_HTML
    with patch("data.macro_scraper.requests.get", return_value=mock_resp):
        result = fetch_macro_data()
    assert isinstance(result, MacroData)

def test_fetch_macro_data_handles_error():
    with patch("data.macro_scraper.requests.get", side_effect=Exception("timeout")):
        result = fetch_macro_data()
    assert isinstance(result, MacroData)
    assert result.india_10y_yield is None
