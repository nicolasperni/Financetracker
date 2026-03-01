import streamlit as st
import yfinance as yf
import pandas as pd


@st.cache_data(ttl=300, show_spinner=False)
def get_current_price(ticker: str) -> dict:
    """Return current price and daily change for a ticker."""
    t = yf.Ticker(ticker)
    info = t.fast_info
    last = info.last_price
    prev = info.previous_close
    change = last - prev if prev else 0.0
    change_pct = change / prev if prev else 0.0

    # Get the full name (cached separately since it's slower)
    name = _get_ticker_name(ticker)

    return {
        "price": last,
        "previous_close": prev,
        "change": change,
        "change_pct": change_pct,
        "name": name,
    }


@st.cache_data(ttl=86400, show_spinner=False)
def _get_ticker_name(ticker: str) -> str:
    """Get human-readable name for a ticker. Cached for 24h."""
    try:
        t = yf.Ticker(ticker)
        return t.info.get("shortName", ticker)
    except Exception:
        return ticker


@st.cache_data(ttl=3600, show_spinner=False)
def get_history(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """Return OHLCV history for a single ticker."""
    t = yf.Ticker(ticker)
    df = t.history(period=period, interval=interval)
    return df


@st.cache_data(ttl=86400, show_spinner=False)
def get_annual_stats(ticker: str, years: int = 5) -> dict:
    """Compute annualized return and volatility from historical data."""
    df = get_history(ticker, period=f"{years}y", interval="1d")
    daily_returns = df["Close"].pct_change().dropna()
    trading_days = 252
    annual_return = float(daily_returns.mean() * trading_days)
    annual_volatility = float(daily_returns.std() * (trading_days**0.5))
    return {
        "annual_return": annual_return,
        "annual_volatility": annual_volatility,
    }


@st.cache_data(ttl=86400, show_spinner=False)
def get_price_on_date(ticker: str, date_str: str, hour: float = 12.0) -> float | None:
    """Get the price for a ticker on a specific date and hour (EST).

    Tries hourly data first (available for ~last 730 days). If hourly data
    is available, returns the price closest to the requested hour.
    Falls back to daily OHLC interpolation for older dates:
      - hour <= 10 (near open): use Open price
      - hour >= 15 (near close): use Close price
      - in between: linear interpolation between Open and Close

    Args:
        ticker: Stock ticker symbol.
        date_str: Date as "YYYY-MM-DD".
        hour: Hour of day in EST as float (e.g. 12.5 = 12:30 PM). Defaults to 12.0 (noon).
    """
    from datetime import datetime, timedelta

    target_date = datetime.strptime(date_str, "%Y-%m-%d")

    t = yf.Ticker(ticker)

    # --- Try hourly data first ---
    start_1h = target_date - timedelta(days=1)
    end_1h = target_date + timedelta(days=2)
    try:
        hist_1h = t.history(
            start=start_1h.strftime("%Y-%m-%d"),
            end=end_1h.strftime("%Y-%m-%d"),
            interval="1h",
        )
        if not hist_1h.empty:
            # Ensure timezone-aware comparison
            idx = hist_1h.index
            if idx.tz is None:
                idx = idx.tz_localize("US/Eastern")
            else:
                idx = idx.tz_convert("US/Eastern")
            hist_1h.index = idx

            # Filter to the target date
            same_day = hist_1h[idx.date == target_date.date()]
            if not same_day.empty:
                # Find bar closest to the requested hour
                diffs = abs(same_day.index.hour + same_day.index.minute / 60 - hour)
                closest_idx = diffs.argmin()
                return float(same_day["Close"].iloc[closest_idx])
    except Exception:
        pass  # Fall through to daily data

    # --- Fallback: daily OHLC ---
    start_d = target_date - timedelta(days=10)
    end_d = target_date + timedelta(days=1)
    hist_d = t.history(start=start_d.strftime("%Y-%m-%d"), end=end_d.strftime("%Y-%m-%d"))
    if hist_d.empty:
        return None

    hist_d.index = hist_d.index.tz_localize(None)
    valid = hist_d[hist_d.index <= target_date]
    if valid.empty:
        row = hist_d.iloc[0]
    else:
        row = valid.iloc[-1]

    open_price = float(row["Open"])
    close_price = float(row["Close"])

    # Interpolate based on hour within market hours (9:30-16:00 ET)
    MARKET_OPEN_H = 9.5
    MARKET_CLOSE_H = 16.0
    if hour <= MARKET_OPEN_H:
        return open_price
    elif hour >= MARKET_CLOSE_H:
        return close_price
    else:
        frac = (hour - MARKET_OPEN_H) / (MARKET_CLOSE_H - MARKET_OPEN_H)
        return open_price + frac * (close_price - open_price)


@st.cache_data(ttl=300, show_spinner=False)
def validate_ticker(ticker: str) -> bool:
    """Check if a ticker is valid by trying to fetch its price."""
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        return info.last_price is not None
    except Exception:
        return False
