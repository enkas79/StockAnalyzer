from unittest.mock import patch

import pandas as pd
import pytest

from stockanalyzer import data

_STOOQ_CSV = (
    "Date,Open,High,Low,Close,Volume\n"
    "2024-01-01,10,11,9,10.5,1000\n"
    "2024-01-02,10.5,11.5,9.5,11,1200\n"
)


def _yahoo_df():
    dates = pd.date_range("2024-01-01", periods=3)
    return pd.DataFrame(
        {
            "Open": [1.0, 2.0, 3.0],
            "High": [1.5, 2.5, 3.5],
            "Low": [0.5, 1.5, 2.5],
            "Close": [1.2, 2.2, 3.2],
            "Volume": [100, 200, 300],
        },
        index=dates,
    )


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("STOCKANALYZER_CACHE_DIR", str(tmp_path))


def test_fetch_ohlcv_uses_yahoo_when_available():
    with patch("stockanalyzer.data.yf.download", return_value=_yahoo_df()) as mock_download:
        df = data.fetch_ohlcv("AAPL", period="1y", interval="1d")

    mock_download.assert_called_once()
    assert list(df.columns) == data.REQUIRED_COLUMNS
    assert len(df) == 3


def test_fetch_ohlcv_serves_from_cache_on_second_call():
    with patch("stockanalyzer.data.yf.download", return_value=_yahoo_df()) as mock_download:
        data.fetch_ohlcv("AAPL", period="1y", interval="1d")
        data.fetch_ohlcv("AAPL", period="1y", interval="1d")

    mock_download.assert_called_once()  # second call hit the cache, not the network


def test_fetch_ohlcv_refetches_after_cache_expires():
    with patch("stockanalyzer.data.yf.download", return_value=_yahoo_df()) as mock_download:
        df = data.fetch_ohlcv("AAPL", period="1y", interval="1d")
        cache_path = data._cache_path("AAPL", "1y", "1d")
        # Backdate the cache file past the TTL instead of sleeping in the test.
        old_time = cache_path.stat().st_mtime - data.CACHE_TTL_SECONDS - 1
        import os

        os.utime(cache_path, (old_time, old_time))

        data.fetch_ohlcv("AAPL", period="1y", interval="1d")

    assert mock_download.call_count == 2


def test_fetch_ohlcv_bypasses_cache_when_disabled():
    with patch("stockanalyzer.data.yf.download", return_value=_yahoo_df()) as mock_download:
        data.fetch_ohlcv("AAPL", period="1y", interval="1d", use_cache=False)
        data.fetch_ohlcv("AAPL", period="1y", interval="1d", use_cache=False)

    assert mock_download.call_count == 2


def test_fetch_ohlcv_falls_back_to_stooq_when_yahoo_empty():
    with (
        patch("stockanalyzer.data.yf.download", return_value=pd.DataFrame()),
        patch("stockanalyzer.data._download_stooq_csv", return_value=_STOOQ_CSV) as mock_stooq,
    ):
        df = data.fetch_ohlcv("ENI.MI", period="1y", interval="1d")

    mock_stooq.assert_called_once()
    assert list(df.columns) == data.REQUIRED_COLUMNS
    assert len(df) == 2


def test_fetch_ohlcv_raises_combined_error_when_both_sources_fail():
    with (
        patch("stockanalyzer.data.yf.download", side_effect=RuntimeError("yahoo down")),
        patch("stockanalyzer.data._download_stooq_csv", side_effect=RuntimeError("stooq down")),
    ):
        with pytest.raises(ValueError) as exc_info:
            data.fetch_ohlcv("NOPE", period="1y", interval="1d")

    assert "Yahoo Finance" in str(exc_info.value)
    assert "Stooq" in str(exc_info.value)


def test_stooq_fallback_declines_intraday_intervals():
    with (
        patch("stockanalyzer.data.yf.download", side_effect=RuntimeError("yahoo down")),
    ):
        with pytest.raises(ValueError) as exc_info:
            data.fetch_ohlcv("AAPL", period="5d", interval="5m")

    assert "Stooq" in str(exc_info.value)
