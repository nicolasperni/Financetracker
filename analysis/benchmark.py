import streamlit as st
import plotly.graph_objects as go
from analysis.registry import register
from data.portfolio import get_time_weighted_return
from data.market_data import get_history


@register("Portfolio vs S&P 500", description="Time-weighted return compared to the S&P 500 benchmark", order=40)
def render():
    period = st.selectbox(
        "Period",
        ["3mo", "6mo", "1y", "2y", "5y"],
        index=2,
        key="benchmark_period",
    )

    twr = get_time_weighted_return(period=period)
    if twr.empty:
        st.info("No portfolio history available yet.")
        return

    try:
        sp500 = get_history("^GSPC", period=period)
    except Exception:
        st.warning("Could not fetch S&P 500 data.")
        return

    if sp500.empty:
        st.warning("No S&P 500 data available.")
        return

    # Align S&P 500 to start at the same date as the portfolio
    portfolio_start = twr.index[0]
    sp_trimmed = sp500["Close"][sp500.index >= portfolio_start]
    if sp_trimmed.empty:
        st.warning("No S&P 500 data available for your portfolio period.")
        return
    sp_norm = (sp_trimmed / sp_trimmed.iloc[0] - 1) * 100

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=twr.index,
            y=twr.values,
            name="Your Portfolio (TWR)",
            line=dict(color="#636EFA", width=2),
            hovertemplate="%{y:+.1f}%<extra>Portfolio</extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=sp_norm.index,
            y=sp_norm.values,
            name="S&P 500",
            line=dict(color="#EF553B", width=2, dash="dash"),
            hovertemplate="%{y:+.1f}%<extra>S&P 500</extra>",
        )
    )

    fig.update_layout(
        margin=dict(t=20, b=20),
        height=400,
        yaxis_title="Return (%)",
        yaxis_ticksuffix="%",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Uses **Time-Weighted Return (TWR)** — deposits and withdrawals are excluded "
        "so this measures pure investment performance, comparable to the S&P 500."
    )
