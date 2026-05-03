from __future__ import annotations

from typing import TYPE_CHECKING, List

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import TECHNICAL_PARAMS

if TYPE_CHECKING:
    from analysis.technicals import TechnicalSnapshot
    from analysis.levels import KeyLevel


def build_usdinr_chart(
    df: pd.DataFrame,
    tech: "TechnicalSnapshot",
    levels: "List[KeyLevel]",
    lookback_months: int = 6,
) -> go.Figure:
    cutoff = pd.Timestamp.now() - pd.DateOffset(months=lookback_months)
    df = df[df.index >= cutoff].copy()
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No price data available", showarrow=False)
        return fig

    p = TECHNICAL_PARAMS
    close = df["Close"]
    sma50  = close.rolling(p["sma_fast"]).mean()
    sma200 = close.rolling(p["sma_slow"]).mean()
    bb_mid = close.rolling(p["bb_period"]).mean()
    bb_std = close.rolling(p["bb_period"]).std()
    bb_upper = bb_mid + p["bb_std"] * bb_std
    bb_lower = bb_mid - p["bb_std"] * bb_std

    # RSI sub-chart
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=p["rsi_period"] - 1, min_periods=p["rsi_period"]).mean()
    avg_loss = loss.ewm(com=p["rsi_period"] - 1, min_periods=p["rsi_period"]).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.03,
    )

    # Candlesticks
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        name="USD/INR", increasing_line_color="#22c55e",
        decreasing_line_color="#ef4444",
    ), row=1, col=1)

    # Bollinger Bands
    fig.add_trace(go.Scatter(
        x=df.index, y=bb_upper, name="BB Upper",
        line=dict(color="rgba(99,102,241,0.5)", width=1, dash="dot"),
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=bb_lower, name="BB Lower",
        fill="tonexty", fillcolor="rgba(99,102,241,0.05)",
        line=dict(color="rgba(99,102,241,0.5)", width=1, dash="dot"),
    ), row=1, col=1)

    # SMAs
    fig.add_trace(go.Scatter(
        x=df.index, y=sma50, name=f"SMA {p['sma_fast']}",
        line=dict(color="#f59e0b", width=1.5),
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=sma200, name=f"SMA {p['sma_slow']}",
        line=dict(color="#8b5cf6", width=1.5),
    ), row=1, col=1)

    # Key levels (horizontal lines)
    colors = {"resistance": "#ef4444", "support": "#22c55e", "pivot": "#f59e0b"}
    for lvl in levels:
        fig.add_hline(
            y=lvl.price, line_dash="dash",
            line_color=colors.get(lvl.level_type, "#6b7280"),
            line_width=1 + lvl.strength * 0.4,
            annotation_text=f"{lvl.name} ({lvl.price:.2f})",
            annotation_position="right",
            row=1, col=1,
        )

    # RSI subplot
    fig.add_trace(go.Scatter(
        x=df.index, y=rsi, name="RSI(14)",
        line=dict(color="#06b6d4", width=1.5),
    ), row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#ef4444", row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#22c55e", row=2, col=1)

    fig.update_layout(
        height=550,
        margin=dict(l=0, r=10, t=30, b=0),
        paper_bgcolor="#0f172a",
        plot_bgcolor="#1e293b",
        font=dict(color="#cbd5e1"),
        legend=dict(orientation="h", yanchor="bottom", y=1.01),
        xaxis_rangeslider_visible=False,
    )
    fig.update_xaxes(gridcolor="#334155", showgrid=True)
    fig.update_yaxes(gridcolor="#334155", showgrid=True)
    return fig
