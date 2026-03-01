import streamlit as st
import plotly.express as px
import numpy as np
from analysis.registry import register
from data.portfolio import get_portfolio_daily_returns


@register("Returns Distribution", description="Distribution of daily/weekly portfolio returns", order=50)
def render():
    freq = st.radio("Frequency", ["Daily", "Weekly"], horizontal=True, key="returns_freq")

    returns = get_portfolio_daily_returns(period="1y")
    if returns.empty:
        st.info("Not enough data to display returns.")
        return

    if freq == "Weekly":
        returns = returns.resample("W").apply(lambda x: (1 + x).prod() - 1).dropna()

    returns_pct = returns * 100

    fig = px.histogram(
        returns_pct,
        nbins=50,
        labels={"value": f"{freq} Return (%)", "count": "Frequency"},
        color_discrete_sequence=["#636EFA"],
        opacity=0.75,
    )
    fig.update_layout(
        margin=dict(t=20, b=20),
        height=400,
        showlegend=False,
        xaxis_ticksuffix="%",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Stats
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Mean", f"{returns_pct.mean():.2f}%")
    col2.metric("Std Dev", f"{returns_pct.std():.2f}%")
    col3.metric("Min", f"{returns_pct.min():.2f}%")
    col4.metric("Max", f"{returns_pct.max():.2f}%")
