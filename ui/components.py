from typing import List, Optional
import streamlit as st
import pandas as pd
from analysis.decision_engine import Decision
from analysis.technicals import TechnicalSnapshot
from data.price_fetcher import PriceData
from data.macro_scraper import MacroData
from data.rbi_scraper import RBIData
from data.news_fetcher import NewsItem


def render_decision_box(decision: Decision, spot: Optional[float]) -> None:
    color = decision.color
    st.markdown(f"""
    <div style="
        background: {color}22;
        border: 2px solid {color};
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 20px;
    ">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
            <div>
                <div style="font-size:0.85rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.1em;">
                    Hedge Recommendation
                </div>
                <div style="font-size:2rem; font-weight:800; color:{color}; line-height:1.2;">
                    {decision.recommendation}
                </div>
                <div style="font-size:0.95rem; color:#e2e8f0; margin-top:6px;">
                    {decision.rationale}
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:1.5rem; font-weight:700; color:#f8fafc;">
                    {decision.hedge_ratio}% hedge
                </div>
                <div style="font-size:0.85rem; color:#94a3b8;">
                    Confidence: <span style="color:{color}; font-weight:600;">{decision.confidence}</span>
                </div>
                <div style="font-size:0.85rem; color:#94a3b8; margin-top:4px;">
                    Signal score: {decision.score:+.0f}
                </div>
            </div>
        </div>
        <div style="margin-top:12px; border-top:1px solid {color}44; padding-top:10px;">
            <div style="font-size:0.8rem; color:#94a3b8;">Spot: <b style="color:#f1f5f9;">{f"₹{spot:.4f}" if spot else "N/A"}</b></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_signal_breakdown(decision: Decision) -> None:
    with st.expander("Signal Breakdown", expanded=False):
        for sig in sorted(decision.signals, key=lambda s: abs(s.weight), reverse=True):
            icon = "🟢" if sig.weight < 0 else "🔴"
            direction = "→ WAIT" if sig.weight < 0 else "→ COVER"
            st.markdown(
                f"{icon} **[{sig.weight:+d}]** {direction} — {sig.description}"
            )
        if not decision.signals:
            st.info("No active signals generated.")


def render_technical_summary(tech: TechnicalSnapshot, futures_near: Optional[float], futures_basis: Optional[float]) -> None:
    st.subheader("Spot & Technical Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("USD/INR Spot", f"{tech.spot:.4f}")
    c2.metric("RSI (14 Daily)", f"{tech.rsi_daily:.1f}" if tech.rsi_daily else "N/A")
    c3.metric("RSI (14 Weekly)", f"{tech.rsi_weekly:.1f}" if tech.rsi_weekly else "N/A")
    c4.metric("ATR (14)", f"{tech.atr_14:.4f}" if tech.atr_14 else "N/A",
              delta=f"90d avg: {tech.atr_90d_avg:.4f}" if tech.atr_90d_avg else None)

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("SMA 50", f"{tech.sma_50:.4f}" if tech.sma_50 else "N/A",
              delta=f"{tech.pct_above_sma50:+.2f}%" if tech.pct_above_sma50 else None)
    c6.metric("SMA 200", f"{tech.sma_200:.4f}" if tech.sma_200 else "N/A",
              delta=f"{tech.pct_above_sma200:+.2f}%" if tech.pct_above_sma200 else None)
    c7.metric("BB %B", f"{tech.bb_pct_b*100:.1f}%" if tech.bb_pct_b is not None else "N/A")
    near_label = f"{futures_near:.4f}" if futures_near else "N/A"
    basis_label = f"Basis: {futures_basis:+.4f}" if futures_basis else None
    c8.metric("Futures (Near)", near_label, delta=basis_label)


def render_key_levels_table(tech: TechnicalSnapshot, levels: List[dict]) -> None:
    st.subheader("Key Levels")
    spot = tech.spot
    rows = []
    for lvl in levels:
        price = lvl["price"]
        if price <= 0:
            continue
        dist_pct = (spot - price) / price * 100
        if abs(dist_pct) < 0.5:
            traffic = "🔴"
        elif abs(dist_pct) < 2.0:
            traffic = "🟡"
        else:
            traffic = "🟢"
        direction = "▲ Above" if dist_pct > 0 else "▼ Below"
        rows.append({
            "": traffic,
            "Level": lvl["name"],
            "Price": f"{price:.4f}",
            "Type": lvl.get("type", "").capitalize(),
            "Distance": f"{dist_pct:+.2f}%",
            "Position": direction,
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_macro_panel(price: PriceData, macro: MacroData, rbi: RBIData) -> None:
    st.subheader("Macro Dashboard")

    def fmt(val, decimals=2, suffix=""):
        return f"{val:.{decimals}f}{suffix}" if val is not None else "N/A"

    rows = [
        {"Indicator": "DXY (Dollar Index)",     "Value": fmt(price.dxy),         "Hedge Signal": "⬆ WAIT" if price.dxy and price.dxy > 104 else "⬇ COVER"},
        {"Indicator": "Brent Crude ($/bbl)",     "Value": fmt(price.brent),       "Hedge Signal": "⬆ WAIT" if price.brent and price.brent > 85 else "—"},
        {"Indicator": "WTI Crude ($/bbl)",       "Value": fmt(price.wti),         "Hedge Signal": "—"},
        {"Indicator": "US 10Y Yield (%)",        "Value": fmt(price.us_10y_yield),"Hedge Signal": "⬆ WAIT" if price.us_10y_yield and price.us_10y_yield > 4.5 else "—"},
        {"Indicator": "India 10Y Yield (%)",     "Value": fmt(macro.india_10y_yield), "Hedge Signal": "—"},
        {"Indicator": "Yield Diff (IN-US) bps",
            "Value": fmt((macro.india_10y_yield or 0) - (price.us_10y_yield or 0), decimals=0, suffix="bps"), "Hedge Signal": "—"},
        {"Indicator": "Nifty 50",                "Value": fmt(price.nifty, 0),    "Hedge Signal": "—"},
        {"Indicator": "US VIX",                  "Value": fmt(price.us_vix),      "Hedge Signal": "⬆ COVER" if price.us_vix and price.us_vix > 25 else "—"},
        {"Indicator": "India VIX",               "Value": fmt(macro.india_vix),   "Hedge Signal": "⬆ COVER" if macro.india_vix and macro.india_vix < 14 else "—"},
        {"Indicator": "RBI Repo Rate (%)",       "Value": fmt(rbi.repo_rate),     "Hedge Signal": "—"},
        {"Indicator": "FX Reserves (USD bn)",    "Value": fmt(rbi.fx_reserves_usd_bn, 1), "Hedge Signal": "—"},
        {"Indicator": "FII Net Equity (₹Cr)",   "Value": fmt(macro.fii_equity_net_crore, 0),
            "Hedge Signal": "⬆ COVER" if macro.fii_equity_net_crore and macro.fii_equity_net_crore > 1000 else
                            ("⬆ WAIT" if macro.fii_equity_net_crore and macro.fii_equity_net_crore < -1000 else "—")},
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_news_panel(news: List[NewsItem]) -> None:
    st.subheader("News & Sentiment (Last 24h)")
    if not news:
        st.info("No recent news fetched.")
        return
    flagged = [n for n in news if n.flagged]
    if flagged:
        st.warning(f"⚠ {len(flagged)} headline(s) flagged for key terms")
    for item in news:
        prefix = "🚨 " if item.flagged else ""
        tags = " ".join(f"`{kw}`" for kw in item.matched_keywords) if item.flagged else ""
        st.markdown(f"**{prefix}[{item.title}]({item.url})**  {tags}  \n*{item.published}*")
        st.divider()


def render_history_table(history: List[dict]) -> None:
    st.subheader("Decision History")
    if not history:
        st.info("No historical snapshots yet. Check back after the first daily run.")
        return
    df = pd.DataFrame(history)[
        ["date", "usdinr_spot", "recommendation", "hedge_ratio", "confidence", "rsi_daily", "dxy", "score"]
    ].rename(columns={
        "date": "Date", "usdinr_spot": "Spot", "recommendation": "Rec",
        "hedge_ratio": "Hedge %", "confidence": "Conf",
        "rsi_daily": "RSI", "dxy": "DXY", "score": "Score",
    })
    st.dataframe(df, use_container_width=True, hide_index=True)
