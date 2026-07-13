"""Rolls the rule engine over history to check its calls against realized returns.

This is a sanity check, not a trading simulator: no costs, slippage, or
position sizing are modeled. It only asks "when the engine called a
direction, did price move that way over the next `forward_bars` bars?".
"""

from dataclasses import dataclass, field

import pandas as pd

from .engine import MIN_BARS, analyze

SCORE_BUCKETS = ["0-33", "34-66", "67-100"]


@dataclass
class BucketStats:
    samples: int
    hit_rate: float
    avg_forward_return: float


@dataclass
class BacktestResult:
    samples: int
    hit_rate: float
    avg_forward_return: float
    by_score_bucket: dict[str, BucketStats] = field(default_factory=dict)


def _score_bucket(score: float) -> str:
    if score < 34:
        return "0-33"
    if score < 67:
        return "34-66"
    return "67-100"


def _safe_mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def run_backtest(
    df: pd.DataFrame,
    forward_bars: int = 10,
    step: int = 5,
    extra_legs: frozenset[str] = frozenset(),
) -> BacktestResult:
    """Step through `df` with an expanding window, score each point with
    `analyze`, and compare the call against the realized close-to-close
    return `forward_bars` later. Only "bullish"/"bearish" calls count
    towards hit-rate ("neutral" makes no directional claim to test).
    """
    min_required = MIN_BARS + forward_bars + 1
    if len(df) < min_required:
        raise ValueError(f"Servono almeno {min_required} barre per il backtest, ricevute {len(df)}.")

    close = df["close"]
    signed_returns: list[float] = []
    hits: list[bool] = []
    bucket_returns: dict[str, list[float]] = {b: [] for b in SCORE_BUCKETS}
    bucket_hits: dict[str, list[bool]] = {b: [] for b in SCORE_BUCKETS}

    last_end = len(df) - forward_bars
    for end in range(MIN_BARS, last_end, step):
        window = df.iloc[:end]
        result = analyze(window, extra_legs=extra_legs)
        if result.direction == "neutral":
            continue

        today_close = close.iloc[end - 1]
        future_close = close.iloc[end - 1 + forward_bars]
        forward_return = (future_close - today_close) / today_close
        signed_return = forward_return if result.direction == "bullish" else -forward_return
        hit = signed_return > 0

        signed_returns.append(signed_return)
        hits.append(hit)
        bucket = _score_bucket(result.score)
        bucket_returns[bucket].append(signed_return)
        bucket_hits[bucket].append(hit)

    by_score_bucket = {
        bucket: BucketStats(
            samples=len(bucket_returns[bucket]),
            hit_rate=_safe_mean([float(h) for h in bucket_hits[bucket]]),
            avg_forward_return=_safe_mean(bucket_returns[bucket]),
        )
        for bucket in SCORE_BUCKETS
    }

    return BacktestResult(
        samples=len(signed_returns),
        hit_rate=_safe_mean([float(h) for h in hits]),
        avg_forward_return=_safe_mean(signed_returns),
        by_score_bucket=by_score_bucket,
    )
