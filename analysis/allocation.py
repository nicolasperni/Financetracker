import streamlit as st
import plotly.express as px
from analysis.registry import register
from data.portfolio import get_portfolio_summary


@register("Portfolio Allocation", description="Current allocation by market value", order=10)
def render():
    summary = get_portfolio_summary(st.session_state["user_id"])
    if summary.empty:
        st.info("No holdings to display. Add some transactions first.")
        return

    fig = px.pie(
        summary,
        values="market_value",
        names="ticker",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=400)
    st.plotly_chart(fig, use_container_width=True)
