"""Bar-by-bar backtester for any Samfx strategy's signals.

Signals are generated once (vectorized), then simulated sequentially:
entries fill at the *next* bar's open (no lookahead), and each open trade
is walked forward bar-by-bar until its stop-loss or take-profit is touched.
Only one position is open at a time.
"""

from dataclasses import dataclass, field
from typing import Protocol

import pandas as pd

from samfx.config import BacktestConfig
from samfx.strategy import LONG, SamFxStrategy


class SignalGenerator(Protocol):
    """Any strategy that turns OHLC bars into signal/stop_loss/take_profit
    columns can be backtested — see SamFxStrategy and MeanReversionStrategy."""

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame: ...


@dataclass
class Trade:
    direction: int  # LONG or SHORT
    entry_index: int
    entry_price: float
    stop_loss: float
    take_profit: float
    size: float
    exit_index: int | None = None
    exit_price: float | None = None
    exit_reason: str | None = None
    pnl: float = 0.0

    @property
    def is_open(self) -> bool:
        return self.exit_index is None


@dataclass
class PerformanceReport:
    trades: list[Trade]
    equity_curve: list[float]
    initial_balance: float
    final_balance: float

    @property
    def total_trades(self) -> int:
        return len(self.trades)

    @property
    def wins(self) -> int:
        return sum(1 for t in self.trades if t.pnl > 0)

    @property
    def losses(self) -> int:
        return sum(1 for t in self.trades if t.pnl <= 0)

    @property
    def win_rate(self) -> float:
        return self.wins / self.total_trades if self.total_trades else 0.0

    @property
    def total_return_pct(self) -> float:
        return (self.final_balance / self.initial_balance - 1) * 100

    @property
    def profit_factor(self) -> float:
        gross_profit = sum(t.pnl for t in self.trades if t.pnl > 0)
        gross_loss = -sum(t.pnl for t in self.trades if t.pnl < 0)
        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0
        return gross_profit / gross_loss

    @property
    def average_win(self) -> float:
        wins = [t.pnl for t in self.trades if t.pnl > 0]
        return sum(wins) / len(wins) if wins else 0.0

    @property
    def average_loss(self) -> float:
        """Average losing trade, as a positive magnitude."""
        losses = [-t.pnl for t in self.trades if t.pnl < 0]
        return sum(losses) / len(losses) if losses else 0.0

    @property
    def expectancy(self) -> float:
        """Expected P&L per trade: win_rate * avg_win - loss_rate * avg_loss.

        A high win_rate with a small avg_win and a large avg_loss can still
        yield a negative expectancy — win rate alone does not imply
        profitability.
        """
        loss_rate = 1 - self.win_rate
        return self.win_rate * self.average_win - loss_rate * self.average_loss

    @property
    def max_drawdown_pct(self) -> float:
        peak = float("-inf")
        max_dd = 0.0
        for value in self.equity_curve:
            peak = max(peak, value)
            if peak > 0:
                max_dd = max(max_dd, (peak - value) / peak)
        return max_dd * 100

    def summary(self) -> dict[str, float | int]:
        return {
            "total_trades": self.total_trades,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate_pct": round(self.win_rate * 100, 2),
            "profit_factor": round(self.profit_factor, 2),
            "expectancy_per_trade": round(self.expectancy, 2),
            "average_win": round(self.average_win, 2),
            "average_loss": round(self.average_loss, 2),
            "total_return_pct": round(self.total_return_pct, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "final_balance": round(self.final_balance, 2),
        }


@dataclass
class Backtester:
    strategy: SignalGenerator = field(default_factory=SamFxStrategy)
    config: BacktestConfig = field(default_factory=BacktestConfig)

    def run(self, df: pd.DataFrame) -> PerformanceReport:
        signals = self.strategy.generate_signals(df).reset_index(drop=True)
        cfg = self.config
        spread = cfg.spread_pips * cfg.pip_size

        balance = cfg.initial_balance
        equity_curve: list[float] = [balance]
        trades: list[Trade] = []
        open_trade: Trade | None = None
        n = len(signals)

        for i in range(n):
            row = signals.iloc[i]

            if open_trade is not None:
                hit_sl = (
                    row["low"] <= open_trade.stop_loss
                    if open_trade.direction == LONG
                    else row["high"] >= open_trade.stop_loss
                )
                hit_tp = (
                    row["high"] >= open_trade.take_profit
                    if open_trade.direction == LONG
                    else row["low"] <= open_trade.take_profit
                )
                if hit_sl or hit_tp:
                    # Conservative: if both levels are touched in the same bar,
                    # assume the adverse (stop-loss) outcome fills first.
                    exit_price = open_trade.stop_loss if hit_sl else open_trade.take_profit
                    reason = "stop_loss" if hit_sl else "take_profit"
                    price_diff = (
                        exit_price - open_trade.entry_price
                        if open_trade.direction == LONG
                        else open_trade.entry_price - exit_price
                    )
                    open_trade.exit_index = i
                    open_trade.exit_price = exit_price
                    open_trade.exit_reason = reason
                    open_trade.pnl = price_diff * open_trade.size
                    balance += open_trade.pnl
                    trades.append(open_trade)
                    open_trade = None

            if open_trade is None and i > 0:
                prev = signals.iloc[i - 1]
                if prev["signal"] != 0:
                    entry_price = row["open"]
                    entry_price += spread if prev["signal"] == LONG else -spread
                    stop_loss = prev["stop_loss"]
                    take_profit = prev["take_profit"]
                    stop_distance = abs(entry_price - stop_loss)
                    if stop_distance > 0 and not pd.isna(stop_loss):
                        risk_amount = balance * (cfg.risk_per_trade_pct / 100)
                        size = risk_amount / stop_distance
                        open_trade = Trade(
                            direction=int(prev["signal"]),
                            entry_index=i,
                            entry_price=entry_price,
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                            size=size,
                        )

            mark_price = row["close"]
            unrealized = 0.0
            if open_trade is not None:
                price_diff = (
                    mark_price - open_trade.entry_price
                    if open_trade.direction == LONG
                    else open_trade.entry_price - mark_price
                )
                unrealized = price_diff * open_trade.size
            equity_curve.append(balance + unrealized)

        if open_trade is not None:
            last = signals.iloc[-1]
            exit_price = last["close"]
            price_diff = (
                exit_price - open_trade.entry_price
                if open_trade.direction == LONG
                else open_trade.entry_price - exit_price
            )
            open_trade.exit_index = n - 1
            open_trade.exit_price = exit_price
            open_trade.exit_reason = "end_of_data"
            open_trade.pnl = price_diff * open_trade.size
            balance += open_trade.pnl
            trades.append(open_trade)

        return PerformanceReport(
            trades=trades,
            equity_curve=equity_curve,
            initial_balance=cfg.initial_balance,
            final_balance=balance,
        )
