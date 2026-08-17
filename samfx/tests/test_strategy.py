import pandas as pd
import pytest

from samfx.config import StrategyConfig
from samfx.data import generate_synthetic_ohlc
from samfx.strategy import LONG, SHORT, SamFxStrategy


def test_generate_signals_adds_expected_columns():
    df = generate_synthetic_ohlc(n_bars=200, seed=1)
    strategy = SamFxStrategy()
    out = strategy.generate_signals(df)

    for col in ("ema_fast", "ema_slow", "rsi", "atr", "signal", "stop_loss", "take_profit"):
        assert col in out.columns
    assert len(out) == len(df)
    assert set(out["signal"].unique()) <= {LONG, SHORT, 0}


def test_generate_signals_requires_ohlc_columns():
    df = pd.DataFrame({"open": [1, 2], "high": [1, 2], "low": [1, 2]})  # missing 'close'
    with pytest.raises(ValueError, match="missing required columns"):
        SamFxStrategy().generate_signals(df)


def test_generate_signals_rejects_empty_df():
    df = pd.DataFrame(columns=["open", "high", "low", "close"])
    with pytest.raises(ValueError, match="empty"):
        SamFxStrategy().generate_signals(df)


def test_long_signal_has_tp_above_and_sl_below_entry():
    df = generate_synthetic_ohlc(n_bars=500, seed=7)
    out = SamFxStrategy().generate_signals(df)
    longs = out[out["signal"] == LONG]
    if len(longs) == 0:
        pytest.skip("no long signals generated for this seed")
    assert (longs["take_profit"] > longs["close"]).all()
    assert (longs["stop_loss"] < longs["close"]).all()


def test_short_signal_has_tp_below_and_sl_above_entry():
    df = generate_synthetic_ohlc(n_bars=500, seed=7)
    out = SamFxStrategy().generate_signals(df)
    shorts = out[out["signal"] == SHORT]
    if len(shorts) == 0:
        pytest.skip("no short signals generated for this seed")
    assert (shorts["take_profit"] < shorts["close"]).all()
    assert (shorts["stop_loss"] > shorts["close"]).all()


def test_strategy_config_validation():
    with pytest.raises(ValueError):
        StrategyConfig(fast_ema=26, slow_ema=12)
    with pytest.raises(ValueError):
        StrategyConfig(rsi_oversold=80, rsi_overbought=20)
    with pytest.raises(ValueError):
        StrategyConfig(atr_sl_mult=0)
