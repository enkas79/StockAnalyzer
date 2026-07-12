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

## GUI (Qt6 / PySide6)

```bash
pip install -e .
python main.py
# oppure, dopo l'installazione: stockanalyzer-gui
```

Nel campo di ricerca puoi inserire un ticker (`AAPL`) oppure il nome
dell'azienda (`Apple`): il simbolo viene risolto automaticamente prima di
scaricare i dati. Scegli periodo/intervallo e premi "Analizza": la GUI
mostra direzione, punteggio di confidenza, il dettaglio dei tre leg
(trend/momentum/volume, colorati per stato) e la distanza di stop
suggerita dall'ATR. Il fetch dati e il calcolo girano su un thread
separato per non bloccare l'interfaccia. Il menu **Aiuto** contiene la
guida all'uso e le informazioni sulla versione del programma.

## Versione e pacchetti di installazione

La versione corrente è in [`version.txt`](version.txt) ed è la fonte
unica usata sia dal pacchetto Python (`pyproject.toml`, versione
dinamica) sia dalla GUI (mostrata in Aiuto → Informazioni). Ad ogni push
su `main` che modifica `version.txt`, il workflow
[`.github/workflows/build-installers.yml`](.github/workflows/build-installers.yml)
genera automaticamente l'installer Windows (`.exe`), il pacchetto macOS
(`.dmg`) e il pacchetto Debian/Ubuntu (`.deb`), e li allega a una GitHub
Release taggata `vX.Y.Z`.

## Sviluppo

```bash
pip install -e ".[dev]"
pytest
```
