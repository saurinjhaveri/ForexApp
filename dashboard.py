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
from analysis.technicals import compute_technicals
from analysis.levels import compute_levels
from analysis.signals import generate_signals
from analysis.decision_engine import make_decision
from storage.db import init_db, save_snapshot, get_history, save_decision
from ui.charts import build_usdinr_chart
from ui.components import (
    render_decision_box,
    render_signal_breakdown,
    render_technical_summary,
    render_key_levels_table,
    render_macro_panel,
    render_news_panel,
    render_history_table,
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
    return price, futures, rbi, macro, news


if refresh:
    st.cache_data.clear()

price, futures, rbi, macro, news = load_all_data()


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


# ── Decision Engine ────────────────────────────────────────────────────────────

signals = generate_signals(
    tech, price, macro, news,
    dxy_5d_change=dxy_5d,
    brent_5d_change=brent_5d,
    usdinr_5d_change=usdinr_5d,
    levels=levels,
)
decision = make_decision(signals, spot=tech.spot)


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
    "raw_json":       json.dumps({
        "tech":    vars(tech),
        "futures": vars(futures),
        "macro":   vars(macro),
    }, default=str),
}
save_snapshot(snapshot)
history = get_history(n=30)


# ── Layout ─────────────────────────────────────────────────────────────────────

st.title("💱 USD/INR Hedging Dashboard")
st.caption(f"For exporters with USD receivables — {datetime.now().strftime('%A, %d %B %Y')}")

# Section 1 — Decision Box
render_decision_box(decision, tech.spot)
render_signal_breakdown(decision)

# Exposure context
if monthly_receivable_usd:
    spot_now = tech.spot or 94.0
    hedged_usd = monthly_receivable_usd * decision.hedge_ratio / 100
    unhedged_usd = monthly_receivable_usd - hedged_usd
    downside_3pct = unhedged_usd * spot_now * 0.03
    st.info(
        f"**Exposure:** USD {monthly_receivable_usd:,.0f} monthly receivables — "
        f"at {decision.hedge_ratio}% sold forward: "
        f"USD {hedged_usd:,.0f} locked · USD {unhedged_usd:,.0f} open. "
        f"A 3% adverse INR move on the open portion = **₹{downside_3pct:,.0f} impact**."
    )

st.divider()

# Section 2 — Technical Summary
render_technical_summary(tech, futures.near_month_price, futures.near_month_basis)
st.plotly_chart(
    build_usdinr_chart(price.usdinr_history, tech, levels, lookback_months),
    use_container_width=True,
)

st.divider()

# Section 3 — Key Levels
render_key_levels_table(tech, levels)

st.divider()

# Section 4 — Macro Dashboard
render_macro_panel(price, macro, rbi)

st.divider()

# Section 5 — News
render_news_panel(news)

st.divider()

# Section 6 — Decision History
render_history_table(history)

st.divider()

# Section 7 — Log manual decision
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
