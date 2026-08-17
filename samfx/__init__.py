"""Samfx — a trend-following forex trading strategy with a bar-by-bar backtester."""

from samfx.config import StrategyConfig
from samfx.strategy import SamFxStrategy

__all__ = ["SamFxStrategy", "StrategyConfig"]

__version__ = "0.1.0"
