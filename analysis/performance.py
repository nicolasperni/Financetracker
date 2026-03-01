import streamlit as st
import plotly.express as px
from analysis.registry import register
from data.portfolio import get_portfolio_value_history


@register("Portfolio Value Over Time", description="Total portfolio value history", order=20)
def render():
    period = st.selectbox(
        "Period",
        ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
        index=3,
        key="perf_period",
    )

    history = get_portfolio_value_history(period=period)
    if history.empty:
        st.info("No portfolio history available yet.")
        return

    fig = px.area(
        history.reset_index(),
        x="Date",
        y="portfolio_value",
        labels={"portfolio_value": "Portfolio Value ($)", "Date": ""},
        color_discrete_sequence=["#636EFA"],
    )
    fig.update_layout(
        margin=dict(t=20, b=20),
        height=400,
        yaxis_tickprefix="$",
        yaxis_tickformat=",",
        hovermode="x unified",
    )
    fig.update_traces(
        hovertemplate="$%{y:,.2f}",
    )
    st.plotly_chart(fig, use_container_width=True)
