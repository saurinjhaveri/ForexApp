from typing import List, Optional
import streamlit as st
import pandas as pd
from analysis.decision_engine import Decision
from analysis.technicals import TechnicalSnapshot
from data.price_fetcher import PriceData
from data.macro_scraper import MacroData
from data.rbi_scraper import RBIData
from data.news_fetcher import NewsItem


def render_decision_box(decision: Decision, spot: Optional[float], budget_rate: Optional[float] = None) -> None:
    color = decision.color
    spot_val = spot or decision.spot

    # Bonus above budget
    bonus_html = ""
    if budget_rate and spot_val:
        bonus = spot_val - budget_rate
        bonus_pct = bonus / budget_rate * 100
        bonus_html = f"""
        <div style="display:flex; gap:24px; flex-wrap:wrap; margin-bottom:14px;">
            <div>
                <div style="font-size:0.7rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.08em;">Spot</div>
                <div style="font-size:1.1rem; font-weight:700; color:#f1f5f9;">₹{spot_val:.4f}</div>
            </div>
            <div>
                <div style="font-size:0.7rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.08em;">Budget Rate</div>
                <div style="font-size:1.1rem; font-weight:700; color:#94a3b8;">₹{budget_rate:.2f}</div>
            </div>
            <div>
                <div style="font-size:0.7rem; color:#94a3b8; text-transform:uppercase; letter-spacing:0.08em;">Bonus Above Budget</div>
                <div style="font-size:1.1rem; font-weight:700; color:#22c55e;">+₹{bonus:.4f} / USD &nbsp;(+{bonus_pct:.1f}%)</div>
            </div>
        </div>"""

    # Key reasons bullets
    reasons_html = ""
    if decision.key_reasons:
        bullets = "".join(
            f'<div style="margin:5px 0; padding:8px 12px; background:rgba(255,255,255,0.05); '
            f'border-left:3px solid {color}; border-radius:4px; font-size:0.85rem; color:#cbd5e1;">'
            f'{r}</div>'
            for r in decision.key_reasons
        )
        reasons_html = f'<div style="margin-top:14px;">{bullets}</div>'

    # Confidence + score footer
    confidence_color = {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#94a3b8"}.get(decision.confidence, "#94a3b8")

    st.markdown(f"""
    <div style="background:{color}18; border:2px solid {color}; border-radius:14px;
                padding:22px 26px; margin-bottom:20px;">

        {bonus_html}

        <div style="display:flex; justify-content:space-between; align-items:flex-start;
                    flex-wrap:wrap; gap:12px;">
            <div style="flex:1; min-width:220px;">
                <div style="font-size:0.72rem; color:#94a3b8; text-transform:uppercase;
                            letter-spacing:0.1em; margin-bottom:4px;">Today's Action</div>
                <div style="font-size:2.2rem; font-weight:900; color:{color}; line-height:1.1;
                            letter-spacing:-0.02em;">
                    {decision.recommendation}
                </div>
            </div>
            <div style="text-align:right; padding-top:4px;">
                <div style="font-size:1.4rem; font-weight:700; color:#f1f5f9;">
                    {decision.hedge_ratio}% of receivables
                </div>
                <div style="font-size:0.82rem; color:#94a3b8; margin-top:4px;">
                    Confidence: <span style="color:{confidence_color}; font-weight:700;">{decision.confidence}</span>
                    &nbsp;·&nbsp; Signal score: <span style="color:#f1f5f9; font-weight:600;">{decision.score:+.0f}</span>
                </div>
            </div>
        </div>

        {reasons_html}
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


def _stat_card(label: str, value: str, sub: str = "", sub_color: str = "#94a3b8") -> str:
    return f"""
    <div style="background:#1e293b;border:1px solid #334155;border-radius:10px;
                padding:14px 16px;height:100%;box-sizing:border-box;">
        <div style="font-size:0.72rem;color:#94a3b8;text-transform:uppercase;
                    letter-spacing:0.07em;margin-bottom:4px;">{label}</div>
        <div style="font-size:1.55rem;font-weight:700;color:#f1f5f9;line-height:1.2;">{value}</div>
        {f'<div style="font-size:0.75rem;color:{sub_color};margin-top:4px;">{sub}</div>' if sub else ''}
    </div>"""


def render_technical_summary(tech: TechnicalSnapshot, futures_near: Optional[float], futures_basis: Optional[float]) -> None:
    st.subheader("Spot & Technical Summary")

    rsi_d = f"{tech.rsi_daily:.1f}" if tech.rsi_daily else "N/A"
    rsi_d_color = "#ef4444" if (tech.rsi_daily or 0) > 70 else ("#22c55e" if (tech.rsi_daily or 100) < 30 else "#f59e0b")
    rsi_w = f"{tech.rsi_weekly:.1f}" if tech.rsi_weekly else "N/A"
    atr_sub = f"90d avg: {tech.atr_90d_avg:.4f}" if tech.atr_90d_avg else ""
    atr_color = "#ef4444" if tech.atr_elevated else "#94a3b8"

    sma50_sub = f"{tech.pct_above_sma50:+.2f}% vs spot" if tech.pct_above_sma50 is not None else ""
    sma200_sub = f"{tech.pct_above_sma200:+.2f}% vs spot" if tech.pct_above_sma200 is not None else ""
    bb_pct = f"{tech.bb_pct_b*100:.1f}%" if tech.bb_pct_b is not None else "N/A"
    bb_color = "#ef4444" if (tech.bb_pct_b or 0) > 0.85 else ("#22c55e" if (tech.bb_pct_b or 1) < 0.15 else "#94a3b8")
    near_val = f"{futures_near:.4f}" if futures_near else "N/A"
    basis_sub = f"Basis vs spot: {futures_basis:+.4f}" if futures_basis else ""

    row1 = st.columns(4)
    row1[0].markdown(_stat_card("USD/INR Spot", f"{tech.spot:.4f}"), unsafe_allow_html=True)
    row1[1].markdown(_stat_card("RSI (14 Daily)", rsi_d, sub_color=rsi_d_color), unsafe_allow_html=True)
    row1[2].markdown(_stat_card("RSI (14 Weekly)", rsi_w), unsafe_allow_html=True)
    row1[3].markdown(_stat_card("ATR (14)", f"{tech.atr_14:.4f}" if tech.atr_14 else "N/A", atr_sub, atr_color), unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    row2 = st.columns(4)
    row2[0].markdown(_stat_card("SMA 50", f"{tech.sma_50:.4f}" if tech.sma_50 else "N/A", sma50_sub), unsafe_allow_html=True)
    row2[1].markdown(_stat_card("SMA 200", f"{tech.sma_200:.4f}" if tech.sma_200 else "N/A", sma200_sub), unsafe_allow_html=True)
    row2[2].markdown(_stat_card("BB %B", bb_pct, sub_color=bb_color), unsafe_allow_html=True)
    row2[3].markdown(_stat_card("Futures (Near)", near_val, basis_sub), unsafe_allow_html=True)


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
