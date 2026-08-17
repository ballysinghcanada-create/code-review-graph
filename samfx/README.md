# Samfx

Small, self-contained forex trading strategies and a backtester, implemented in Python.

> **Disclaimer:** These are educational/demo trading strategies, not
> financial advice. Backtested performance on historical or synthetic data
> does not guarantee future results. Do not trade real capital based on this
> code without independent risk review.

Two strategies are included:

| | `SamFxStrategy` (trend) | `MeanReversionStrategy` (high win rate) |
|---|---|---|
| Entry | EMA(12/26) crossover, RSI-filtered | RSI extreme at Bollinger Band, faded |
| Reward:risk | 2:1 (TP 3x ATR, SL 1.5x ATR) | ~1:6 (TP 0.55x ATR, SL 3.4x ATR) |
| Typical win rate | ~35-55% | ~75-95% (averages ~85% across seeds) |
| Typical profit factor | varies, often >1 on trending data | often close to 1, sometimes <1 |

## Why 85% win rate isn't the same as profitable

Win rate and profitability are different axes. You can hit almost any win
rate you want just by shrinking the take-profit relative to the stop-loss —
`MeanReversionStrategy` does exactly that (TP = 0.55x ATR, SL = 3.4x ATR).
For a driftless random walk, the probability of a small barrier being hit
before a far one is approximately `SL / (TP + SL)`, so a ~1:6 reward:risk
ratio mechanically produces a win rate around 85% — independent of whether
the strategy has any real edge.

The catch: **average loss size dwarfs average win size**, so a small run of
bad luck (or one large loss) can offset dozens of small wins. Run
`python -m samfx.cli backtest --demo --strategy mean-reversion` and look at
`average_win` vs. `average_loss`, and `expectancy_per_trade` (win_rate *
avg_win − loss_rate * avg_loss) — not just `win_rate_pct` — to see whether a
given run was actually profitable. `samfx/tests/test_mean_reversion.py`
verifies both the ~85% win rate *and* that average loss exceeds average win,
so the tradeoff is asserted, not just described.

If you want a strategy whose edge doesn't depend on TP/SL geometry, use
`SamFxStrategy` (the trend-following one) instead, or bring your own entry
signal and reuse `Backtester`/`PerformanceReport`.

## Strategies

### `SamFxStrategy` — trend-following

- **Entry:** EMA(12) crosses EMA(26) — long on a bullish cross, short on a
  bearish cross.
- **Filter:** the cross is only taken if RSI(14) isn't already in overbought
  (>70) territory for longs, or oversold (<30) for shorts — this avoids
  entering a move that's already exhausted.
- **Exit:** ATR(14)-based stop-loss (1.5x ATR) and take-profit (3x ATR), for
  a 2:1 reward:risk ratio by default.

### `MeanReversionStrategy` — high win rate

- **Entry:** price touches the lower Bollinger Band (period 20, 2σ) while
  RSI(14) is oversold (<30) → long; upper band + overbought (>70) → short.
  Bets on a short-term snap back toward the mean.
- **Exit:** small take-profit (0.55x ATR) and wide stop-loss (3.4x ATR).
  This asymmetry is what drives the high win rate — see above.

Both share:

- **Position sizing:** each trade risks a fixed percentage of account
  balance (default 1%), sized off the distance to the stop-loss.
- **One position at a time**, filled at the next bar's open (no lookahead).

All parameters are configurable via `StrategyConfig` / `MeanReversionStrategyConfig`
/ `BacktestConfig`.

## Layout

```
samfx/
  config.py          # StrategyConfig, BacktestConfig
  indicators.py       # EMA, SMA, RSI, ATR, Bollinger Bands (pandas-only, no TA-Lib)
  strategy.py          # SamFxStrategy.generate_signals()
  mean_reversion.py    # MeanReversionStrategy.generate_signals()
  backtester.py        # Backtester.run() -> PerformanceReport (any strategy)
  data.py              # generate_synthetic_ohlc() for demos/tests
  cli.py               # `python -m samfx.cli backtest ...`
  tests/               # pytest suite
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
from samfx.mean_reversion import MeanReversionStrategy

df = generate_synthetic_ohlc(n_bars=2000, seed=42)  # or load your own OHLC CSV
report = Backtester(strategy=MeanReversionStrategy()).run(df)
print(report.summary())  # check expectancy_per_trade, not just win_rate_pct
```

### CLI

```bash
# Trend strategy (default)
python -m samfx.cli backtest --demo --pair EURUSD

# High win-rate mean-reversion strategy
python -m samfx.cli backtest --demo --strategy mean-reversion --pair EURUSD

# Backtest your own OHLC data (CSV with open,high,low,close[,date] columns)
python -m samfx.cli backtest --data path/to/eurusd_h1.csv --pair EURUSD \
    --strategy mean-reversion --risk-pct 1.0 --spread-pips 1.0 --pip-size 0.0001

# For JPY pairs, pip size is 0.01
python -m samfx.cli backtest --data path/to/usdjpy_h1.csv --pip-size 0.01
```

Output:

```
Samfx backtest [mean-reversion] — EURUSD (2000 bars)
----------------------------------------
        total_trades: 41
                wins: 38
              losses: 3
        win_rate_pct: 92.68
       profit_factor: 1.87
expectancy_per_trade: 6.55
         average_win: 15.17
        average_loss: 102.63
    total_return_pct: 2.69
    max_drawdown_pct: 2.41
       final_balance: 10268.74
----------------------------------------
High win rate here comes from a small TP vs. a wide SL —
check expectancy_per_trade and profit_factor, not just win_rate_pct.
```

### Tests

```bash
pytest samfx/tests/ -q
```
