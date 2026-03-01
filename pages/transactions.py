import streamlit as st
import pandas as pd
import pytz
from datetime import date, datetime, time
from db.models import (
    add_transaction,
    get_transactions,
    get_transaction_by_id,
    update_transaction,
    delete_transaction,
)
from data.market_data import validate_ticker, get_price_on_date
from utils.validators import validate_ticker_format

# Timezone options: label -> pytz name
TIMEZONES = {
    "EST (Eastern)": "US/Eastern",
    "CST (Central)": "US/Central",
    "MST (Mountain)": "US/Mountain",
    "PST (Pacific)": "US/Pacific",
    "ART (Argentina)": "America/Argentina/Buenos_Aires",
    "UTC": "UTC",
}


def _to_est_hour(local_time: time, tz_label: str) -> float:
    """Convert a local time + timezone to a fractional hour in EST."""
    tz_name = TIMEZONES[tz_label]
    local_tz = pytz.timezone(tz_name)
    est = pytz.timezone("US/Eastern")
    # Use a reference date to do the conversion
    ref = datetime(2025, 6, 15, local_time.hour, local_time.minute)
    local_dt = local_tz.localize(ref)
    est_dt = local_dt.astimezone(est)
    return est_dt.hour + est_dt.minute / 60


def run():
    user_id = st.session_state["user_id"]
    st.title("Transactions")

    # --- Add Transaction Form ---
    st.subheader("Add Transaction")

    input_mode = st.radio(
        "Input method",
        ["Dollar Amount", "Number of Shares"],
        horizontal=True,
        key="add_input_mode",
    )

    with st.form("add_txn", clear_on_submit=True):
        col1, col2, col3 = st.columns([2, 1, 2])
        ticker = col1.text_input("Ticker", placeholder="e.g. AAPL").strip().upper()
        txn_type = col2.selectbox("Type", ["BUY", "SELL"])
        txn_date = col3.date_input("Date", value=date.today(), max_value=date.today())

        col4, col5, col6 = st.columns([1, 1, 2])
        txn_time = col4.time_input("Time", value=time(12, 0))
        tz_label = col5.selectbox("Timezone", list(TIMEZONES.keys()), index=0)

        if input_mode == "Dollar Amount":
            amount = col6.number_input(
                "Amount ($)",
                min_value=0.01,
                step=100.0,
                format="%.2f",
                help="Dollar amount invested. Shares will be calculated from the price at the specified date/time.",
            )
            num_shares = None
        else:
            num_shares = col6.number_input(
                "Shares",
                min_value=0.0001,
                step=1.0,
                format="%.4f",
                help="Number of shares purchased. Total cost will be calculated from the price at the specified date/time.",
            )
            amount = None

        notes = st.text_input("Notes (optional)", placeholder="e.g. Quarterly DCA")

        submitted = st.form_submit_button("Add Transaction", type="primary", use_container_width=True)

        if submitted:
            try:
                ticker = validate_ticker_format(ticker)
            except ValueError as e:
                st.error(str(e))
                st.stop()

            if not validate_ticker(ticker):
                st.error(f"Could not find ticker '{ticker}'. Please check the symbol.")
                st.stop()

            # Look up the price on the transaction date/time (converted to EST)
            hour_est = _to_est_hour(txn_time, tz_label)
            price = get_price_on_date(ticker, txn_date.isoformat(), hour=hour_est)
            if price is None or price <= 0:
                st.error(
                    f"Could not find a price for {ticker} on {txn_date.isoformat()}. "
                    "Try a different date."
                )
                st.stop()

            if input_mode == "Dollar Amount":
                shares = amount / price
                total = amount
            else:
                shares = num_shares
                total = shares * price

            try:
                txn_id = add_transaction(
                    user_id=user_id,
                    ticker=ticker,
                    txn_type=txn_type,
                    shares=shares,
                    price=price,
                    date=txn_date.isoformat(),
                    notes=notes,
                )
                st.success(
                    f"Added {txn_type} of {shares:.4f} shares of {ticker} "
                    f"at ${price:.2f}/share (${total:,.2f} total)"
                )
                st.rerun()
            except ValueError as e:
                st.error(str(e))

    st.divider()

    # --- Transaction History ---
    st.subheader("Transaction History")

    txns = get_transactions(user_id)
    if txns.empty:
        st.info("No transactions yet. Add your first one above.")
        return

    # Filters
    col1, col2 = st.columns(2)
    ticker_filter = col1.selectbox(
        "Filter by ticker", ["All"] + sorted(txns["ticker"].unique().tolist())
    )
    type_filter = col2.selectbox("Filter by type", ["All", "BUY", "SELL"])

    filtered = txns.copy()
    if ticker_filter != "All":
        filtered = filtered[filtered["ticker"] == ticker_filter]
    if type_filter != "All":
        filtered = filtered[filtered["type"] == type_filter]

    # Display table
    display = filtered[["id", "date", "ticker", "type", "shares", "price", "notes"]].copy()
    display["total"] = display["shares"] * display["price"]
    display.columns = ["ID", "Date", "Ticker", "Type", "Shares", "Price/Share", "Notes", "Total"]

    st.dataframe(
        display.style.format(
            {
                "Shares": "{:.4f}",
                "Price/Share": "${:,.2f}",
                "Total": "${:,.2f}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.caption(f"Showing {len(filtered)} of {len(txns)} transactions")

    st.divider()

    # --- Edit / Delete ---
    st.subheader("Edit or Delete")

    txn_ids = filtered["id"].tolist()
    if not txn_ids:
        return

    selected_id = st.selectbox(
        "Select transaction ID",
        txn_ids,
        format_func=lambda x: (
            f"#{x} — {filtered[filtered['id']==x].iloc[0]['date']} "
            f"{filtered[filtered['id']==x].iloc[0]['type']} "
            f"${filtered[filtered['id']==x].iloc[0]['shares'] * filtered[filtered['id']==x].iloc[0]['price']:,.2f} "
            f"of {filtered[filtered['id']==x].iloc[0]['ticker']}"
        ),
    )

    col_edit, col_delete = st.columns(2)

    with col_edit:
        if st.button("Edit", use_container_width=True):
            st.session_state["editing_id"] = selected_id

    with col_delete:
        if st.button("Delete", type="secondary", use_container_width=True):
            st.session_state["deleting_id"] = selected_id

    # Edit form
    if st.session_state.get("editing_id") == selected_id:
        txn = get_transaction_by_id(selected_id, user_id)
        if txn:
            st.write("---")
            st.write(f"**Editing transaction #{selected_id}**")

            edit_mode = st.radio(
                "Input method",
                ["Dollar Amount", "Number of Shares"],
                horizontal=True,
                key="edit_input_mode",
            )

            with st.form("edit_txn"):
                col1, col2, col3 = st.columns([2, 1, 2])
                new_ticker = col1.text_input("Ticker", value=txn["ticker"]).strip().upper()
                new_type = col2.selectbox("Type", ["BUY", "SELL"], index=0 if txn["type"] == "BUY" else 1)
                new_date = col3.date_input("Date", value=datetime.strptime(txn["date"], "%Y-%m-%d").date())

                col4, col5, col6 = st.columns([1, 1, 2])
                new_time = col4.time_input("Time", value=time(12, 0))
                new_tz_label = col5.selectbox("Timezone", list(TIMEZONES.keys()), index=0, key="edit_tz")

                current_total = txn["shares"] * txn["price"]
                if edit_mode == "Dollar Amount":
                    new_amount = col6.number_input(
                        "Amount ($)", value=round(current_total, 2), min_value=0.01, format="%.2f"
                    )
                    new_num_shares = None
                else:
                    new_num_shares = col6.number_input(
                        "Shares", value=round(txn["shares"], 4), min_value=0.0001, format="%.4f"
                    )
                    new_amount = None

                new_notes = st.text_input("Notes", value=txn["notes"] or "")

                if st.form_submit_button("Save Changes", type="primary"):
                    try:
                        new_ticker = validate_ticker_format(new_ticker)
                    except ValueError as e:
                        st.error(str(e))
                        st.stop()

                    # Look up price on the (possibly new) date/time
                    new_hour_est = _to_est_hour(new_time, new_tz_label)
                    new_price = get_price_on_date(new_ticker, new_date.isoformat(), hour=new_hour_est)
                    if new_price is None or new_price <= 0:
                        st.error(f"Could not find a price for {new_ticker} on {new_date.isoformat()}.")
                        st.stop()

                    if edit_mode == "Dollar Amount":
                        new_shares = new_amount / new_price
                    else:
                        new_shares = new_num_shares

                    try:
                        update_transaction(
                            selected_id,
                            user_id,
                            ticker=new_ticker,
                            type=new_type,
                            shares=new_shares,
                            price=new_price,
                            date=new_date.isoformat(),
                            notes=new_notes,
                        )
                        st.success("Transaction updated.")
                        st.session_state.pop("editing_id", None)
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))

    # Delete confirmation
    if st.session_state.get("deleting_id") == selected_id:
        st.warning(f"Are you sure you want to delete transaction #{selected_id}?")
        col1, col2 = st.columns(2)
        if col1.button("Confirm Delete", type="primary"):
            try:
                delete_transaction(selected_id, user_id)
                st.success("Transaction deleted.")
                st.session_state.pop("deleting_id", None)
                st.rerun()
            except ValueError as e:
                st.error(str(e))
        if col2.button("Cancel"):
            st.session_state.pop("deleting_id", None)
            st.rerun()


run()
