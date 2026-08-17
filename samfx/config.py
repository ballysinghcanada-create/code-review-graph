"""Configuration for the Samfx strategy and backtester."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyConfig:
    """Tunable parameters for signal generation.

    Defaults describe a trend-following setup: an EMA(12/26) crossover
    confirmed by RSI(14) so entries aren't taken deep into overbought/oversold
    territory, with ATR(14)-based stop-loss/take-profit distances.
    """

    fast_ema: int = 12
    slow_ema: int = 26
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    atr_period: int = 14
    atr_sl_mult: float = 1.5
    atr_tp_mult: float = 3.0

    def __post_init__(self) -> None:
        if self.fast_ema <= 0 or self.slow_ema <= 0:
            raise ValueError("EMA periods must be positive")
        if self.fast_ema >= self.slow_ema:
            raise ValueError("fast_ema must be shorter than slow_ema")
        if self.rsi_period <= 0 or self.atr_period <= 0:
            raise ValueError("rsi_period and atr_period must be positive")
        if not (0 < self.rsi_oversold < self.rsi_overbought < 100):
            raise ValueError("require 0 < rsi_oversold < rsi_overbought < 100")
        if self.atr_sl_mult <= 0 or self.atr_tp_mult <= 0:
            raise ValueError("ATR multipliers must be positive")


@dataclass(frozen=True)
class BacktestConfig:
    """Execution and risk parameters for the backtester."""

    initial_balance: float = 10_000.0
    risk_per_trade_pct: float = 1.0
    spread_pips: float = 1.0
    pip_size: float = 0.0001

    def __post_init__(self) -> None:
        if self.initial_balance <= 0:
            raise ValueError("initial_balance must be positive")
        if not (0 < self.risk_per_trade_pct <= 100):
            raise ValueError("risk_per_trade_pct must be in (0, 100]")
        if self.spread_pips < 0:
            raise ValueError("spread_pips cannot be negative")
        if self.pip_size <= 0:
            raise ValueError("pip_size must be positive")
