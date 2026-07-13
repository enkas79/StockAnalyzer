import numpy as np
import pandas as pd
import pytest

from stockanalyzer.backtest import run_backtest
from stockanalyzer.engine import MIN_BARS


def _make_df(close: np.ndarray, volume: np.ndarray) -> pd.DataFrame:
    dates = pd.date_range("2023-01-01", periods=len(close), freq="B")
    high = close * 1.01
    low = close * 0.99
    return pd.DataFrame(
        {"open": close, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


def test_run_backtest_raises_on_insufficient_history():
    df = _make_df(np.full(210, 100.0), np.full(210, 1000.0))
    with pytest.raises(ValueError):
        run_backtest(df, forward_bars=10)


def test_run_backtest_high_hit_rate_on_clean_uptrend():
    n = MIN_BARS + 100
    t = np.arange(n)
    close = 100 + 0.5 * t
    volume = np.full(n, 1000.0)
    df = _make_df(close, volume)

    result = run_backtest(df, forward_bars=5, step=5)

    assert result.samples > 0
    assert result.hit_rate > 0.9
    assert result.avg_forward_return > 0


def test_run_backtest_returns_score_buckets():
    n = MIN_BARS + 100
    t = np.arange(n)
    close = 100 + 0.5 * t + 3 * np.sin(t / 5.0)
    volume = np.full(n, 1000.0)
    df = _make_df(close, volume)

    result = run_backtest(df, forward_bars=5, step=5)

    assert set(result.by_score_bucket) == {"0-33", "34-66", "67-100"}
    total_bucketed = sum(b.samples for b in result.by_score_bucket.values())
    assert total_bucketed == result.samples
