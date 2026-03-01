def fmt_currency(value: float) -> str:
    return f"${value:,.2f}"


def fmt_pct(value: float) -> str:
    return f"{value:+.2f}%"


def fmt_shares(value: float) -> str:
    if value == int(value):
        return f"{value:.0f}"
    return f"{value:.4f}"


def color_gain_loss(value: float) -> str:
    return "green" if value >= 0 else "red"
