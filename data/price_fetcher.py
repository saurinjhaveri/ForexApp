from dataclasses import dataclass, field
from typing import Optional
import pandas as pd
import yfinance as yf
from config import TICKERS


@dataclass
class PriceData:
    usdinr_spot: Optional[float] = None
    dxy: Optional[float] = None
    eurusd: Optional[float] = None
    brent: Optional[float] = None
    wti: Optional[float] = None
    us_10y_yield: Optional[float] = None
    nifty: Optional[float] = None
    us_vix: Optional[float] = None
    usdinr_history: pd.DataFrame = field(default_factory=pd.DataFrame)
    dxy_history: pd.DataFrame = field(default_factory=pd.DataFrame)
    brent_history: pd.DataFrame = field(default_factory=pd.DataFrame)
    usdbrl_history: pd.DataFrame = field(default_factory=pd.DataFrame)
    usdzar_history: pd.DataFrame = field(default_factory=pd.DataFrame)
    usdidr_history: pd.DataFrame = field(default_factory=pd.DataFrame)


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


def _safe_history(ticker_obj, period: str = "1y") -> pd.DataFrame:
    try:
        hist = ticker_obj.history(period=period)
        if hist.empty:
            return pd.DataFrame()
        hist.index = pd.to_datetime(hist.index).tz_localize(None)
        return hist[["Open", "High", "Low", "Close", "Volume"]]
    except Exception:
        return pd.DataFrame()


def fetch_price_data() -> PriceData:
    result = PriceData()
    for attr, sym in [
        ("_usdinr", TICKERS["usdinr_spot"]),
        ("_dxy",    TICKERS["dxy"]),
        ("_eurusd", TICKERS["eurusd"]),
        ("_brent",  TICKERS["brent"]),
        ("_wti",    TICKERS["wti"]),
        ("_us10y",  TICKERS["us_10y"]),
        ("_nifty",  TICKERS["nifty"]),
        ("_usvix",  TICKERS["us_vix"]),
        ("_usdbrl", TICKERS["usdbrl"]),
        ("_usdzar", TICKERS["usdzar"]),
        ("_usdidr", TICKERS["usdidr"]),
    ]:
        t = yf.Ticker(sym)
        if attr == "_usdinr":
            result.usdinr_spot = _safe_price(t)
            result.usdinr_history = _safe_history(t, "2y")
        elif attr == "_dxy":
            result.dxy = _safe_price(t)
            result.dxy_history = _safe_history(t, "1y")
        elif attr == "_eurusd":
            result.eurusd = _safe_price(t)
        elif attr == "_brent":
            result.brent = _safe_price(t)
            result.brent_history = _safe_history(t, "1y")
        elif attr == "_wti":
            result.wti = _safe_price(t)
        elif attr == "_us10y":
            result.us_10y_yield = _safe_price(t)
        elif attr == "_nifty":
            result.nifty = _safe_price(t)
        elif attr == "_usvix":
            result.us_vix = _safe_price(t)
        elif attr == "_usdbrl":
            result.usdbrl_history = _safe_history(t, "1y")
        elif attr == "_usdzar":
            result.usdzar_history = _safe_history(t, "1y")
        elif attr == "_usdidr":
            result.usdidr_history = _safe_history(t, "1y")
    return result
