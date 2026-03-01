import re
from datetime import date


def validate_ticker_format(ticker: str) -> str:
    """Basic format check before hitting the API."""
    ticker = ticker.strip().upper()
    if not re.match(r"^[A-Z]{1,5}$", ticker):
        raise ValueError(f"Invalid ticker format: '{ticker}'. Must be 1-5 letters.")
    return ticker


def validate_date(d: date) -> date:
    if d > date.today():
        raise ValueError("Transaction date cannot be in the future.")
    return d


def validate_positive(value: float, field_name: str) -> float:
    if value <= 0:
        raise ValueError(f"{field_name} must be positive.")
    return value
