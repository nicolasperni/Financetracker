import numpy as np


def run_simulation(
    initial_value: float,
    monthly_contribution: float | np.ndarray,
    years: int,
    annual_return: float,
    annual_volatility: float,
    n_simulations: int = 1000,
    seed: int | None = 42,
) -> np.ndarray:
    """Run Monte Carlo simulation using Geometric Brownian Motion.

    monthly_contribution can be a single float (applied every month)
    or an ndarray of length n_months with per-month values.

    Returns np.ndarray of shape (n_simulations, n_months + 1).
    Each row is one simulation path of monthly portfolio values.
    """
    rng = np.random.default_rng(seed)

    n_months = years * 12
    monthly_return = annual_return / 12
    monthly_vol = annual_volatility / np.sqrt(12)

    # GBM drift with Ito correction
    drift = monthly_return - 0.5 * monthly_vol**2

    # Normalize contribution to an array
    if isinstance(monthly_contribution, np.ndarray):
        contributions = monthly_contribution
    else:
        contributions = np.full(n_months, monthly_contribution)

    # Generate all random shocks at once
    Z = rng.standard_normal((n_simulations, n_months))

    paths = np.zeros((n_simulations, n_months + 1))
    paths[:, 0] = initial_value

    for t in range(n_months):
        growth_factor = np.exp(drift + monthly_vol * Z[:, t])
        paths[:, t + 1] = paths[:, t] * growth_factor + contributions[t]

    return paths


def compute_percentiles(
    paths: np.ndarray, percentiles: tuple = (5, 10, 25, 50, 75, 90, 95)
) -> dict:
    """Compute percentile bands from simulation paths."""
    return {p: np.percentile(paths, p, axis=0) for p in percentiles}


def probability_of_target(paths: np.ndarray, target: float) -> float:
    """Fraction of simulations reaching or exceeding the target at final step."""
    return float(np.mean(paths[:, -1] >= target))


def summary_statistics(paths: np.ndarray) -> dict:
    """Summary stats of final portfolio values across all simulations."""
    final = paths[:, -1]
    return {
        "mean": float(np.mean(final)),
        "median": float(np.median(final)),
        "std": float(np.std(final)),
        "p5": float(np.percentile(final, 5)),
        "p10": float(np.percentile(final, 10)),
        "p25": float(np.percentile(final, 25)),
        "p75": float(np.percentile(final, 75)),
        "p90": float(np.percentile(final, 90)),
        "p95": float(np.percentile(final, 95)),
        "min": float(np.min(final)),
        "max": float(np.max(final)),
    }
