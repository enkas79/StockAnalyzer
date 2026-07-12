# StockAnalyzer

Motore di trend-confirmation basato su regole. Invece di un segnale binario
buy/sell/hold, restituisce un punteggio di confidenza (0-100) e un conteggio
di conferme, così i casi ambigui restano visibili.

## Logica

- **Trend primario** — EMA 50/200 (crossover + posizione del prezzo). È
  l'unico leg che stabilisce una direzione; gli altri confermano, restano
  neutri o mettono veto.
- **Momentum** — RSI(14) usato come filtro, non come trigger: conferma il
  trend attivo, resta neutro, o mette veto quando il trend è già esteso
  in ipercomprato/ipervenduto.
- **Volume** — volume relativo alla media a 20 giorni: un movimento senza
  supporto di volume viene segnalato come a rischio.
- **Rischio** — ATR(14), escluso dal conteggio delle conferme: fornisce solo
  la distanza suggerita per lo stop-loss.

## Uso

```python
from stockanalyzer import fetch_ohlcv, analyze

df = fetch_ohlcv("AAPL", period="1y", interval="1d")
result = analyze(df)

print(result.direction)        # "bullish" | "bearish" | "neutral"
print(result.score)            # 0-100
print(f"{result.confirmations}/{result.total_legs}")
for leg in result.legs:
    print(leg.name, leg.state, leg.detail)
```

## Sviluppo

```bash
pip install -e ".[dev]"
pytest
```
