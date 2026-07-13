import numpy as np
import pandas as pd
import pytest

from stockanalyzer import indicators


def test_ema_converges_to_constant_series():
    close = pd.Series([10.0] * 60)
    result = indicators.ema(close, 20)
    assert result.iloc[-1] == 10.0


def test_rsi_is_100_for_pure_uptrend():
    close = pd.Series(np.arange(1, 40, dtype=float))
    result = indicators.rsi(close, 14)
    assert result.iloc[-1] == 100.0


def test_rsi_is_0_for_pure_downtrend():
    close = pd.Series(np.arange(40, 1, -1, dtype=float))
    result = indicators.rsi(close, 14)
    assert result.iloc[-1] == 0.0


def test_rsi_stays_within_bounds_for_noisy_series():
    rng = np.random.default_rng(42)
    close = pd.Series(100 + np.cumsum(rng.normal(0, 1, 200)))
    result = indicators.rsi(close, 14).dropna()
    assert (result >= 0).all() and (result <= 100).all()


def test_atr_is_non_negative():
    rng = np.random.default_rng(1)
    close = pd.Series(100 + np.cumsum(rng.normal(0, 1, 100)))
    high = close + rng.uniform(0, 2, 100)
    low = close - rng.uniform(0, 2, 100)
    result = indicators.atr(high, low, close, 14).dropna()
    assert (result >= 0).all()


def test_obv_accumulates_on_up_days_and_subtracts_on_down_days():
    close = pd.Series([10, 11, 10, 12])
    volume = pd.Series([100, 200, 150, 300])
    result = indicators.obv(close, volume)
    # day0: no prior day -> diff NaN -> sign 0 -> obv=0
    # day1: up -> +200 -> obv=200
    # day2: down -> -150 -> obv=50
    # day3: up -> +300 -> obv=350
    assert result.tolist() == [0, 200, 50, 350]


def test_relative_volume_above_one_when_above_average():
    volume = pd.Series([100] * 19 + [200])
    result = indicators.relative_volume(volume, period=20)
    assert result.iloc[-1] == pytest.approx(200 / 105)


def test_macd_line_is_zero_for_constant_series():
    close = pd.Series([10.0] * 60)
    macd_line, signal_line, histogram = indicators.macd(close)
    assert macd_line.iloc[-1] == pytest.approx(0.0)
    assert signal_line.iloc[-1] == pytest.approx(0.0)
    assert histogram.iloc[-1] == pytest.approx(0.0)


def test_macd_line_is_positive_in_sustained_uptrend():
    close = pd.Series(np.arange(1, 100, dtype=float))
    macd_line, _signal_line, _histogram = indicators.macd(close)
    assert macd_line.iloc[-1] > 0


def test_bollinger_bands_bracket_a_noisy_series():
    rng = np.random.default_rng(7)
    close = pd.Series(100 + np.cumsum(rng.normal(0, 1, 100)))
    middle, upper, lower = indicators.bollinger_bands(close, period=20)
    valid = middle.notna()
    assert (upper[valid] >= middle[valid]).all()
    assert (lower[valid] <= middle[valid]).all()


def test_bollinger_bands_collapse_to_price_for_constant_series():
    close = pd.Series([50.0] * 40)
    middle, upper, lower = indicators.bollinger_bands(close, period=20)
    assert middle.iloc[-1] == pytest.approx(50.0)
    assert upper.iloc[-1] == pytest.approx(50.0)
    assert lower.iloc[-1] == pytest.approx(50.0)
