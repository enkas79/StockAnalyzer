"""Position sizing based on account risk, independent of the trend engine."""

from dataclasses import dataclass


@dataclass
class PositionSize:
    shares: int
    risk_amount: float
    position_value: float


def position_size(account_size: float, risk_pct: float, stop_distance: float, price: float) -> PositionSize:
    """Shares to buy/sell so a stop at `stop_distance` loses at most `risk_pct`
    of `account_size`.

    `stop_distance` is typically `AnalysisResult.suggested_stop_distance`
    (ATR-based). Returns zero shares if any input can't produce a sizing
    (e.g. no real stop distance).
    """
    if account_size <= 0 or risk_pct <= 0 or stop_distance <= 0 or price <= 0:
        return PositionSize(shares=0, risk_amount=0.0, position_value=0.0)

    risk_amount = account_size * (risk_pct / 100)
    shares = int(risk_amount // stop_distance)
    return PositionSize(shares=shares, risk_amount=risk_amount, position_value=shares * price)
