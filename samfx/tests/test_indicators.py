import pandas as pd
import pytest

from samfx.indicators import atr, ema, rsi, sma, true_range


def test_sma_basic():
    s = pd.Series([1, 2, 3, 4, 5])
    result = sma(s, window=2)
    assert result.iloc[-1] == pytest.approx(4.5)
    assert pd.isna(result.iloc[0])


def test_ema_converges_toward_constant_series():
    s = pd.Series([10.0] * 50)
    result = ema(s, span=10)
    assert result.iloc[-1] == pytest.approx(10.0)


def test_rsi_all_gains_is_100():
    s = pd.Series(range(1, 30))  # strictly increasing
    result = rsi(s, period=14)
    assert result.iloc[-1] == pytest.approx(100.0)


def test_rsi_all_losses_is_0():
    s = pd.Series(range(30, 1, -1))  # strictly decreasing
    result = rsi(s, period=14)
    assert result.iloc[-1] == pytest.approx(0.0)


def test_rsi_bounded_0_100():
    s = pd.Series([1.0, 2.0, 1.5, 3.0, 2.5, 4.0, 3.5, 5.0, 1.0, 6.0, 2.0, 7.0, 3.0, 8.0, 4.0])
    result = rsi(s, period=14)
    assert ((result >= 0) & (result <= 100)).all()


def test_true_range_and_atr_non_negative():
    df = pd.DataFrame(
        {
            "high": [1.2, 1.3, 1.25, 1.4],
            "low": [1.0, 1.1, 1.05, 1.2],
            "close": [1.1, 1.2, 1.15, 1.35],
        }
    )
    tr = true_range(df)
    assert (tr >= 0).all()
    result = atr(df, period=2)
    assert (result.dropna() >= 0).all()
