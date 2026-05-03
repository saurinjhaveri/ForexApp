import re
from dataclasses import dataclass
from typing import Optional
import requests
from bs4 import BeautifulSoup

WORLDGOVBONDS_INDIA = "https://worldgovernmentbonds.com/country/india/"
NSE_INDICES_URL = "https://www.nseindia.com/api/allIndices"
NSDL_FII_URL = "https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx"

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ForexDashbot/1.0)"}
_NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.nseindia.com/",
}


@dataclass
class MacroData:
    india_10y_yield: Optional[float] = None
    india_vix: Optional[float] = None
    fii_equity_net_crore: Optional[float] = None
    error: Optional[str] = None


def _fetch_india_10y() -> Optional[float]:
    try:
        resp = requests.get(WORLDGOVBONDS_INDIA, headers=_HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        text = soup.get_text(" ")
        match = re.search(r"10\s*Year[^\d]*([\d]+\.[\d]+)\s*%", text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        match = re.search(r"([\d]+\.[\d]+)\s*%", text)
        if match:
            return float(match.group(1))
    except Exception:
        pass
    return None


def _fetch_india_vix() -> Optional[float]:
    try:
        import requests as req
        session = req.Session()
        session.get("https://www.nseindia.com", headers=_NSE_HEADERS, timeout=10)
        resp = session.get(NSE_INDICES_URL, headers=_NSE_HEADERS, timeout=10)
        data = resp.json()
        for idx in data.get("data", []):
            if "INDIA VIX" in idx.get("index", "").upper():
                return float(idx["last"])
    except Exception:
        pass
    return None


def _fetch_fii_flows() -> Optional[float]:
    try:
        resp = requests.get(NSDL_FII_URL, headers=_HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        text = soup.get_text(" ")
        match = re.search(
            r"(?:Equity|Equities)[^\d\-]*([\-\d,]+\.?\d*)\s*(?:Cr|crore)",
            text, re.IGNORECASE
        )
        if match:
            return float(match.group(1).replace(",", ""))
    except Exception:
        pass
    return None


def fetch_macro_data() -> MacroData:
    errors = []
    india_10y = None
    india_vix = None
    fii = None
    try:
        india_10y = _fetch_india_10y()
    except Exception as e:
        errors.append(str(e))
    try:
        india_vix = _fetch_india_vix()
    except Exception as e:
        errors.append(str(e))
    try:
        fii = _fetch_fii_flows()
    except Exception as e:
        errors.append(str(e))
    return MacroData(
        india_10y_yield=india_10y,
        india_vix=india_vix,
        fii_equity_net_crore=fii,
        error="; ".join(errors) if errors else None,
    )
