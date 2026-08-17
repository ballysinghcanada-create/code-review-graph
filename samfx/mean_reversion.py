"""A deliberately high-win-rate mean-reversion strategy.

WARNING: this strategy is included as a documented example of why "win
rate" alone is a misleading metric. It works by taking a *small*
take-profit and a *wide* stop-loss, so it wins on most small pullbacks
but gives back many wins' worth of gain on the rare trade that runs to
its stop. See samfx/README.md ("Why 85% win rate isn't the same as
profitable") before using this as a template for anything real.

Entry logic: fade RSI extremes at the Bollinger Bands — long when price
touches/pierces the lower band while RSI is oversold, short at the upper
band while RSI is overbought, betting on reversion toward the mean.
"""

import pandas as pd

from samfx.indicators import atr, bollinger_bands, rsi
from samfx.strategy import FLAT, LONG, SHORT

REQUIRED_COLUMNS = ("open", "high", "low", "close")


class MeanReversionStrategyConfig:
    """Config for MeanReversionStrategy (separate from the trend StrategyConfig
    since the parameters — Bollinger period/width and asymmetric TP/SL — don't
    overlap with the EMA-crossover strategy)."""

    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
        rsi_period: int = 14,
        rsi_oversold: float = 30.0,
        rsi_overbought: float = 70.0,
        atr_period: int = 14,
        tp_atr_mult: float = 0.55,
        sl_atr_mult: float = 3.4,
    ) -> None:
        if bb_period <= 0 or rsi_period <= 0 or atr_period <= 0:
            raise ValueError("bb_period, rsi_period, atr_period must be positive")
        if bb_std <= 0:
            raise ValueError("bb_std must be positive")
        if not (0 < rsi_oversold < rsi_overbought < 100):
            raise ValueError("require 0 < rsi_oversold < rsi_overbought < 100")
        if tp_atr_mult <= 0 or sl_atr_mult <= 0:
            raise ValueError("tp_atr_mult and sl_atr_mult must be positive")
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.atr_period = atr_period
        self.tp_atr_mult = tp_atr_mult
        self.sl_atr_mult = sl_atr_mult


class MeanReversionStrategy:
    """Fades RSI extremes at the Bollinger Bands with a tight TP / wide SL.

    Same `generate_signals(df) -> df` contract as SamFxStrategy, so it drops
    straight into Backtester(strategy=MeanReversionStrategy(...)).
    """

    def __init__(self, config: MeanReversionStrategyConfig | None = None) -> None:
        self.config = config or MeanReversionStrategyConfig()

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"df is missing required columns: {missing}")
        if len(df) == 0:
            raise ValueError("df is empty")

        cfg = self.config
        out = df.copy()
        upper, middle, lower = bollinger_bands(out["close"], cfg.bb_period, cfg.bb_std)
        out["bb_upper"], out["bb_middle"], out["bb_lower"] = upper, middle, lower
        out["rsi"] = rsi(out["close"], cfg.rsi_period)
        out["atr"] = atr(out, cfg.atr_period)

        atr_ready = out["atr"].notna() & out["bb_lower"].notna()
        long_ok = (out["close"] <= out["bb_lower"]) & (out["rsi"] < cfg.rsi_oversold) & atr_ready
        short_ok = (out["close"] >= out["bb_upper"]) & (out["rsi"] > cfg.rsi_overbought) & atr_ready

        out["signal"] = FLAT
        out.loc[long_ok, "signal"] = LONG
        out.loc[short_ok, "signal"] = SHORT

        out["stop_loss"] = float("nan")
        out["take_profit"] = float("nan")
        out.loc[long_ok, "stop_loss"] = out.loc[long_ok, "close"] - cfg.sl_atr_mult * out.loc[
            long_ok, "atr"
        ]
        out.loc[long_ok, "take_profit"] = out.loc[long_ok, "close"] + cfg.tp_atr_mult * out.loc[
            long_ok, "atr"
        ]
        out.loc[short_ok, "stop_loss"] = out.loc[short_ok, "close"] + cfg.sl_atr_mult * out.loc[
            short_ok, "atr"
        ]
        out.loc[short_ok, "take_profit"] = out.loc[short_ok, "close"] - cfg.tp_atr_mult * out.loc[
            short_ok, "atr"
        ]

        return out
