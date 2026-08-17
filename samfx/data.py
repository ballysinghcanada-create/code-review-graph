"""Synthetic OHLC data generation for demos and tests (no external data files)."""

import numpy as np
import pandas as pd


def generate_synthetic_ohlc(
    n_bars: int = 2000,
    start_price: float = 1.1000,
    daily_vol: float = 0.0015,
    seed: int = 42,
    freq: str = "h",
) -> pd.DataFrame:
    """Generate a plausible random-walk OHLC series for a forex pair.

    Not real market data — useful only for exercising the strategy and
    backtester end-to-end.
    """
    if n_bars <= 0:
        raise ValueError("n_bars must be positive")

    rng = np.random.default_rng(seed)
    returns = rng.normal(loc=0.0, scale=daily_vol, size=n_bars)
    close = start_price * np.cumprod(1 + returns)

    open_ = np.empty(n_bars)
    open_[0] = start_price
    open_[1:] = close[:-1]

    intrabar_range = np.abs(rng.normal(loc=0.0, scale=daily_vol * 0.6, size=n_bars))
    high = np.maximum(open_, close) + intrabar_range
    low = np.minimum(open_, close) - intrabar_range
    volume = rng.integers(low=100, high=10_000, size=n_bars)

    index = pd.date_range("2024-01-01", periods=n_bars, freq=freq)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=index,
    )
