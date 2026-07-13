"""Headless command-line entry point for the trend-confirmation engine."""

import argparse
import sys

from .data import fetch_ohlcv, resolve_ticker
from .engine import AnalysisResult, analyze
from .risk import PositionSize, position_size


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stockanalyzer",
        description="Analizza un ticker con il motore di trend-confirmation a regole.",
    )
    parser.add_argument("query", help="Ticker (es. AAPL) o nome azienda (es. Apple)")
    parser.add_argument("--period", default="1y", help="Periodo Yahoo Finance (default: 1y)")
    parser.add_argument("--interval", default="1d", help="Intervallo Yahoo Finance (default: 1d)")
    parser.add_argument("--macd", action="store_true", help="Abilita il leg opzionale MACD")
    parser.add_argument(
        "--bollinger", action="store_true", help="Abilita il leg opzionale Bollinger Bands"
    )
    parser.add_argument(
        "--account-size", type=float, default=None, help="Capitale, per calcolare il position sizing"
    )
    parser.add_argument(
        "--risk-pct", type=float, default=1.0, help="Rischio percentuale per trade (default: 1.0)"
    )
    return parser


def _format_result(symbol: str, name: str, result: AnalysisResult, sizing: PositionSize | None) -> str:
    lines = [
        f"{symbol} — {name}" if name != symbol else symbol,
        f"Direzione: {result.direction.upper()}",
        f"Confidenza: {result.score:.1f}/100 ({result.confirmations}/{result.total_legs} conferme)",
        "",
    ]
    for leg in result.legs:
        lines.append(f"  [{leg.state:7}] {leg.name}: {leg.detail}")
    lines += [
        "",
        f"Prezzo: {result.price:.2f}",
        f"ATR: {result.atr:.2f}",
        f"Stop suggerito: {result.suggested_stop_distance:.2f}",
    ]
    if sizing is not None:
        lines.append(
            f"Size suggerita: {sizing.shares} azioni "
            f"(~{sizing.position_value:.2f}, rischio {sizing.risk_amount:.2f})"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    extra_legs = set()
    if args.macd:
        extra_legs.add("macd")
    if args.bollinger:
        extra_legs.add("bollinger")

    try:
        symbol, name = resolve_ticker(args.query)
        df = fetch_ohlcv(symbol, period=args.period, interval=args.interval)
        result = analyze(df, extra_legs=frozenset(extra_legs))
    except Exception as exc:  # noqa: BLE001 - surface any failure on stderr with a non-zero exit
        print(f"Errore: {exc}", file=sys.stderr)
        return 1

    sizing = None
    if args.account_size is not None:
        sizing = position_size(
            account_size=args.account_size,
            risk_pct=args.risk_pct,
            stop_distance=result.suggested_stop_distance,
            price=result.price,
        )

    print(_format_result(symbol, name, result, sizing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
