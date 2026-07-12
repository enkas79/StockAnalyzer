"""OHLCV data fetching via Yahoo Finance."""

import pandas as pd
import yfinance as yf

REQUIRED_COLUMNS = ["open", "high", "low", "close", "volume"]


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
