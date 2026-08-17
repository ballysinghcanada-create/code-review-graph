# Samfx

A small, self-contained forex trading strategy and backtester, implemented in Python.

> **Disclaimer:** This is an educational/demo trading strategy, not financial
> advice. Backtested performance on historical or synthetic data does not
> guarantee future results. Do not trade real capital based on this code
> without independent risk review.

## Strategy

Samfx is a trend-following strategy:

- **Entry:** EMA(12) crosses EMA(26) — long on a bullish cross, short on a
  bearish cross.
- **Filter:** the cross is only taken if RSI(14) isn't already in overbought
  (>70) territory for longs, or oversold (<30) for shorts — this avoids
  entering a move that's already exhausted.
- **Exit:** ATR(14)-based stop-loss (1.5x ATR) and take-profit (3x ATR), for
  a 2:1 reward:risk ratio by default. Only one position is open at a time.
- **Position sizing:** each trade risks a fixed percentage of account
  balance (default 1%), sized off the distance to the stop-loss.

All parameters are configurable via `StrategyConfig` / `BacktestConfig`.

## Layout

```
samfx/
  config.py       # StrategyConfig, BacktestConfig
  indicators.py   # EMA, SMA, RSI, ATR (pandas-only, no TA-Lib)
  strategy.py      # SamFxStrategy.generate_signals()
  backtester.py    # Backtester.run() -> PerformanceReport
  data.py          # generate_synthetic_ohlc() for demos/tests
  cli.py           # `python -m samfx.cli backtest ...`
  tests/           # pytest suite
```

## Install

```bash
pip install -r samfx/requirements.txt
```

## Usage

### As a library

```python
from samfx.backtester import Backtester
from samfx.data import generate_synthetic_ohlc

df = generate_synthetic_ohlc(n_bars=2000, seed=42)  # or load your own OHLC CSV
report = Backtester().run(df)
print(report.summary())
```

### CLI

```bash
# Quick demo on generated data
python -m samfx.cli backtest --demo --pair EURUSD

# Backtest your own OHLC data (CSV with open,high,low,close[,date] columns)
python -m samfx.cli backtest --data path/to/eurusd_h1.csv --pair EURUSD \
    --risk-pct 1.0 --spread-pips 1.0 --pip-size 0.0001

# For JPY pairs, pip size is 0.01
python -m samfx.cli backtest --data path/to/usdjpy_h1.csv --pip-size 0.01
```

Output:

```
Samfx backtest — EURUSD (2000 bars)
----------------------------------------
      total_trades: 34
              wins: 19
            losses: 15
      win_rate_pct: 55.88
      profit_factor: 1.62
    total_return_pct: 8.41
    max_drawdown_pct: 4.72
      final_balance: 10841.23
```

### Tests

```bash
pytest samfx/tests/ -q
```
