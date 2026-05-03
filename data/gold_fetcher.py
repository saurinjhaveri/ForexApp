from dataclasses import dataclass, field
from typing import Optional
import pandas as pd
import yfinance as yf
from config import GOLD_TICKERS

TROY_OZ_PER_10G = 10 / 31.1035   # 1 troy oz = 31.1035g


@dataclass
class GoldData:
    xauusd_spot: Optional[float] = None          # USD per troy oz
    silver_spot: Optional[float] = None           # USD per troy oz
    gold_silver_ratio: Optional[float] = None
    xauinr_per_10g: Optional[float] = None        # INR per 10g (most useful for Indian users)
    xauusd_history: pd.DataFrame = field(default_factory=pd.DataFrame)
    silver_history: pd.DataFrame = field(default_factory=pd.DataFrame)


def _safe_price(ticker_obj) -> Optional[float]:
    try:
        price = ticker_obj.info.get("regularMarketPrice")
        if price:
            return float(price)
        hist = ticker_obj.history(period="2d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return None


def _safe_history(ticker_obj, period: str = "2y") -> pd.DataFrame:
    try:
        hist = ticker_obj.history(period=period)
        if hist.empty:
            return pd.DataFrame()
        hist.index = pd.to_datetime(hist.index).tz_localize(None)
        return hist[["Open", "High", "Low", "Close", "Volume"]]
    except Exception:
        return pd.DataFrame()


def fetch_gold_data(usdinr_spot: Optional[float] = None) -> GoldData:
    result = GoldData()

    gold = yf.Ticker(GOLD_TICKERS["xauusd"])
    result.xauusd_spot = _safe_price(gold)
    result.xauusd_history = _safe_history(gold, "2y")

    silver = yf.Ticker(GOLD_TICKERS["silver"])
    result.silver_spot = _safe_price(silver)
    result.silver_history = _safe_history(silver, "1y")

    if result.xauusd_spot and result.silver_spot and result.silver_spot > 0:
        result.gold_silver_ratio = round(result.xauusd_spot / result.silver_spot, 1)

    if result.xauusd_spot and usdinr_spot:
        result.xauinr_per_10g = round(result.xauusd_spot * usdinr_spot * TROY_OZ_PER_10G, 0)

    return result
