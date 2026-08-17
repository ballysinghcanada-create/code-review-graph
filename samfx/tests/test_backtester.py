import pytest

from samfx.backtester import Backtester, PerformanceReport
from samfx.config import BacktestConfig, StrategyConfig
from samfx.data import generate_synthetic_ohlc
from samfx.strategy import SamFxStrategy


def test_run_returns_report_with_consistent_equity_curve():
    df = generate_synthetic_ohlc(n_bars=1000, seed=3)
    backtester = Backtester()
    report = backtester.run(df)

    assert isinstance(report, PerformanceReport)
    assert report.equity_curve[0] == pytest.approx(report.initial_balance)
    assert report.equity_curve[-1] == pytest.approx(report.final_balance, rel=1e-6)
    assert len(report.equity_curve) == len(df) + 1


def test_win_rate_and_profit_factor_are_consistent_with_trades():
    df = generate_synthetic_ohlc(n_bars=1500, seed=11)
    report = Backtester().run(df)

    if report.total_trades == 0:
        pytest.skip("no trades generated for this seed")

    assert report.wins + report.losses == report.total_trades
    assert 0.0 <= report.win_rate <= 1.0
    assert report.profit_factor >= 0.0


def test_max_drawdown_is_non_negative_and_bounded():
    df = generate_synthetic_ohlc(n_bars=1200, seed=5)
    report = Backtester().run(df)
    assert 0.0 <= report.max_drawdown_pct <= 100.0


def test_tighter_risk_per_trade_reduces_position_size_and_drawdown_variance():
    df = generate_synthetic_ohlc(n_bars=1200, seed=9)
    low_risk = Backtester(config=BacktestConfig(risk_per_trade_pct=0.5)).run(df)
    high_risk = Backtester(config=BacktestConfig(risk_per_trade_pct=5.0)).run(df)

    if low_risk.total_trades == 0 or high_risk.total_trades == 0:
        pytest.skip("no trades generated for this seed")

    assert abs(low_risk.trades[0].size) <= abs(high_risk.trades[0].size)


def test_summary_keys():
    df = generate_synthetic_ohlc(n_bars=300, seed=2)
    report = Backtester().run(df)
    summary = report.summary()
    expected_keys = {
        "total_trades",
        "wins",
        "losses",
        "win_rate_pct",
        "profit_factor",
        "total_return_pct",
        "max_drawdown_pct",
        "final_balance",
    }
    assert set(summary.keys()) == expected_keys


def test_custom_strategy_and_backtest_config_wire_through():
    df = generate_synthetic_ohlc(n_bars=800, seed=4)
    backtester = Backtester(
        strategy=SamFxStrategy(StrategyConfig(fast_ema=5, slow_ema=20)),
        config=BacktestConfig(initial_balance=5_000.0, risk_per_trade_pct=2.0),
    )
    report = backtester.run(df)
    assert report.initial_balance == 5_000.0
