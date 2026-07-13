"""OHLCV data fetching via Yahoo Finance."""

import pandas as pd
import yfinance as yf

from .engine import MIN_BARS

REQUIRED_COLUMNS = ["open", "high", "low", "close", "volume"]

# Selectable periods, in Yahoo Finance's `period` format, with an Italian
# label and an approximate calendar-day span used to size the interval.
PERIOD_CHOICES = [
    ("5d", "Settimana", 7),
    ("1mo", "Mese", 30),
    ("3mo", "3 mesi", 91),
    ("6mo", "6 mesi", 182),
    ("1y", "1 anno", 365),
    ("2y", "2 anni", 730),
    ("5y", "5 anni", 1825),
]

INTERVAL_LABELS = {
    "1mo": "1 mese",
    "1wk": "1 settimana",
    "1d": "1 giorno",
    "60m": "1 ora",
    "30m": "30 minuti",
    "15m": "15 minuti",
    "5m": "5 minuti",
    "2m": "2 minuti",
    "1m": "1 minuto",
}

# Coarsest-to-finest. Bars-per-trading-day is approximate (6.5h session).
_INTERVAL_ORDER = ["1mo", "1wk", "1d", "60m", "30m", "15m", "5m", "2m", "1m"]
_BARS_PER_TRADING_DAY = {
    "1mo": 1 / 21,
    "1wk": 1 / 5,
    "1d": 1,
    "60m": 7,
    "30m": 13,
    "15m": 26,
    "5m": 78,
    "2m": 195,
    "1m": 390,
}
# Yahoo Finance's max lookback per intraday interval (calendar days).
# None means there's no practical limit for our period choices.
_INTERVAL_MAX_DAYS = {
    "1mo": None,
    "1wk": None,
    "1d": None,
    "60m": 730,
    "30m": 60,
    "15m": 60,
    "5m": 60,
    "2m": 60,
    "1m": 7,
}


def estimated_bars(calendar_days: int, interval: str) -> float:
    """Rough count of candles a period spanning `calendar_days` yields at `interval`."""
    trading_days = calendar_days * 5 / 7
    return trading_days * _BARS_PER_TRADING_DAY[interval]


def valid_intervals(calendar_days: int) -> list[str]:
    """Intervals (coarsest first) that both fit Yahoo's lookback limit and
    yield at least MIN_BARS candles for a period of `calendar_days`."""
    valid = []
    for interval in _INTERVAL_ORDER:
        max_days = _INTERVAL_MAX_DAYS[interval]
        if max_days is not None and calendar_days > max_days:
            continue
        if estimated_bars(calendar_days, interval) >= MIN_BARS:
            valid.append(interval)
    return valid


def default_interval(calendar_days: int) -> str:
    """Pick "1d" when it already satisfies MIN_BARS, otherwise the coarsest
    intraday interval that does (finer periods need finer candles)."""
    options = valid_intervals(calendar_days)
    if not options:
        return _INTERVAL_ORDER[-1]  # finest available, best effort
    if "1d" in options:
        return "1d"
    intraday = [i for i in options if i not in ("1mo", "1wk")]
    return intraday[0] if intraday else options[0]


def search_candidates(query: str, max_results: int = 8) -> list[dict]:
    """Look up tickers matching `query` (name or partial symbol) on Yahoo Finance.

    Returns a list of {"symbol", "name", "exchange"} dicts, best match first.
    A plain ticker like "eni" often has no exact Yahoo symbol (the Italian
    listing is "ENI.MI") so this is what lets the caller offer the user a
    pick-list instead of guessing a single, possibly wrong, symbol.
    """
    query = query.strip()
    if not query:
        return []

    try:
        quotes = yf.Search(query, max_results=max_results, raise_errors=False).quotes
    except Exception:
        return []

    candidates = []
    for quote in quotes:
        symbol = quote.get("symbol")
        if not symbol:
            continue
        name = quote.get("shortname") or quote.get("longname") or symbol
        exchange = quote.get("exchDisp") or quote.get("exchange") or ""
        candidates.append({"symbol": symbol, "name": name, "exchange": exchange})
    return candidates


def resolve_ticker(query: str) -> tuple[str, str]:
    """Resolve a ticker symbol or company name to (symbol, display_name).

    Runs a Yahoo Finance symbol search first so a company name (e.g.
    "Apple") works alongside an exact ticker (e.g. "AAPL"). Falls back to
    treating the query itself as a ticker if the search finds nothing or
    the network call fails. Prefer `search_candidates` + explicit user
    choice when several tickers could plausibly match (e.g. "eni" matches
    both "ENI.MI" and "E" on the NYSE) since this only ever returns the
    top hit.
    """
    query = query.strip()
    if not query:
        raise ValueError("Ticker o nome azienda mancante.")

    candidates = search_candidates(query, max_results=5)
    if candidates:
        return candidates[0]["symbol"], candidates[0]["name"]

    return query.upper(), query.upper()


def fetch_ohlcv(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """Fetch OHLCV history for a ticker, with lower-case single-level columns."""
    raw = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False)
    if raw.empty:
        raise ValueError(f"Nessun dato trovato per il ticker '{ticker}'")

    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    df = raw.rename(columns=str.lower)

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Dati incompleti per '{ticker}': mancano le colonne {missing}")

    return df[REQUIRED_COLUMNS]
