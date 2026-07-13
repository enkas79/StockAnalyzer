from unittest.mock import patch

import pandas as pd

from stockanalyzer.cli import main
from stockanalyzer.engine import AnalysisResult, Leg

_RESULT = AnalysisResult(
    direction="bullish",
    score=75.0,
    confirmations=2,
    total_legs=3,
    legs=[
        Leg("trend", "confirm", "EMA50 > EMA200 e prezzo sopra EMA50."),
        Leg("momentum", "confirm", "RSI conferma."),
        Leg("volume", "neutral", "Volume nella norma."),
    ],
    price=100.0,
    ema50=95.0,
    ema200=90.0,
    rsi=55.0,
    relative_volume=1.0,
    atr=2.0,
    suggested_stop_distance=3.0,
)


def _patched(**overrides):
    defaults = dict(
        resolve_ticker=("AAPL", "Apple Inc."),
        fetch_ohlcv=pd.DataFrame({"close": [100.0]}),
        analyze=_RESULT,
    )
    defaults.update(overrides)
    return (
        patch("stockanalyzer.cli.resolve_ticker", return_value=defaults["resolve_ticker"]),
        patch("stockanalyzer.cli.fetch_ohlcv", return_value=defaults["fetch_ohlcv"]),
        patch("stockanalyzer.cli.analyze", return_value=defaults["analyze"]),
    )


def test_cli_prints_summary_and_returns_zero(capsys):
    p1, p2, p3 = _patched()
    with p1, p2, p3:
        exit_code = main(["aapl"])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "AAPL — Apple Inc." in out
    assert "Direzione: BULLISH" in out
    assert "Confidenza: 75.0/100 (2/3 conferme)" in out
    assert "Stop suggerito: 3.00" in out
    assert "Size suggerita" not in out


def test_cli_includes_position_sizing_when_requested(capsys):
    p1, p2, p3 = _patched()
    with p1, p2, p3:
        exit_code = main(["aapl", "--account-size", "10000", "--risk-pct", "1"])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "Size suggerita:" in out


def test_cli_passes_extra_legs_through_to_analyze(capsys):
    p1, p2, p3 = _patched()
    with p1, p2, p3 as mock_analyze:
        main(["aapl", "--macd", "--bollinger"])

    _args, kwargs = mock_analyze.call_args
    assert kwargs["extra_legs"] == frozenset({"macd", "bollinger"})


def test_cli_reports_error_and_returns_one_on_failure(capsys):
    with patch("stockanalyzer.cli.resolve_ticker", side_effect=ValueError("ticker mancante")):
        exit_code = main([""])

    err = capsys.readouterr().err
    assert exit_code == 1
    assert "Errore: ticker mancante" in err
