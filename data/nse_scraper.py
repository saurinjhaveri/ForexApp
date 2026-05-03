from dataclasses import dataclass
from typing import Optional
import requests


@dataclass
class FuturesData:
    near_month_price: Optional[float] = None
    near_month_expiry: Optional[str] = None
    next_month_price: Optional[float] = None
    next_month_expiry: Optional[str] = None
    near_month_basis: Optional[float] = None           # futures - spot
    near_month_oi: Optional[float] = None              # open interest (contracts)
    near_month_oi_change: Optional[float] = None       # change from prev session
    near_month_oi_change_pct: Optional[float] = None
    annualized_premium_pct: Optional[float] = None     # (basis/spot) × (365/dte) × 100
    error: Optional[str] = None


NSE_API_URL = "https://www.nseindia.com/api/quote-derivative?symbol=USDINR"
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}


def fetch_nse_futures(spot_price: Optional[float] = None) -> FuturesData:
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=10)
        resp = session.get(NSE_API_URL, headers=NSE_HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        futures = [
            s for s in data.get("stocks", [])
            if "Futures" in s.get("metadata", {}).get("instrumentType", "")
        ]
        from datetime import datetime
        def _parse_expiry(s):
            try:
                return datetime.strptime(s["metadata"]["expiryDate"], "%d-%b-%Y")
            except Exception:
                return datetime.max
        futures.sort(key=_parse_expiry)

        result = FuturesData()
        if len(futures) >= 1:
            near = futures[0]
            trade  = near.get("marketDeptOrderBook", {}).get("tradeInfo", {})
            other  = near.get("marketDeptOrderBook", {}).get("otherInfo", {})

            result.near_month_price = _safe_float(trade.get("lastPrice"))
            result.near_month_expiry = near["metadata"]["expiryDate"]

            result.near_month_oi            = _safe_float(other.get("openInterest"))
            result.near_month_oi_change     = _safe_float(other.get("changeinOpenInterest"))
            result.near_month_oi_change_pct = _safe_float(other.get("pchangeinOpenInterest"))

            if spot_price and result.near_month_price:
                result.near_month_basis = round(result.near_month_price - spot_price, 4)
                try:
                    expiry_dt = datetime.strptime(result.near_month_expiry, "%d-%b-%Y")
                    dte = max((expiry_dt - datetime.now()).days, 1)
                    result.annualized_premium_pct = round(
                        (result.near_month_basis / spot_price) * (365 / dte) * 100, 2
                    )
                except Exception:
                    pass

        if len(futures) >= 2:
            nxt = futures[1]
            result.next_month_price  = _safe_float(
                nxt["marketDeptOrderBook"]["tradeInfo"]["lastPrice"]
            )
            result.next_month_expiry = nxt["metadata"]["expiryDate"]

        return result

    except Exception as e:
        return FuturesData(error=str(e))


def _safe_float(val) -> Optional[float]:
    try:
        v = float(val)
        return v if v != 0 else None
    except (TypeError, ValueError):
        return None
