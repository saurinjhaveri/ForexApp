from typing import List, Optional
import streamlit as st
import pandas as pd
from analysis.decision_engine import Decision
from analysis.technicals import TechnicalSnapshot
from analysis.levels import KeyLevel
from data.price_fetcher import PriceData
from data.macro_scraper import MacroData
from data.rbi_scraper import RBIData
from data.news_fetcher import NewsItem


_REGIME_STYLE = {
    "mean_reversion": ("#fef3c7", "#92400e", "↩ Mean-Reversion Regime"),
    "trend":          ("#dbeafe", "#1e40af", "→ Trend Regime"),
    "neutral":        ("#1e293b", "#94a3b8", "◈ Neutral Regime"),
}


def render_decision_box(decision: Decision, spot: Optional[float], budget_rate: Optional[float] = None) -> None:
    color = decision.color
    confidence_color = {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#94a3b8"}.get(decision.confidence, "#94a3b8")

    # ── Regime badge ──────────────────────────────────────────────────────────────
    reg_bg, reg_fg, reg_label = _REGIME_STYLE.get(decision.regime, _REGIME_STYLE["neutral"])
    st.markdown(
        f"<div style='display:inline-block; padding:3px 10px; background:{reg_bg}; "
        f"color:{reg_fg}; border-radius:12px; font-size:0.72rem; font-weight:700; "
        f"letter-spacing:0.06em; margin-bottom:10px;'>{reg_label}</div>",
        unsafe_allow_html=True,
    )

    # ── Top bar: action + quantity ────────────────────────────────────────────────
    left, right = st.columns([3, 1])
    with left:
        st.markdown(
            f"<div style='font-size:0.72rem; color:#94a3b8; text-transform:uppercase; "
            f"letter-spacing:0.1em; margin-bottom:2px;'>TODAY'S ACTION</div>"
            f"<div style='font-size:2.6rem; font-weight:900; color:{color}; line-height:1.1;'>"
            f"{decision.recommendation}</div>",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            f"<div style='text-align:right; padding-top:6px;'>"
            f"<div style='font-size:1.3rem; font-weight:700; color:#f1f5f9;'>{decision.hedge_ratio}% of receivables</div>"
            f"<div style='font-size:0.8rem; color:#94a3b8; margin-top:4px;'>"
            f"Confidence: <span style='color:{confidence_color}; font-weight:700;'>{decision.confidence}</span>"
            f"&nbsp;·&nbsp;Score: <span style='color:#f1f5f9;'>{decision.score:+.0f}</span></div>"
            f"<div style='font-size:0.8rem; color:#94a3b8; margin-top:2px;'>"
            f"Spot: <span style='color:#f1f5f9; font-weight:600;'>₹{spot:.4f}</span></div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── Key reasons ───────────────────────────────────────────────────────────────
    if decision.key_reasons:
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        for reason in decision.key_reasons:
            st.markdown(
                f"<div style='padding:9px 14px; background:rgba(255,255,255,0.04); "
                f"border-left:3px solid {color}; border-radius:5px; "
                f"font-size:0.88rem; color:#cbd5e1; margin-bottom:6px;'>"
                f"▸ {reason}</div>",
                unsafe_allow_html=True,
            )

    # ── Tranche trigger ───────────────────────────────────────────────────────────
    if decision.tranche_trigger:
        st.markdown(
            f"<div style='margin-top:10px; padding:8px 14px; background:rgba(99,102,241,0.08); "
            f"border-left:3px solid #6366f1; border-radius:5px; "
            f"font-size:0.82rem; color:#a5b4fc;'>"
            f"⟳ Next tranche: {decision.tranche_trigger}</div>",
            unsafe_allow_html=True,
        )


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


def render_technical_summary(
    tech: TechnicalSnapshot,
    futures_near: Optional[float],
    futures_basis: Optional[float],
    futures_oi: Optional[float] = None,
    futures_oi_change: Optional[float] = None,
    oi_pct_above_avg: Optional[float] = None,
    annualized_premium: Optional[float] = None,
    forward_premium_pctile: Optional[float] = None,
    inr_em_divergence: Optional[float] = None,
    em_basket_5d: Optional[float] = None,
) -> None:
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

    # OI row — only render if we have data
    if futures_oi:
        oi_change_str = f"{futures_oi_change:+,.0f} contracts today" if futures_oi_change is not None else ""
        oi_color = "#94a3b8"
        if futures_oi_change is not None:
            oi_color = "#ef4444" if futures_oi_change > 0 else "#22c55e"
        avg_str = f"{oi_pct_above_avg:+.0f}% vs 20d avg" if oi_pct_above_avg is not None else ""
        avg_color = "#ef4444" if (oi_pct_above_avg or 0) > 15 else "#94a3b8"

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        row3 = st.columns(4)
        row3[0].markdown(_stat_card("Near-Month OI", f"{futures_oi:,.0f}", oi_change_str, oi_color), unsafe_allow_html=True)
        row3[1].markdown(_stat_card("OI vs 20d Avg", avg_str if avg_str else "N/A", sub_color=avg_color), unsafe_allow_html=True)
        oi_signal = "Longs Building 🔴" if (futures_oi_change or 0) > 0 else ("Covering 🟡" if (futures_oi_change or 0) < 0 else "—")
        row3[2].markdown(_stat_card("OI Signal", oi_signal), unsafe_allow_html=True)
        row3[3].markdown(_stat_card("OI Crowded?", "YES 🔴" if (oi_pct_above_avg or 0) > 15 else "No 🟢"), unsafe_allow_html=True)

    # ── EM divergence + forward premium row ───────────────────────────────────────
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    row4 = st.columns(4)

    # EM divergence card
    if inr_em_divergence is not None:
        em_sign = "+" if inr_em_divergence > 0 else ""
        em_color = "#ef4444" if inr_em_divergence > 0.5 else ("#22c55e" if inr_em_divergence < -0.5 else "#94a3b8")
        em_label = "India-specific 🔴" if inr_em_divergence > 0.5 else ("Global USD 🟡" if inr_em_divergence < -0.5 else "In-line with EM")
        em_sub = f"EM basket 5d: {em_basket_5d:+.2f}%" if em_basket_5d is not None else ""
        row4[0].markdown(_stat_card("INR vs EM Basket", f"{em_sign}{inr_em_divergence:.2f}%", f"{em_sub} · {em_label}", em_color), unsafe_allow_html=True)
    else:
        row4[0].markdown(_stat_card("INR vs EM Basket", "N/A", "BRL/ZAR/IDR basket"), unsafe_allow_html=True)

    # Forward premium card
    if annualized_premium is not None:
        pctile_str = f"{forward_premium_pctile:.0f}th pctile (90d)" if forward_premium_pctile is not None else ""
        prem_color = "#ef4444" if (forward_premium_pctile or 0) >= 90 else ("#f59e0b" if (forward_premium_pctile or 0) >= 75 else ("#22c55e" if (forward_premium_pctile or 0) <= 25 else "#94a3b8"))
        row4[1].markdown(_stat_card("Fwd Premium (Ann.)", f"{annualized_premium:.1f}%", pctile_str, prem_color), unsafe_allow_html=True)
    else:
        row4[1].markdown(_stat_card("Fwd Premium (Ann.)", "N/A", "Requires futures data"), unsafe_allow_html=True)

    row4[2].markdown("", unsafe_allow_html=True)
    row4[3].markdown("", unsafe_allow_html=True)


def render_key_levels_table(tech: TechnicalSnapshot, levels: List[KeyLevel]) -> None:
    st.subheader("Key Levels")
    spot = tech.spot
    rows = []
    source_label = {
        "weekly_pivot":  "Weekly Pivot",
        "monthly_pivot": "Monthly Pivot",
        "swing":         "Swing",
        "round_number":  "Round Number",
        "200dma":        "200 DMA",
    }
    strength_label = {1: "·", 2: "··", 3: "···"}
    for lvl in levels:
        dist_pct = (spot - lvl.price) / lvl.price * 100
        if abs(dist_pct) < 0.35:
            traffic = "🔴"
        elif abs(dist_pct) < 1.5:
            traffic = "🟡"
        else:
            traffic = "🟢"
        direction = "▲ Above" if dist_pct > 0 else "▼ Below"
        rows.append({
            "": traffic,
            "Level": lvl.name,
            "Price": f"{lvl.price:.4f}",
            "Type": lvl.level_type.capitalize(),
            "Source": source_label.get(lvl.source, lvl.source),
            "Strength": strength_label.get(lvl.strength, "·"),
            "Distance": f"{dist_pct:+.2f}%",
            "Position": direction,
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No key levels computed yet.")


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


def render_scenario_table(
    monthly_receivable_usd: float,
    hedge_ratio: int,
    spot: float,
    bear_pct: float = 3.0,
    bull_pct: float = 1.5,
    forward_rate: Optional[float] = None,
) -> None:
    """
    Asymmetric P&L scenario table.
    Bear = INR strengthens (bad for exporter's unhedged portion).
    Bull = INR weakens (good for unhedged, but historically capped by RBI).
    Hedged portion always locks in forward_rate (or spot if unavailable).
    """
    lock_rate    = forward_rate or spot
    hedged_usd   = monthly_receivable_usd * hedge_ratio / 100
    unhedged_usd = monthly_receivable_usd - hedged_usd
    hedged_inr   = hedged_usd * lock_rate

    scenarios = [
        ("🐻 Bear (INR strengthens)", spot * (1 - bear_pct / 100), "#22c55e"),
        ("◈ Base (no change)",        spot,                         "#94a3b8"),
        ("🐂 Bull (INR weakens)",     spot * (1 + bull_pct / 100),  "#ef4444"),
    ]

    base_total = hedged_inr + unhedged_usd * spot
    rows = []
    for label, rate, _ in scenarios:
        total_inr  = hedged_inr + unhedged_usd * rate
        vs_base    = total_inr - base_total
        vs_base_pct = vs_base / base_total * 100 if base_total else 0
        rows.append({
            "Scenario":          label,
            "USD/INR Rate":      f"{rate:.4f}",
            "INR Received (₹)":  f"₹{total_inr:,.0f}",
            "vs Base (₹)":       f"{'+' if vs_base >= 0 else ''}{vs_base:,.0f}",
            "vs Base (%)":       f"{'+' if vs_base_pct >= 0 else ''}{vs_base_pct:.1f}%",
        })

    st.subheader("Exposure & Scenario Analysis")
    lock_note = f"Hedged {hedge_ratio}% at ₹{lock_rate:.4f} forward · Unhedged: USD {unhedged_usd:,.0f} open"
    st.caption(lock_note)
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


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
