from samfx.cli import build_parser, main


def test_backtest_demo_runs_and_prints_summary(capsys):
    exit_code = main(["backtest", "--demo", "--pair", "EURUSD"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Samfx backtest" in captured.out
    assert "win_rate_pct" in captured.out


def test_backtest_without_data_or_demo_errors(capsys):
    exit_code = main(["backtest"])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert "--data" in captured.err


def test_backtest_from_csv(tmp_path):
    from samfx.data import generate_synthetic_ohlc

    df = generate_synthetic_ohlc(n_bars=100, seed=8)
    csv_path = tmp_path / "eurusd.csv"
    df.reset_index(names="date").to_csv(csv_path, index=False)

    exit_code = main(["backtest", "--data", str(csv_path)])
    assert exit_code == 0


def test_parser_requires_subcommand():
    parser = build_parser()
    assert parser.prog == "samfx"
