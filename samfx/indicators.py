"""Vectorized technical indicators used by the Samfx strategy.

Implemented directly on pandas Series/DataFrame — no TA-Lib dependency.
"""

import pandas as pd


def ema(series: pd.Series, span: int) -> pd.Series:
    """Exponential moving average."""
    return series.ewm(span=span, adjust=False).mean()


def sma(series: pd.Series, window: int) -> pd.Series:
    """Simple moving average."""
    return series.rolling(window=window).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's Relative Strength Index."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    # Wilder smoothing == EWM with alpha = 1/period
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    result = 100 - (100 / (1 + rs))
    return result.where(avg_loss != 0, 100.0).fillna(50.0)


def true_range(df: pd.DataFrame) -> pd.Series:
    """True range from High/Low/Close columns."""
    prev_close = df["close"].shift(1)
    ranges = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range (Wilder smoothing)."""
    tr = true_range(df)
    return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
