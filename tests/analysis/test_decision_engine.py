import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import pytest
from analysis.technicals import TechnicalSnapshot
from analysis.signals import generate_signals
from analysis.decision_engine import make_decision, Decision
from data.price_fetcher import PriceData
from data.macro_scraper import MacroData
from data.news_fetcher import NewsItem

def base_tech() -> TechnicalSnapshot:
    return TechnicalSnapshot(
        spot=94.95, rsi_daily=55.0, rsi_weekly=52.0,
        sma_50=93.5, sma_200=91.0,
        pct_above_sma50=1.55, pct_above_sma200=4.34,
        bb_upper=96.0, bb_mid=94.0, bb_lower=92.0,
        bb_pct_b=0.55, bb_bandwidth=4.25,
        atr_14=0.42, atr_90d_avg=0.38, atr_elevated=False,
    )

def base_price() -> PriceData:
    p = PriceData()
    p.dxy = 104.2; p.brent = 82.5; p.us_10y_yield = 4.35
    p.us_vix = 17.5
    return p

def test_cover_now_on_overbought_dxy_falling():
    tech = base_tech()
    tech.rsi_daily = 74.0
    tech.bb_pct_b = 0.95
    tech.atr_elevated = True
    price = base_price()
    price.dxy = 101.5  # falling (need history context, signals use snapshot only)
    macro = MacroData(india_10y_yield=7.05, india_vix=13.5, fii_equity_net_crore=2500)
    signals = generate_signals(tech, price, macro, [], dxy_5d_change=-1.5)
    decision = make_decision(signals)
    assert isinstance(decision, Decision)
    assert decision.hedge_ratio >= 50

def test_wait_on_low_rsi_strong_dxy():
    tech = base_tech()
    tech.rsi_daily = 38.0
    tech.bb_pct_b = 0.15
    price = base_price()
    macro = MacroData(india_10y_yield=7.05, india_vix=22.0, fii_equity_net_crore=-1500)
    signals = generate_signals(tech, price, macro, [], dxy_5d_change=+1.2)
    decision = make_decision(signals)
    assert decision.hedge_ratio <= 25

def test_decision_has_rationale():
    tech = base_tech()
    price = base_price()
    macro = MacroData()
    signals = generate_signals(tech, price, macro, [], dxy_5d_change=0)
    decision = make_decision(signals)
    assert len(decision.rationale) > 10
    assert decision.confidence in ("Low", "Medium", "High")
