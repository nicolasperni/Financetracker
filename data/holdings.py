import pandas as pd
from db.models import get_transactions


def compute_holdings() -> pd.DataFrame:
    """Compute current holdings from all transactions.

    Returns DataFrame with columns:
        ticker, total_shares, avg_cost_basis, total_invested
    Only tickers with net shares > 0 are included.
    """
    txns = get_transactions()
    if txns.empty:
        return pd.DataFrame(columns=["ticker", "total_shares", "avg_cost_basis", "total_invested"])

    holdings = []
    for ticker, group in txns.groupby("ticker"):
        buys = group[group["type"] == "BUY"]
        sells = group[group["type"] == "SELL"]

        total_bought = buys["shares"].sum()
        total_sold = sells["shares"].sum() if not sells.empty else 0.0
        net_shares = total_bought - total_sold

        if net_shares < 1e-9:
            continue

        # Average cost basis
        total_cost = (buys["shares"] * buys["price"]).sum()
        avg_cost = total_cost / total_bought if total_bought > 0 else 0

        holdings.append(
            {
                "ticker": ticker,
                "total_shares": net_shares,
                "avg_cost_basis": avg_cost,
                "total_invested": net_shares * avg_cost,
            }
        )

    return pd.DataFrame(holdings)
