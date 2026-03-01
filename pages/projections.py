import streamlit as st
import plotly.graph_objects as go
import numpy as np
from simulation.monte_carlo import (
    run_simulation,
    compute_percentiles,
    probability_of_target,
    summary_statistics,
)
from simulation.scenarios import SCENARIOS
from data.portfolio import get_portfolio_summary
from utils.formatting import fmt_currency


def _build_fan_chart(percentile_data: dict, n_months: int) -> go.Figure:
    """Build a fan chart showing percentile bands."""
    x = list(range(n_months + 1))
    # Convert month index to year labels
    x_years = [m / 12 for m in x]

    fig = go.Figure()

    bands = [
        (5, 95, "rgba(99, 110, 250, 0.08)", "5th-95th percentile"),
        (10, 90, "rgba(99, 110, 250, 0.12)", "10th-90th percentile"),
        (25, 75, "rgba(99, 110, 250, 0.22)", "25th-75th percentile"),
    ]

    for low, high, color, name in bands:
        fig.add_trace(
            go.Scatter(
                x=x_years + x_years[::-1],
                y=list(percentile_data[high]) + list(percentile_data[low])[::-1],
                fill="toself",
                fillcolor=color,
                line=dict(color="rgba(255,255,255,0)"),
                name=name,
                hoverinfo="skip",
            )
        )

    # Median line
    fig.add_trace(
        go.Scatter(
            x=x_years,
            y=list(percentile_data[50]),
            line=dict(color="rgb(99, 110, 250)", width=2.5),
            name="Median (50th percentile)",
            hovertemplate="Year %{x:.1f}: $%{y:,.0f}<extra>Median</extra>",
        )
    )

    fig.update_layout(
        height=500,
        margin=dict(t=30, b=30),
        xaxis_title="Years from Now",
        yaxis_title="Portfolio Value ($)",
        yaxis_tickprefix="$",
        yaxis_tickformat=",",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def run():
    st.title("Investment Projections")
    st.caption("Monte Carlo simulation using Geometric Brownian Motion")

    # --- Current portfolio value ---
    summary = get_portfolio_summary(st.session_state["user_id"])
    current_value = summary["market_value"].sum() if not summary.empty else 0.0

    # --- Configuration ---
    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.subheader("Configuration")

        initial = st.number_input(
            "Starting Value ($)",
            value=round(current_value, 2),
            min_value=0.0,
            step=1000.0,
            format="%.2f",
            help="Defaults to your current portfolio value",
        )

        years = st.slider("Time Horizon (Years)", min_value=1, max_value=40, value=10)

        # --- Contribution Schedule ---
        st.markdown("**Monthly Contributions**")

        if "contribution_phases" not in st.session_state:
            st.session_state["contribution_phases"] = [{"years": years, "monthly": 500.0}]

        phases = st.session_state["contribution_phases"]

        phases_to_remove = None
        for i, phase in enumerate(phases):
            c_yr, c_amt, c_del = st.columns([1, 1.3, 0.4])
            with c_yr:
                phase["years"] = st.number_input(
                    "Years", value=phase["years"], min_value=1, max_value=40,
                    step=1, key=f"phase_yr_{i}",
                    label_visibility="collapsed" if i > 0 else "visible",
                )
            with c_amt:
                phase["monthly"] = st.number_input(
                    "$/month", value=phase["monthly"], min_value=0.0,
                    step=100.0, format="%.0f", key=f"phase_amt_{i}",
                    label_visibility="collapsed" if i > 0 else "visible",
                )
            with c_del:
                if i == 0:
                    st.markdown("<div style='height:29px'></div>", unsafe_allow_html=True)
                if len(phases) > 1:
                    if st.button("✕", key=f"phase_del_{i}", use_container_width=True):
                        phases_to_remove = i

        if phases_to_remove is not None:
            phases.pop(phases_to_remove)
            st.rerun()

        if st.button("＋ Add Phase", use_container_width=True):
            total_used = sum(p["years"] for p in phases)
            remaining = max(1, years - total_used)
            phases.append({"years": remaining, "monthly": 500.0})
            st.rerun()

        total_phase_years = sum(p["years"] for p in phases)
        if total_phase_years != years:
            st.warning(f"Phases cover {total_phase_years}y but horizon is {years}y. Adjust to match.")

        n_sims = st.select_slider(
            "Simulations",
            options=[100, 500, 1000, 5000, 10000],
            value=1000,
        )

        st.divider()

        scenario = st.radio(
            "Growth Scenario",
            list(SCENARIOS.keys()) + ["Custom"],
            index=1,
        )

        if scenario == "Custom":
            annual_ret = st.number_input(
                "Annual Return (%)", value=7.0, step=0.5, format="%.1f"
            ) / 100
            annual_vol = st.number_input(
                "Annual Volatility (%)", value=18.0, step=0.5, format="%.1f"
            ) / 100
        else:
            s = SCENARIOS[scenario]
            st.caption(s["description"])
            annual_ret = s["annual_return"]
            annual_vol = s["annual_volatility"]

        st.divider()

        target = st.number_input(
            "Target Amount ($, optional)",
            value=0.0,
            min_value=0.0,
            step=10000.0,
            format="%.0f",
            help="Set a goal to see the probability of reaching it",
        )

        run_btn = st.button("Run Simulation", type="primary", use_container_width=True)

    # --- Results ---
    with col_right:
        if run_btn or st.session_state.get("mc_ran"):
            if run_btn:
                # Build monthly contribution array from phases
                contrib_list = []
                for phase in phases:
                    contrib_list.extend([phase["monthly"]] * (phase["years"] * 12))
                # Trim or pad to match time horizon
                n_months_target = years * 12
                if len(contrib_list) >= n_months_target:
                    contrib_list = contrib_list[:n_months_target]
                else:
                    contrib_list.extend([0.0] * (n_months_target - len(contrib_list)))
                contrib_array = np.array(contrib_list)

                paths = run_simulation(
                    initial_value=initial,
                    monthly_contribution=contrib_array,
                    years=years,
                    annual_return=annual_ret,
                    annual_volatility=annual_vol,
                    n_simulations=n_sims,
                    seed=None,
                )
                st.session_state["mc_paths"] = paths
                st.session_state["mc_ran"] = True
                st.session_state["mc_years"] = years
                st.session_state["mc_total_contributed"] = initial + float(contrib_array.sum())

            paths = st.session_state.get("mc_paths")
            if paths is None:
                st.info("Click 'Run Simulation' to generate projections.")
                return

            years_used = st.session_state.get("mc_years", years)
            n_months = years_used * 12

            # Fan chart
            pct_data = compute_percentiles(paths)
            fig = _build_fan_chart(pct_data, n_months)
            st.plotly_chart(fig, use_container_width=True)

            # Summary stats
            stats = summary_statistics(paths)
            total_contributed = st.session_state.get("mc_total_contributed", initial)

            st.subheader("Summary")

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Contributed", fmt_currency(total_contributed))
            c2.metric("Median Outcome", fmt_currency(stats["median"]))
            c3.metric("Expected (Mean)", fmt_currency(stats["mean"]))

            st.divider()

            # Percentile table
            st.write("**Outcome Distribution (Final Value)**")
            pcols = st.columns(5)
            pcols[0].metric("Pessimistic (10th)", fmt_currency(stats["p10"]))
            pcols[1].metric("Conservative (25th)", fmt_currency(stats["p25"]))
            pcols[2].metric("Median (50th)", fmt_currency(stats["median"]))
            pcols[3].metric("Optimistic (75th)", fmt_currency(stats["p75"]))
            pcols[4].metric("Best Case (90th)", fmt_currency(stats["p90"]))

            # Target probability
            if target > 0:
                st.divider()
                prob = probability_of_target(paths, target)
                st.metric(
                    f"Probability of Reaching {fmt_currency(target)}",
                    f"{prob * 100:.1f}%",
                )
                if prob >= 0.8:
                    st.success("High likelihood of reaching your target.")
                elif prob >= 0.5:
                    st.info("Moderate likelihood. Consider increasing contributions or time horizon.")
                else:
                    st.warning("Low likelihood. You may need higher contributions or a longer horizon.")
        else:
            st.info("Configure your simulation on the left and click **Run Simulation**.")


run()
