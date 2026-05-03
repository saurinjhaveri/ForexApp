import json
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from config import DB_PATH
from data.price_fetcher import fetch_price_data
from data.nse_scraper import fetch_nse_futures
from data.rbi_scraper import fetch_rbi_data
from data.macro_scraper import fetch_macro_data
from data.news_fetcher import fetch_news
from data.gold_fetcher import fetch_gold_data
from analysis.technicals import compute_technicals
from analysis.levels import compute_levels
from analysis.signals import generate_signals
from analysis.decision_engine import make_decision
from analysis.gold_signals import generate_gold_signals, make_gold_decision
from analysis.trade_setup import compute_trade_setup
from storage.db import init_db, save_snapshot, get_history, save_decision, get_oi_history, get_premium_history
from ui.charts import build_usdinr_chart, build_gold_chart
from ui.components import (
    render_decision_box,
    render_signal_breakdown,
    render_technical_summary,
    render_gold_technical_summary,
    render_key_levels_table,
    render_macro_panel,
    render_news_panel,
    render_history_table,
    render_scenario_table,
    render_trade_box,
)

st.set_page_config(
    page_title="USD/INR Hedge Dashboard",
    page_icon="💱",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* ── Base ───────────────────────────────────────────────── */
    .stApp { background-color: #0f172a !important; }
    .stApp, .stApp p, .stApp span, .stApp div,
    .stApp label, .stApp li { color: #e2e8f0 !important; }
    [data-testid="stAppViewContainer"] { background-color: #0f172a !important; }
    [data-testid="stHeader"] { background-color: #0f172a !important; }

    /* ── Headings ───────────────────────────────────────────── */
    h1, h2, h3, h4, h5, h6 { color: #f1f5f9 !important; }

    /* ── Sidebar ────────────────────────────────────────────── */
    [data-testid="stSidebar"] { background-color: #1e293b !important; }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] div { color: #e2e8f0 !important; }
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] textarea {
        background-color: #0f172a !important;
        color: #f1f5f9 !important;
        border-color: #475569 !important;
    }
    [data-testid="stSidebar"] .stSelectbox > div > div {
        background-color: #0f172a !important;
        color: #f1f5f9 !important;
        border-color: #475569 !important;
    }

    /* ── Metric cards ───────────────────────────────────────── */
    [data-testid="stMetric"] {
        background: #1e293b !important;
        border-radius: 10px !important;
        padding: 14px 16px !important;
        border: 1px solid #334155 !important;
    }
    [data-testid="stMetricLabel"],
    [data-testid="stMetricLabel"] p { color: #94a3b8 !important; font-size: 0.78rem !important; }
    [data-testid="stMetricValue"],
    [data-testid="stMetricValue"] div { color: #f1f5f9 !important; font-size: 1.6rem !important; font-weight: 700 !important; }
    [data-testid="stMetricDelta"] { font-size: 0.78rem !important; }

    /* ── Inputs (main area) ─────────────────────────────────── */
    .stTextInput input, .stNumberInput input, .stTextArea textarea {
        background-color: #1e293b !important;
        color: #f1f5f9 !important;
        border-color: #475569 !important;
    }
    .stTextInput label, .stNumberInput label,
    .stTextArea label, .stSelectbox label,
    .stSlider label { color: #94a3b8 !important; }

    /* ── Selectbox dropdown ─────────────────────────────────── */
    .stSelectbox > div > div {
        background-color: #1e293b !important;
        color: #f1f5f9 !important;
        border-color: #475569 !important;
    }

    /* ── Buttons ────────────────────────────────────────────── */
    .stButton > button {
        background-color: #334155 !important;
        color: #f1f5f9 !important;
        border-color: #475569 !important;
    }
    .stButton > button:hover { background-color: #475569 !important; }

    /* ── DataFrames ─────────────────────────────────────────── */
    .stDataFrame { font-size: 0.85rem; }
    [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th {
        color: #e2e8f0 !important;
        background-color: #1e293b !important;
    }

    /* ── Expander ───────────────────────────────────────────── */
    [data-testid="stExpander"] {
        background-color: #1e293b !important;
        border-color: #334155 !important;
    }
    [data-testid="stExpander"] summary { color: #e2e8f0 !important; }

    /* ── Alert / Info boxes ─────────────────────────────────── */
    [data-testid="stAlert"] { background-color: #1e3a5f !important; border-color: #3b82f6 !important; }
    [data-testid="stAlert"] p { color: #bfdbfe !important; }

    /* ── Caption / small text ───────────────────────────────── */
    .stCaption, [data-testid="stCaptionContainer"] p { color: #64748b !important; }

    /* ── Divider ────────────────────────────────────────────── */
    hr { border-color: #334155 !important; }

    /* ── Slider ─────────────────────────────────────────────── */
    [data-testid="stSlider"] p { color: #94a3b8 !important; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙ Controls")

    st.markdown("**Mode**")
    app_mode = st.radio(
        "app_mode", ["Hedging", "Trading"],
        horizontal=True, label_visibility="collapsed",
    )
    if app_mode == "Hedging":
        st.caption("Lock in rates/prices for your existing exposure.")
    else:
        st.caption("Speculative entries with stop loss & targets.")

    st.markdown("---")
    st.markdown("**Exposure Settings**")
    monthly_receivable_usd = st.number_input(
        "Monthly Receivables (USD)", value=500_000, step=50_000, format="%d"
    )

    st.markdown("---")
    st.markdown("**Key Levels**")
    st.caption("Auto-computed from price history: weekly/monthly pivots, swing highs/lows, 200 DMA.")

    st.markdown("---")
    st.markdown("**Chart Settings**")
    lookback_months = st.slider("Chart lookback (months)", 1, 24, 6)

    st.markdown("---")
    refresh = st.button("🔄 Refresh Data", use_container_width=True)
    st.caption(f"Last refreshed: {datetime.now().strftime('%d %b %Y, %H:%M IST')}")


# ── Data loading (cached 30 min) ───────────────────────────────────────────────

@st.cache_data(ttl=1800)
def load_all_data():
    price = fetch_price_data()
    futures = fetch_nse_futures(spot_price=price.usdinr_spot)
    rbi = fetch_rbi_data()
    macro = fetch_macro_data()
    news = fetch_news()
    gold = fetch_gold_data(usdinr_spot=price.usdinr_spot)
    return price, futures, rbi, macro, news, gold


# Clear stale cache once per session (catches post-deploy schema changes)
if "cache_version" not in st.session_state:
    st.cache_data.clear()
    st.session_state["cache_version"] = "v3"

if refresh:
    st.cache_data.clear()

price, futures, rbi, macro, news, gold_data = load_all_data()


# ── Technical Analysis ─────────────────────────────────────────────────────────

if price.usdinr_history.empty:
    st.error("Could not load USD/INR price history. Check your internet connection.")
    st.stop()

tech = compute_technicals(price.usdinr_history)


# 5-day momentum calculations
def _5d_change(df: pd.DataFrame) -> Optional[float]:
    if df is None or df.empty or len(df) < 6:
        return None
    return float((df["Close"].iloc[-1] / df["Close"].iloc[-6] - 1) * 100)


dxy_5d    = _5d_change(price.dxy_history)
brent_5d  = _5d_change(price.brent_history)
usdinr_5d = _5d_change(price.usdinr_history)

# ── EM basket divergence ───────────────────────────────────────────────────────
em_changes = [
    c for c in [
        _5d_change(price.usdbrl_history),
        _5d_change(price.usdzar_history),
        _5d_change(price.usdidr_history),
    ] if c is not None
]
em_basket_5d     = sum(em_changes) / len(em_changes) if em_changes else None
inr_em_divergence = (
    (usdinr_5d - em_basket_5d) if usdinr_5d is not None and em_basket_5d is not None
    else None
)

# ── Forward premium percentile rank ───────────────────────────────────────────
init_db()
premium_history = [x for x in get_premium_history(90) if x is not None]
forward_premium_pctile_rank: Optional[float] = None
if len(premium_history) >= 10 and futures.annualized_premium_pct is not None:
    below = sum(1 for p in premium_history if p <= futures.annualized_premium_pct)
    forward_premium_pctile_rank = below / len(premium_history) * 100

# ── FX reserves 7-day change ──────────────────────────────────────────────────
reserves_7d_change: Optional[float] = None
hist_7d = get_history(n=7)
if len(hist_7d) >= 2:
    newest = next((r["raw_json"] for r in hist_7d if r.get("raw_json")), None)
    oldest = next((r["raw_json"] for r in reversed(hist_7d) if r.get("raw_json")), None)
    try:
        if newest and oldest:
            import json as _json
            r_new = _json.loads(newest).get("macro", {})
            r_old = _json.loads(oldest).get("macro", {})
            fx_new = r_new.get("fx_reserves_usd_bn") or rbi.fx_reserves_usd_bn
            fx_old = r_old.get("fx_reserves_usd_bn")
            if fx_new and fx_old:
                reserves_7d_change = fx_new - fx_old
    except Exception:
        pass

# ── Compute key levels from price history ──────────────────────────────────────

try:
    levels = compute_levels(price.usdinr_history, tech.spot, sma_200=tech.sma_200)
except Exception:
    levels = []

# Show computed levels in sidebar
with st.sidebar:
    if levels:
        rows = []
        for lvl in levels:
            dist_pct = (tech.spot - lvl.price) / lvl.price * 100
            rows.append({
                "Level": lvl.name,
                "Price": f"{lvl.price:.4f}",
                "Dist": f"{dist_pct:+.2f}%",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ── OI positioning context ─────────────────────────────────────────────────────

init_db()  # ensure schema is up to date before reading OI history
oi_history = [x for x in get_oi_history(20) if x is not None]
oi_pct_above_avg: Optional[float] = None
if len(oi_history) >= 5 and futures.near_month_oi:
    oi_avg = sum(oi_history) / len(oi_history)
    if oi_avg > 0:
        oi_pct_above_avg = (futures.near_month_oi - oi_avg) / oi_avg * 100


# ── Decision Engine ────────────────────────────────────────────────────────────

signals = generate_signals(
    tech, price, macro, news,
    dxy_5d_change=dxy_5d,
    brent_5d_change=brent_5d,
    usdinr_5d_change=usdinr_5d,
    levels=levels,
    futures=futures,
    oi_pct_above_avg=oi_pct_above_avg,
    inr_em_divergence=inr_em_divergence,
    forward_premium_pctile_rank=forward_premium_pctile_rank,
    reserves_7d_change=reserves_7d_change,
)
decision = make_decision(signals, spot=tech.spot, levels=levels, inr_em_divergence=inr_em_divergence)


# ── Persist daily snapshot ─────────────────────────────────────────────────────

init_db()
today = datetime.now().strftime("%Y-%m-%d")
snapshot = {
    "date":           today,
    "usdinr_spot":    tech.spot,
    "rsi_daily":      tech.rsi_daily,
    "dxy":            price.dxy,
    "brent":          price.brent,
    "recommendation": decision.recommendation,
    "hedge_ratio":    decision.hedge_ratio,
    "confidence":     decision.confidence,
    "rationale":      decision.rationale,
    "score":          decision.score,
    "near_month_oi":      futures.near_month_oi,
    "forward_premium_ann": futures.annualized_premium_pct,
    "raw_json":       json.dumps({
        "tech":    vars(tech),
        "futures": vars(futures),
        "macro":   vars(macro),
    }, default=str),
}
save_snapshot(snapshot)
history = get_history(n=30)


# ── Gold analysis ─────────────────────────────────────────────────────────────

gold_5d: Optional[float] = None
if not gold_data.xauusd_history.empty and len(gold_data.xauusd_history) >= 6:
    gold_5d = float(
        (gold_data.xauusd_history["Close"].iloc[-1] /
         gold_data.xauusd_history["Close"].iloc[-6] - 1) * 100
    )

gold_tech = None
gold_levels = []
gold_signals = []
gold_decision = None
if not gold_data.xauusd_history.empty:
    try:
        gold_tech = compute_technicals(gold_data.xauusd_history)
        gold_levels = compute_levels(gold_data.xauusd_history, gold_tech.spot, sma_200=gold_tech.sma_200)
    except Exception:
        gold_tech = None
        gold_levels = []
    if gold_tech:
        gold_signals = generate_gold_signals(
            gold_tech, gold_data,
            dxy=price.dxy,
            dxy_5d_change=dxy_5d,
            us_yield_5d_change=None,
            us_vix=price.us_vix,
            gold_5d_change=gold_5d,
            levels=gold_levels,
        )
        gold_decision = make_gold_decision(gold_signals, spot=gold_tech.spot, levels=gold_levels)


# ── Layout ─────────────────────────────────────────────────────────────────────

st.title("📊 Hedge Dashboard")
st.caption(datetime.now().strftime('%A, %d %B %Y'))

tab_fx, tab_gold = st.tabs(["💱 USD/INR", "🥇 Gold"])


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — USD/INR
# ════════════════════════════════════════════════════════════════════════════════
with tab_fx:
    if app_mode == "Hedging":
        render_decision_box(decision, tech.spot)
        render_signal_breakdown(decision)
        if monthly_receivable_usd:
            render_scenario_table(
                monthly_receivable_usd=monthly_receivable_usd,
                hedge_ratio=decision.hedge_ratio,
                spot=tech.spot or 84.0,
                bear_pct=3.0,
                bull_pct=1.5,
                forward_rate=futures.near_month_price,
            )
    else:
        fx_trade = compute_trade_setup(decision.score, tech, levels, decision.signals, decision.confidence)
        render_trade_box(fx_trade, tech.spot, instrument="USD/INR")
        render_signal_breakdown(decision)

    st.divider()

    render_technical_summary(
        tech,
        futures.near_month_price,
        futures.near_month_basis,
        futures_oi=futures.near_month_oi,
        futures_oi_change=futures.near_month_oi_change,
        oi_pct_above_avg=oi_pct_above_avg,
        annualized_premium=futures.annualized_premium_pct,
        forward_premium_pctile=forward_premium_pctile_rank,
        inr_em_divergence=inr_em_divergence,
        em_basket_5d=em_basket_5d,
    )
    st.plotly_chart(
        build_usdinr_chart(price.usdinr_history, tech, levels, lookback_months),
        use_container_width=True,
    )

    st.divider()
    render_key_levels_table(tech, levels)

    st.divider()
    render_macro_panel(price, macro, rbi)

    st.divider()
    render_news_panel(news)

    st.divider()
    render_history_table(history)

    st.divider()
    with st.expander("Log today's actual decision"):
        action = st.selectbox(
            "Action taken",
            ["WAIT", "Hedged 25%", "Hedged 50%", "Hedged 75%", "Hedged 100%"],
        )
        pct = st.slider("Hedge %", 0, 100, 0, step=25)
        notes = st.text_area("Notes (optional)")
        if st.button("Save Decision"):
            save_decision({
                "date":         today,
                "action_taken": action,
                "hedge_pct":    pct,
                "notes":        notes,
            })
            st.success("Decision logged.")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — GOLD
# ════════════════════════════════════════════════════════════════════════════════
with tab_gold:
    if gold_decision is None or gold_tech is None:
        st.error("Could not load gold price data. Check your internet connection.")
    else:
        if app_mode == "Hedging":
            render_decision_box(gold_decision, gold_tech.spot)
            render_signal_breakdown(gold_decision)
            if monthly_receivable_usd:
                render_scenario_table(
                    monthly_receivable_usd=monthly_receivable_usd,
                    hedge_ratio=gold_decision.hedge_ratio,
                    spot=gold_tech.spot or 2400.0,
                    bear_pct=4.0,
                    bull_pct=2.0,
                    forward_rate=None,
                )
        else:
            gold_trade = compute_trade_setup(
                gold_decision.score, gold_tech, gold_levels,
                gold_decision.signals, gold_decision.confidence,
            )
            render_trade_box(gold_trade, gold_tech.spot, instrument="Gold XAU/USD")
            render_signal_breakdown(gold_decision)

        st.divider()

        render_gold_technical_summary(
            gold_tech, gold_data,
            dxy=price.dxy,
            us_vix=price.us_vix,
            gold_5d_change=gold_5d,
        )
        st.plotly_chart(
            build_gold_chart(gold_data.xauusd_history, gold_tech, gold_levels, lookback_months),
            use_container_width=True,
        )

        st.divider()
        render_key_levels_table(gold_tech, gold_levels)
