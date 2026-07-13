from stockanalyzer.risk import position_size


def test_position_size_basic():
    # 10000 account, 1% risk = 100 risk budget, stop distance 2.0 -> 50 shares
    result = position_size(account_size=10_000, risk_pct=1, stop_distance=2.0, price=50.0)
    assert result.shares == 50
    assert result.risk_amount == 100.0
    assert result.position_value == 2500.0


def test_position_size_floors_to_whole_shares():
    result = position_size(account_size=1_000, risk_pct=1, stop_distance=3.0, price=10.0)
    # risk budget 10, stop distance 3 -> 3.33 shares, floored to 3
    assert result.shares == 3


def test_position_size_zero_on_invalid_inputs():
    assert position_size(0, 1, 2.0, 50.0).shares == 0
    assert position_size(10_000, 0, 2.0, 50.0).shares == 0
    assert position_size(10_000, 1, 0, 50.0).shares == 0
    assert position_size(10_000, 1, 2.0, 0).shares == 0
