"""CLI entry point: `python -m samfx.cli backtest [options]`."""

import argparse
import sys

import pandas as pd

from samfx.backtester import Backtester
from samfx.config import BacktestConfig, StrategyConfig
from samfx.data import generate_synthetic_ohlc
from samfx.strategy import SamFxStrategy


def _load_ohlc(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    required = {"open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV at {path} is missing required columns: {sorted(missing)}")
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
    return df


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="samfx", description="Samfx forex strategy CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    bt = sub.add_parser("backtest", help="Run a backtest over OHLC data")
    bt.add_argument("--data", help="Path to a CSV with open,high,low,close[,date] columns")
    bt.add_argument("--demo", action="store_true", help="Use generated synthetic data instead")
    bt.add_argument("--pair", default="EURUSD", help="Pair label, used only for display")
    bt.add_argument("--initial-balance", type=float, default=10_000.0)
    bt.add_argument("--risk-pct", type=float, default=1.0, help="Risk per trade, percent")
    bt.add_argument("--spread-pips", type=float, default=1.0)
    bt.add_argument("--pip-size", type=float, default=0.0001, help="0.01 for JPY pairs")
    bt.add_argument("--fast-ema", type=int, default=12)
    bt.add_argument("--slow-ema", type=int, default=26)
    bt.add_argument("--rsi-period", type=int, default=14)
    bt.add_argument("--atr-period", type=int, default=14)
    bt.add_argument("--atr-sl-mult", type=float, default=1.5)
    bt.add_argument("--atr-tp-mult", type=float, default=3.0)

    return parser


def run_backtest(args: argparse.Namespace) -> int:
    if not args.data and not args.demo:
        print("error: pass --data <csv> or --demo", file=sys.stderr)
        return 2

    df = generate_synthetic_ohlc() if args.demo else _load_ohlc(args.data)

    strategy_cfg = StrategyConfig(
        fast_ema=args.fast_ema,
        slow_ema=args.slow_ema,
        rsi_period=args.rsi_period,
        atr_period=args.atr_period,
        atr_sl_mult=args.atr_sl_mult,
        atr_tp_mult=args.atr_tp_mult,
    )
    backtest_cfg = BacktestConfig(
        initial_balance=args.initial_balance,
        risk_per_trade_pct=args.risk_pct,
        spread_pips=args.spread_pips,
        pip_size=args.pip_size,
    )

    backtester = Backtester(strategy=SamFxStrategy(strategy_cfg), config=backtest_cfg)
    report = backtester.run(df)

    print(f"Samfx backtest — {args.pair} ({len(df)} bars)")
    print("-" * 40)
    for key, value in report.summary().items():
        print(f"{key:>18}: {value}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "backtest":
        return run_backtest(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
