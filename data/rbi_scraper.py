import re
from dataclasses import dataclass
from typing import Optional, List
import requests
from bs4 import BeautifulSoup

RBI_MONETARY_URL = "https://www.rbi.org.in/Scripts/BS_ViewMastersiteMap.aspx"
RBI_PRESS_URL    = "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx"


@dataclass
class RBIData:
    repo_rate: Optional[float] = None
    fx_reserves_usd_bn: Optional[float] = None
    press_releases: List[dict] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.press_releases is None:
            self.press_releases = []


_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ForexDashbot/1.0)"}


def _parse_repo_rate(html: str) -> Optional[float]:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ")
    match = re.search(r"Repo\s+Rate[^\d]*(\d+\.?\d*)\s*%", text, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


def _parse_fx_reserves(html: str) -> Optional[float]:
    match = re.search(
        r"Foreign Exchange Reserves[^\d]*([\d,]+\.?\d*)\s*(billion|USD bn|USD)",
        html, re.IGNORECASE
    )
    if match:
        val = float(match.group(1).replace(",", ""))
        return val
    return None


def _fetch_press_releases() -> List[dict]:
    try:
        resp = requests.get(RBI_PRESS_URL, headers=_HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "lxml")
        items = []
        for row in soup.select("table tr")[1:11]:
            cols = row.find_all("td")
            if len(cols) >= 2:
                items.append({
                    "date": cols[0].get_text(strip=True),
                    "title": cols[1].get_text(strip=True),
                    "url": "https://www.rbi.org.in" + (cols[1].find("a") or {}).get("href", ""),
                })
        return items
    except Exception:
        return []


def fetch_rbi_data() -> RBIData:
    try:
        resp = requests.get(RBI_MONETARY_URL, headers=_HEADERS, timeout=10)
        repo = _parse_repo_rate(resp.text)
        fx = _parse_fx_reserves(resp.text)
        releases = _fetch_press_releases()
        return RBIData(repo_rate=repo, fx_reserves_usd_bn=fx, press_releases=releases)
    except Exception as e:
        try:
            FALLBACK = "https://www.rbi.org.in/home.aspx"
            resp = requests.get(FALLBACK, headers=_HEADERS, timeout=10)
            return RBIData(
                repo_rate=_parse_repo_rate(resp.text),
                fx_reserves_usd_bn=None,
                press_releases=_fetch_press_releases(),
            )
        except Exception as e2:
            return RBIData(error=str(e2))
