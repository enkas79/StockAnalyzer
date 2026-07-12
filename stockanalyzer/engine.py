"""Rule engine that scores trend confirmation instead of emitting a binary signal.

Design (see project discussion):
- EMA 50/200 sets the primary trend direction. It is the only leg that can
  establish a direction; the others only confirm, stay neutral, or veto it.
- RSI(14) is a filter, not a trigger: it never proposes a direction on its
  own. It confirms the active trend, stays neutral, or vetoes it when the
  trend is already stretched into overbought/oversold territory.
- Relative volume (vs. its 20-day average) is the fourth, largely
  independent leg: a trend/breakout without volume support is flagged.
- ATR(14) is deliberately excluded from the confirmation count. It is a
  risk-sizing input (stop-loss distance), not a directional vote.

The output is a confidence score (0-100) and a confirmations count
(e.g. "2/3"), not a buy/sell/hold verdict, so ambiguous cases stay visible
instead of being collapsed into a false-certain answer.
"""

from dataclasses import dataclass, field

import pandas as pd

from . import indicators

TREND_WEIGHT = 0.5
MOMENTUM_WEIGHT = 0.25
VOLUME_WEIGHT = 0.25

RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
RELATIVE_VOLUME_CONFIRM = 1.2
RELATIVE_VOLUME_VETO = 0.7
FLAT_TREND_THRESHOLD = 0.001  # relative EMA50/EMA200 spread below this = no trend

LEG_STATE_SCORE = {"confirm": 1.0, "neutral": 0.5, "veto": 0.0}

MIN_BARS = 200


@dataclass
class Leg:
    name: str
    state: str  # "confirm" | "neutral" | "veto"
    detail: str


@dataclass
class AnalysisResult:
    direction: str  # "bullish" | "bearish" | "neutral"
    score: float  # 0-100 confidence in `direction`
    confirmations: int
    total_legs: int
    legs: list[Leg] = field(default_factory=list)
    price: float = 0.0
    ema50: float = 0.0
    ema200: float = 0.0
    rsi: float = 0.0
    relative_volume: float = 0.0
    atr: float = 0.0
    suggested_stop_distance: float = 0.0


def _trend_leg(price: float, ema50: float, ema200: float) -> tuple[str, Leg]:
    spread = (ema50 - ema200) / ema200

    if abs(spread) < FLAT_TREND_THRESHOLD:
        return "neutral", Leg(
            "trend", "neutral", "EMA50 ed EMA200 sono troppo vicine: nessun trend primario."
        )

    if spread > 0:
        direction = "bullish"
        if price > ema50:
            return direction, Leg(
                "trend", "confirm", "EMA50 > EMA200 e prezzo sopra EMA50: trend rialzista attivo."
            )
        return direction, Leg(
            "trend", "neutral", "EMA50 > EMA200 ma prezzo sotto EMA50: trend rialzista in pausa/pullback."
        )

    direction = "bearish"
    if price < ema50:
        return direction, Leg(
            "trend", "confirm", "EMA50 < EMA200 e prezzo sotto EMA50: trend ribassista attivo."
        )
    return direction, Leg(
        "trend", "neutral", "EMA50 < EMA200 ma prezzo sopra EMA50: trend ribassista in pausa/rimbalzo."
    )


def _momentum_leg(direction: str, rsi_value: float) -> Leg:
    if direction == "neutral":
        return Leg("momentum", "neutral", "Nessun trend primario da confermare con RSI.")

    if direction == "bullish":
        if rsi_value >= RSI_OVERBOUGHT:
            return Leg(
                "momentum", "veto",
                f"RSI {rsi_value:.1f} ipercomprato in trend rialzista: rischio pullback, non aggiungere long qui.",
            )
        if rsi_value > 50:
            return Leg(
                "momentum", "confirm",
                f"RSI {rsi_value:.1f} conferma la direzione senza essere in zona estrema.",
            )
        return Leg("momentum", "neutral", f"RSI {rsi_value:.1f} non conferma né nega il trend.")

    if rsi_value <= RSI_OVERSOLD:
        return Leg(
            "momentum", "veto",
            f"RSI {rsi_value:.1f} ipervenduto in trend ribassista: rischio rimbalzo, non aggiungere short qui.",
        )
    if rsi_value < 50:
        return Leg(
            "momentum", "confirm",
            f"RSI {rsi_value:.1f} conferma la direzione senza essere in zona estrema.",
        )
    return Leg("momentum", "neutral", f"RSI {rsi_value:.1f} non conferma né nega il trend.")


def _volume_leg(direction: str, rel_volume: float) -> Leg:
    if direction == "neutral" or pd.isna(rel_volume):
        return Leg("volume", "neutral", "Nessun trend primario, o volume medio non ancora disponibile.")

    if rel_volume >= RELATIVE_VOLUME_CONFIRM:
        return Leg(
            "volume", "confirm",
            f"Volume {rel_volume:.2f}x la media a 20 giorni: il movimento è supportato.",
        )
    if rel_volume <= RELATIVE_VOLUME_VETO:
        return Leg(
            "volume", "veto",
            f"Volume {rel_volume:.2f}x la media a 20 giorni: movimento non supportato, alto rischio di falso segnale.",
        )
    return Leg("volume", "neutral", f"Volume {rel_volume:.2f}x la media a 20 giorni: nella norma.")


def analyze(df: pd.DataFrame, atr_stop_multiplier: float = 1.5) -> AnalysisResult:
    """Score how well momentum and volume confirm the EMA50/200 trend.

    `df` must have lower-case columns open/high/low/close/volume, sorted by
    date ascending, with at least MIN_BARS rows.
    """
    if len(df) < MIN_BARS:
        raise ValueError(
            f"Servono almeno {MIN_BARS} barre per calcolare EMA200 in modo affidabile, "
            f"ricevute {len(df)}."
        )

    ema50 = indicators.ema(df["close"], 50)
    ema200 = indicators.ema(df["close"], 200)
    rsi14 = indicators.rsi(df["close"], 14)
    atr14 = indicators.atr(df["high"], df["low"], df["close"], 14)
    rel_vol = indicators.relative_volume(df["volume"], 20)

    price = float(df["close"].iloc[-1])
    ema50_last = float(ema50.iloc[-1])
    ema200_last = float(ema200.iloc[-1])
    rsi_last = float(rsi14.iloc[-1])
    atr_last = float(atr14.iloc[-1])
    rel_vol_last = float(rel_vol.iloc[-1]) if not pd.isna(rel_vol.iloc[-1]) else float("nan")

    direction, trend_leg = _trend_leg(price, ema50_last, ema200_last)
    momentum_leg = _momentum_leg(direction, rsi_last)
    volume_leg = _volume_leg(direction, rel_vol_last)

    legs = [trend_leg, momentum_leg, volume_leg]
    weights = {"trend": TREND_WEIGHT, "momentum": MOMENTUM_WEIGHT, "volume": VOLUME_WEIGHT}
    score = 100 * sum(weights[leg.name] * LEG_STATE_SCORE[leg.state] for leg in legs)
    confirmations = sum(1 for leg in legs if leg.state == "confirm")

    return AnalysisResult(
        direction=direction,
        score=round(score, 1),
        confirmations=confirmations,
        total_legs=len(legs),
        legs=legs,
        price=price,
        ema50=ema50_last,
        ema200=ema200_last,
        rsi=rsi_last,
        relative_volume=rel_vol_last,
        atr=atr_last,
        suggested_stop_distance=round(atr_last * atr_stop_multiplier, 4),
    )
