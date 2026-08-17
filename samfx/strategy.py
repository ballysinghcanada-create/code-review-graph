"""Samfx signal generation: EMA crossover confirmed by RSI, sized off ATR."""

import pandas as pd

from samfx.config import StrategyConfig
from samfx.indicators import atr, ema, rsi

REQUIRED_COLUMNS = ("open", "high", "low", "close")

LONG = 1
SHORT = -1
FLAT = 0


class SamFxStrategy:
    """Trend-following EMA crossover strategy with an RSI entry filter.

    Rules:
      - Long when the fast EMA crosses above the slow EMA and RSI is not
        already overbought (avoids chasing an exhausted move).
      - Short when the fast EMA crosses below the slow EMA and RSI is not
        already oversold.
      - Stop-loss / take-profit distances are derived from ATR at the
        signal bar, giving a volatility-adjusted risk:reward of
        atr_tp_mult : atr_sl_mult (2:1 with the defaults).
    """

    def __init__(self, config: StrategyConfig | None = None) -> None:
        self.config = config or StrategyConfig()

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return a copy of `df` with indicator and signal columns added.

        `df` must contain lowercase OHLC columns: open, high, low, close.
        Added columns: ema_fast, ema_slow, rsi, atr, signal, stop_loss,
        take_profit (the latter two are only meaningful on signal rows).
        """
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"df is missing required columns: {missing}")
        if len(df) == 0:
            raise ValueError("df is empty")

        cfg = self.config
        out = df.copy()
        out["ema_fast"] = ema(out["close"], cfg.fast_ema)
        out["ema_slow"] = ema(out["close"], cfg.slow_ema)
        out["rsi"] = rsi(out["close"], cfg.rsi_period)
        out["atr"] = atr(out, cfg.atr_period)

        fast, slow = out["ema_fast"], out["ema_slow"]
        crossed_up = (fast > slow) & (fast.shift(1) <= slow.shift(1))
        crossed_down = (fast < slow) & (fast.shift(1) >= slow.shift(1))

        atr_ready = out["atr"].notna()
        long_ok = crossed_up & (out["rsi"] < cfg.rsi_overbought) & atr_ready
        short_ok = crossed_down & (out["rsi"] > cfg.rsi_oversold) & atr_ready

        out["signal"] = FLAT
        out.loc[long_ok, "signal"] = LONG
        out.loc[short_ok, "signal"] = SHORT

        out["stop_loss"] = float("nan")
        out["take_profit"] = float("nan")
        out.loc[long_ok, "stop_loss"] = out.loc[long_ok, "close"] - cfg.atr_sl_mult * out.loc[
            long_ok, "atr"
        ]
        out.loc[long_ok, "take_profit"] = out.loc[long_ok, "close"] + cfg.atr_tp_mult * out.loc[
            long_ok, "atr"
        ]
        out.loc[short_ok, "stop_loss"] = out.loc[short_ok, "close"] + cfg.atr_sl_mult * out.loc[
            short_ok, "atr"
        ]
        out.loc[short_ok, "take_profit"] = out.loc[short_ok, "close"] - cfg.atr_tp_mult * out.loc[
            short_ok, "atr"
        ]

        return out
