import pandas as pd
import streamlit as st
from data.holdings import compute_holdings
from data.market_data import get_current_price, get_history
from db.models import get_transactions


def get_portfolio_summary(user_id: int) -> pd.DataFrame:
    """Holdings enriched with live market data.

    Returns DataFrame with columns:
        ticker, name, total_shares, avg_cost_basis, total_invested,
        current_price, market_value, unrealized_gain, unrealized_gain_pct,
        daily_change, daily_change_pct, weight
    """
    holdings = compute_holdings(user_id)
    if holdings.empty:
        return holdings

    rows = []
    for _, h in holdings.iterrows():
        try:
            price_data = get_current_price(h["ticker"])
        except Exception:
            price_data = {
                "price": 0,
                "previous_close": 0,
                "change": 0,
                "change_pct": 0,
                "name": h["ticker"],
            }

        market_value = h["total_shares"] * price_data["price"]
        unrealized = market_value - h["total_invested"]
        unrealized_pct = unrealized / h["total_invested"] if h["total_invested"] > 0 else 0

        rows.append(
            {
                "ticker": h["ticker"],
                "name": price_data["name"],
                "total_shares": h["total_shares"],
                "avg_cost_basis": h["avg_cost_basis"],
                "total_invested": h["total_invested"],
                "current_price": price_data["price"],
                "market_value": market_value,
                "unrealized_gain": unrealized,
                "unrealized_gain_pct": unrealized_pct,
                "daily_change": price_data["change"] * h["total_shares"],
                "daily_change_pct": price_data["change_pct"],
                "weight": 0.0,  # computed below
            }
        )

    df = pd.DataFrame(rows)
    total_value = df["market_value"].sum()
    if total_value > 0:
        df["weight"] = df["market_value"] / total_value
    return df


def get_portfolio_value_history(user_id: int, period: str = "1y") -> pd.DataFrame:
    """Time series of total portfolio value over a period.

    Walks through transactions chronologically and applies historical prices
    to compute the daily portfolio value.
    """
    txns = get_transactions(user_id)
    if txns.empty:
        return pd.DataFrame()

    tickers = txns["ticker"].unique().tolist()

    # Fetch historical prices for all tickers
    price_frames = {}
    for t in tickers:
        try:
            hist = get_history(t, period=period)
            if not hist.empty:
                price_frames[t] = hist["Close"]
        except Exception:
            continue

    if not price_frames:
        return pd.DataFrame()

    price_df = pd.DataFrame(price_frames).sort_index()
    price_df = price_df.ffill()  # Forward-fill gaps

    # Build shares-held matrix
    shares_df = pd.DataFrame(0.0, index=price_df.index, columns=tickers)
    for _, row in txns.sort_values("date").iterrows():
        t = row["ticker"]
        if t not in shares_df.columns:
            continue
        mask = price_df.index >= pd.Timestamp(row["date"]).tz_localize(price_df.index.tz)
        delta = row["shares"] if row["type"] == "BUY" else -row["shares"]
        shares_df.loc[mask, t] += delta

    # Portfolio value = sum of (shares * price)
    value_series = (shares_df * price_df).sum(axis=1)
    result = value_series.to_frame(name="portfolio_value")
    # Only include dates where we actually held something
    result = result[result["portfolio_value"] > 0]
    return result


def _build_twr_components(user_id: int, period: str = "1y"):
    """Shared helper: build portfolio value series and daily cash flows.

    Returns (portfolio_value: Series, cashflow_series: Series) or (None, None).
    """
    txns = get_transactions(user_id)
    if txns.empty:
        return None, None

    tickers = txns["ticker"].unique().tolist()

    price_frames = {}
    for t in tickers:
        try:
            hist = get_history(t, period=period)
            if not hist.empty:
                price_frames[t] = hist["Close"]
        except Exception:
            continue

    if not price_frames:
        return None, None

    price_df = pd.DataFrame(price_frames).sort_index().ffill()

    # Build shares-held matrix and daily cash flow series
    shares_df = pd.DataFrame(0.0, index=price_df.index, columns=tickers)
    cashflow_series = pd.Series(0.0, index=price_df.index)

    for _, row in txns.sort_values("date").iterrows():
        t = row["ticker"]
        if t not in shares_df.columns:
            continue
        txn_ts = pd.Timestamp(row["date"]).tz_localize(price_df.index.tz)
        mask = price_df.index >= txn_ts
        if not mask.any():
            continue
        delta = row["shares"] if row["type"] == "BUY" else -row["shares"]
        shares_df.loc[mask, t] += delta

        # Cash flow: money IN (buy) positive, money OUT (sell) negative
        flow = row["shares"] * row["price"]
        first_date = price_df.index[mask][0]
        if row["type"] == "BUY":
            cashflow_series.loc[first_date] += flow
        else:
            cashflow_series.loc[first_date] -= flow

    portfolio_value = (shares_df * price_df).sum(axis=1)

    valid = portfolio_value > 0
    if not valid.any():
        return None, None

    first_valid = valid.idxmax()
    return portfolio_value.loc[first_valid:], cashflow_series.loc[first_valid:]


def _compute_twr_daily_returns(portfolio_value: pd.Series, cashflow_series: pd.Series) -> pd.Series:
    """Compute daily Time-Weighted Returns from value and cash flow series.

    On each day t:
      V_start(t) = V_end(t-1) + CF(t)   (prior close + any new money added today)
      daily_return(t) = V_end(t) / V_start(t) - 1

    This way, depositing new money doesn't count as a return.
    """
    v_end_prev = portfolio_value.shift(1)
    v_start = v_end_prev + cashflow_series

    # First day: starting value is the cash invested
    if cashflow_series.iloc[0] > 0:
        v_start.iloc[0] = cashflow_series.iloc[0]
    else:
        v_start.iloc[0] = portfolio_value.iloc[0]

    daily_return = (portfolio_value / v_start - 1)
    daily_return = daily_return.replace([float("inf"), float("-inf")], 0.0).fillna(0.0)
    daily_return = daily_return.clip(-0.5, 0.5)
    return daily_return


def get_time_weighted_return(user_id: int, period: str = "1y") -> pd.Series:
    """Cumulative Time-Weighted Return series (as percentage).

    TWR strips out cash flows so it measures pure investment performance,
    making it directly comparable to a benchmark like the S&P 500.
    """
    pv, cf = _build_twr_components(user_id, period)
    if pv is None:
        return pd.Series(dtype=float)

    daily_return = _compute_twr_daily_returns(pv, cf)
    cumulative_twr = ((1 + daily_return).cumprod() - 1) * 100
    return cumulative_twr


def get_portfolio_daily_returns(user_id: int, period: str = "1y") -> pd.Series:
    """Daily percentage returns of the portfolio (TWR-based, excludes cash flow effects)."""
    pv, cf = _build_twr_components(user_id, period)
    if pv is None:
        return pd.Series(dtype=float)
    return _compute_twr_daily_returns(pv, cf)
