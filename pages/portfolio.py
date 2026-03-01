import streamlit as st
import pandas as pd
from data.portfolio import get_portfolio_summary
from data.holdings import compute_holdings
from utils.formatting import fmt_currency, fmt_pct


def run():
    st.title("Portfolio Overview")

    summary = get_portfolio_summary(st.session_state["user_id"])

    if summary.empty:
        st.info(
            "Your portfolio is empty. Head over to **Transactions** to add your first stock purchase."
        )
        return

    # --- Header metrics ---
    total_value = summary["market_value"].sum()
    total_invested = summary["total_invested"].sum()
    total_gain = total_value - total_invested
    total_gain_pct = total_gain / total_invested if total_invested > 0 else 0
    daily_change = summary["daily_change"].sum()

    col1, col2, col3 = st.columns(3)
    daily_delta = f"-${abs(daily_change):,.2f} today" if daily_change < 0 else f"${daily_change:,.2f} today"
    col1.metric("Total Value", fmt_currency(total_value), delta=daily_delta)
    col2.metric("Total Invested", fmt_currency(total_invested))
    col3.metric(
        "Unrealized Gain/Loss",
        fmt_currency(total_gain),
        delta=fmt_pct(total_gain_pct * 100),
    )

    st.divider()

    # --- Holdings table ---
    st.subheader("Holdings")

    display_df = summary[
        [
            "ticker",
            "name",
            "total_shares",
            "avg_cost_basis",
            "current_price",
            "market_value",
            "unrealized_gain",
            "unrealized_gain_pct",
            "daily_change_pct",
            "weight",
        ]
    ].copy()

    display_df.columns = [
        "Ticker",
        "Name",
        "Shares",
        "Avg Cost",
        "Price",
        "Market Value",
        "Gain/Loss ($)",
        "Gain/Loss (%)",
        "Day Change (%)",
        "Weight",
    ]

    st.dataframe(
        display_df.style.format(
            {
                "Shares": "{:.4f}",
                "Avg Cost": "${:,.2f}",
                "Price": "${:,.2f}",
                "Market Value": "${:,.2f}",
                "Gain/Loss ($)": "${:+,.2f}",
                "Gain/Loss (%)": "{:+.2f}%",
                "Day Change (%)": "{:+.2f}%",
                "Weight": "{:.1%}",
            }
        ).map(
            lambda v: "color: #00cc66" if isinstance(v, (int, float)) and v > 0 else (
                "color: #ff4444" if isinstance(v, (int, float)) and v < 0 else ""
            ),
            subset=["Gain/Loss ($)", "Gain/Loss (%)", "Day Change (%)"],
        ),
        use_container_width=True,
        hide_index=True,
    )

    # --- Quick highlights ---
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        best = summary.loc[summary["daily_change_pct"].idxmax()]
        st.metric(
            f"Top Gainer Today: {best['ticker']}",
            fmt_currency(best["current_price"]),
            delta=fmt_pct(best["daily_change_pct"] * 100),
        )
    with col2:
        worst = summary.loc[summary["daily_change_pct"].idxmin()]
        st.metric(
            f"Top Loser Today: {worst['ticker']}",
            fmt_currency(worst["current_price"]),
            delta=fmt_pct(worst["daily_change_pct"] * 100),
        )


run()
