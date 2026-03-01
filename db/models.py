import pandas as pd
from db.database import get_connection


def _validate_no_negative_holdings(conn, ticker, exclude_id=None):
    """Ensure shares never go negative at any point in the transaction timeline."""
    query = """
        SELECT date, type, shares FROM transactions
        WHERE ticker = ? AND (? IS NULL OR id != ?)
        ORDER BY date ASC, id ASC
    """
    rows = conn.execute(query, (ticker, exclude_id, exclude_id)).fetchall()
    running = 0.0
    for row in rows:
        if row["type"] == "BUY":
            running += row["shares"]
        else:
            running -= row["shares"]
        if running < -1e-9:
            raise ValueError(
                f"This would cause negative holdings of {ticker} on {row['date']}"
            )


def add_transaction(ticker: str, txn_type: str, shares: float, price: float, date: str, notes: str = "") -> int:
    conn = get_connection()
    try:
        # For SELL, validate we have enough shares
        if txn_type == "SELL":
            # Temporarily check what holdings would look like with this sell
            query = """
                SELECT COALESCE(SUM(CASE WHEN type='BUY' THEN shares ELSE -shares END), 0) as net
                FROM transactions WHERE ticker = ?
            """
            net = conn.execute(query, (ticker,)).fetchone()["net"]
            if net < shares - 1e-9:
                raise ValueError(
                    f"Cannot sell {shares} shares of {ticker}. You only hold {net:.4f} shares."
                )

        cursor = conn.execute(
            """INSERT INTO transactions (ticker, type, shares, price, date, notes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (ticker.upper(), txn_type, shares, price, date, notes),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_transactions(ticker=None, start_date=None, end_date=None) -> pd.DataFrame:
    conn = get_connection()
    try:
        query = "SELECT * FROM transactions WHERE 1=1"
        params = []
        if ticker:
            query += " AND ticker = ?"
            params.append(ticker.upper())
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        query += " ORDER BY date DESC, id DESC"
        df = pd.read_sql_query(query, conn, params=params)
        return df
    finally:
        conn.close()


def get_transaction_by_id(txn_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM transactions WHERE id = ?", (txn_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_transaction(txn_id: int, **kwargs) -> bool:
    conn = get_connection()
    try:
        allowed = {"ticker", "type", "shares", "price", "date", "notes"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        # Build the updated transaction to validate
        current = conn.execute("SELECT * FROM transactions WHERE id = ?", (txn_id,)).fetchone()
        if not current:
            return False

        merged = dict(current)
        merged.update(updates)
        if "ticker" in updates:
            merged["ticker"] = updates["ticker"].upper()

        # Validate no negative holdings with this change
        _validate_no_negative_holdings(conn, merged["ticker"], exclude_id=txn_id)

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [txn_id]
        conn.execute(
            f"UPDATE transactions SET {set_clause}, updated_at = datetime('now') WHERE id = ?",
            values,
        )
        conn.commit()
        return True
    finally:
        conn.close()


def delete_transaction(txn_id: int) -> bool:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM transactions WHERE id = ?", (txn_id,)).fetchone()
        if not row:
            return False

        # Validate that deleting this transaction won't cause negative holdings
        _validate_no_negative_holdings(conn, row["ticker"], exclude_id=txn_id)

        conn.execute("DELETE FROM transactions WHERE id = ?", (txn_id,))
        conn.commit()
        return True
    finally:
        conn.close()


def get_distinct_tickers() -> list[str]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT DISTINCT ticker FROM transactions ORDER BY ticker").fetchall()
        return [r["ticker"] for r in rows]
    finally:
        conn.close()
