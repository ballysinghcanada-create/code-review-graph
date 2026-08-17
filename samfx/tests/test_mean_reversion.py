import pytest

from samfx.backtester import Backtester
from samfx.data import generate_synthetic_ohlc
from samfx.mean_reversion import MeanReversionStrategy, MeanReversionStrategyConfig
from samfx.strategy import LONG, SHORT


def test_generate_signals_adds_expected_columns():
    df = generate_synthetic_ohlc(n_bars=500, seed=1)
    strategy = MeanReversionStrategy()
    out = strategy.generate_signals(df)

    expected_cols = (
        "bb_upper",
        "bb_middle",
        "bb_lower",
        "rsi",
        "atr",
        "signal",
        "stop_loss",
        "take_profit",
    )
    for col in expected_cols:
        assert col in out.columns
    assert set(out["signal"].unique()) <= {LONG, SHORT, 0}


def test_long_signal_has_small_tp_and_wide_sl():
    df = generate_synthetic_ohlc(n_bars=1000, seed=3)
    out = MeanReversionStrategy().generate_signals(df)
    longs = out[out["signal"] == LONG]
    if len(longs) == 0:
        pytest.skip("no long signals generated for this seed")

    tp_distance = longs["take_profit"] - longs["close"]
    sl_distance = longs["close"] - longs["stop_loss"]
    assert (tp_distance > 0).all()
    assert (sl_distance > 0).all()
    # the whole point of this strategy: reward is much smaller than risk
    assert (tp_distance < sl_distance).all()


def test_requires_ohlc_columns():
    import pandas as pd

    df = pd.DataFrame({"open": [1, 2], "high": [1, 2], "low": [1, 2]})
    with pytest.raises(ValueError, match="missing required columns"):
        MeanReversionStrategy().generate_signals(df)


def test_config_validation():
    with pytest.raises(ValueError):
        MeanReversionStrategyConfig(bb_std=0)
    with pytest.raises(ValueError):
        MeanReversionStrategyConfig(rsi_oversold=80, rsi_overbought=20)
    with pytest.raises(ValueError):
        MeanReversionStrategyConfig(tp_atr_mult=0)


def test_default_config_averages_roughly_85pct_win_rate_across_seeds():
    """Documents the strategy's actual behavior: a tight TP vs. wide SL
    (0.55x ATR vs 3.4x ATR) produces a high win rate by construction, even
    on data with no real mean-reversion edge (a synthetic random walk)."""
    win_rates = []
    for seed in range(1, 21):
        df = generate_synthetic_ohlc(n_bars=2000, seed=seed)
        report = Backtester(strategy=MeanReversionStrategy()).run(df)
        if report.total_trades >= 10:
            win_rates.append(report.win_rate)

    assert len(win_rates) >= 15, "expected most seeds to generate enough trades"
    avg_win_rate = sum(win_rates) / len(win_rates)
    assert 0.75 <= avg_win_rate <= 0.95


def test_high_win_rate_does_not_imply_reliably_profitable():
    """The point of shipping this strategy with the warning it carries:
    average win size is far smaller than average loss size, so profit
    factor/expectancy — not win_rate — decide whether it actually makes
    money, and either sign is possible depending on the data."""
    df = generate_synthetic_ohlc(n_bars=2000, seed=42)
    report = Backtester(strategy=MeanReversionStrategy()).run(df)
    if report.total_trades < 5:
        pytest.skip("not enough trades for this seed")

    assert report.average_loss > report.average_win
