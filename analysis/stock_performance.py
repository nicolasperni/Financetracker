import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from analysis.registry import register
from data.market_data import get_history
from db.models import get_distinct_tickers


@register("Individual Stock Performance", description="Normalized return comparison across holdings", order=30)
def render():
    tickers = get_distinct_tickers(st.session_state["user_id"])
    if not tickers:
        st.info("No stocks in portfolio yet.")
        return

    period = st.selectbox(
        "Period",
        ["1mo", "3mo", "6mo", "1y", "2y", "5y"],
        index=3,
        key="stock_perf_period",
    )

    fig = go.Figure()
    colors = [
        "#636EFA", "#EF553B", "#00CC96", "#AB63FA",
        "#FFA15A", "#19D3F3", "#FF6692", "#B6E880",
    ]

    for i, ticker in enumerate(tickers):
        try:
            hist = get_history(ticker, period=period)
            if hist.empty:
                continue
            # Normalize to percentage return from start
            normalized = (hist["Close"] / hist["Close"].iloc[0] - 1) * 100
            fig.add_trace(
                go.Scatter(
                    x=normalized.index,
                    y=normalized.values,
                    name=ticker,
                    line=dict(color=colors[i % len(colors)], width=2),
                    hovertemplate=f"{ticker}: %{{y:+.1f}}%<extra></extra>",
                )
            )
        except Exception:
            continue

    fig.update_layout(
        margin=dict(t=20, b=20),
        height=400,
        yaxis_title="Return (%)",
        yaxis_ticksuffix="%",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)
