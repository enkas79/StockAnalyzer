from stockanalyzer.data import MIN_BARS, PERIOD_CHOICES, default_interval, estimated_bars, valid_intervals


def test_every_period_choice_has_a_valid_default_interval():
    for _code, _label, days in PERIOD_CHOICES:
        interval = default_interval(days)
        assert estimated_bars(days, interval) >= MIN_BARS


def test_long_periods_keep_daily_candles_as_default():
    for code, _label, days in PERIOD_CHOICES:
        if code in ("1y", "2y"):
            assert default_interval(days) == "1d"


def test_short_periods_fall_back_to_intraday_candles():
    for code, _label, days in PERIOD_CHOICES:
        if code in ("5d", "1mo", "3mo", "6mo"):
            assert default_interval(days) != "1d"


def test_valid_intervals_are_sorted_coarsest_first():
    for _code, _label, days in PERIOD_CHOICES:
        options = valid_intervals(days)
        for interval in options:
            assert estimated_bars(days, interval) >= MIN_BARS
