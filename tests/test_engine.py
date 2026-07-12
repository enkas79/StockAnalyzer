import numpy as np
import pandas as pd
import pytest

from stockanalyzer.engine import MIN_BARS, analyze


def _make_df(close: np.ndarray, volume: np.ndarray) -> pd.DataFrame:
    dates = pd.date_range("2023-01-01", periods=len(close), freq="B")
    high = close * 1.01
    low = close * 0.99
    return pd.DataFrame(
        {"open": close, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


def test_analyze_raises_on_insufficient_history():
    df = _make_df(np.full(50, 100.0), np.full(50, 1000.0))
    with pytest.raises(ValueError):
        analyze(df)


def test_bullish_trend_with_volume_support_scores_high():
    t = np.arange(250)
    close = 100 + 0.3 * t + 3 * np.sin(t / 5.0)
    volume = np.full(250, 1000.0)
    volume[-5:] = 2000.0  # recent volume spike above the 20d average
    df = _make_df(close, volume)

    result = analyze(df)

    assert result.direction == "bullish"
    assert result.score > 50
    leg_states = {leg.name: leg.state for leg in result.legs}
    assert leg_states["trend"] == "confirm"
    assert leg_states["volume"] == "confirm"


def test_bearish_trend_with_thin_volume_scores_low():
    t = np.arange(250)
    close = 300 - 0.3 * t + 3 * np.sin(t / 5.0)
    volume = np.full(250, 1000.0)
    volume[-5:] = 400.0  # move not supported by volume
    df = _make_df(close, volume)

    result = analyze(df)

    assert result.direction == "bearish"
    leg_states = {leg.name: leg.state for leg in result.legs}
    assert leg_states["trend"] == "confirm"
    assert leg_states["volume"] == "veto"
    assert result.score < 75


def test_flat_series_has_no_trend():
    close = np.full(250, 100.0)
    volume = np.full(250, 1000.0)
    df = _make_df(close, volume)

    result = analyze(df)

    assert result.direction == "neutral"
    assert result.confirmations == 0


def test_overbought_rsi_vetoes_momentum_in_uptrend():
    t = np.arange(250)
    # Monotonic ramp: strong enough uptrend to push RSI(14) to the overbought zone.
    close = 100 + 1.0 * t
    volume = np.full(250, 1000.0)
    df = _make_df(close, volume)

    result = analyze(df)

    assert result.direction == "bullish"
    leg_states = {leg.name: leg.state for leg in result.legs}
    assert leg_states["momentum"] == "veto"


def test_suggested_stop_distance_scales_with_atr():
    t = np.arange(250)
    close = 100 + 0.3 * t + 3 * np.sin(t / 5.0)
    volume = np.full(250, 1000.0)
    df = _make_df(close, volume)

    result = analyze(df, atr_stop_multiplier=2.0)

    assert result.suggested_stop_distance == pytest.approx(result.atr * 2.0, abs=1e-3)
