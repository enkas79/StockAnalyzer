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
- **Leg opzionali** (disattivati di default) — MACD e Bollinger Bands, per chi
  vuole affinare la conferma; il punteggio si rinormalizza automaticamente
  quando li attivi, quindi il punteggio a 3 leg di default resta invariato.

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

`fetch_ohlcv` prova prima Yahoo Finance, poi ripiega su Stooq (solo
dati giornalieri/settimanali/mensili) se Yahoo non ha dati per il
ticker, e tiene una cache su disco di 15 minuti per evitare richieste
di rete ripetute sullo stesso ticker/periodo/intervallo.

## CLI

```bash
stockanalyzer-cli AAPL --period 1y --interval 1d
stockanalyzer-cli eni.mi --macd --bollinger --account-size 10000 --risk-pct 1
```

Stampa direzione, punteggio, dettaglio dei leg, rischio (ATR/stop) e,
se richiesto con `--account-size`, la size di posizione suggerita.

## Backtest

```python
from stockanalyzer.backtest import run_backtest

result = run_backtest(df, forward_bars=10, step=5)
print(result.hit_rate, result.avg_forward_return)
```

Fa scorrere `analyze()` su una finestra crescente della storia e
confronta ogni chiamata direzionale con il rendimento realizzato
`forward_bars` candele dopo — un controllo di coerenza, non un
simulatore di trading (nessun costo/slippage/size).

## GUI (Qt6 / PySide6)

```bash
pip install -e .
python main.py
# oppure, dopo l'installazione: stockanalyzer-gui
```

La finestra si apre massimizzata, adattandosi alla risoluzione dello
schermo. Il menu **Visualizza** permette di scegliere tra tema chiaro e
tema scuro: la scelta viene ricordata tra un avvio e l'altro.

La finestra è divisa in tre schede:

- **Analisi** — Nel campo di ricerca puoi inserire un ticker (`AAPL`) oppure
  il nome dell'azienda (`Eni`): dopo un paio di lettere compare un elenco
  di aziende corrispondenti con simbolo e borsa (es. `ENI.MI` — Eni S.p.A.,
  Milan) da cui scegliere quella giusta. Il periodo va da una settimana a
  5 anni; l'elenco degli intervalli disponibili si aggiorna in base al
  periodo scelto in modo da garantire sempre almeno 200 candele (necessarie
  per l'EMA200) — per i periodi più corti (settimana, mese, 3/6 mesi)
  vengono proposti solo intervalli intraday (es. 5m, 30m, 1h), mentre per
  1 anno o più resta disponibile anche il giornaliero. Premi "Analizza": la
  GUI mostra direzione, punteggio di confidenza, il dettaglio dei leg
  (colorati per stato), prezzo/ATR/stop suggerito e, inserendo capitale e
  rischio % per trade, la size di posizione suggerita.
- **Grafico** — prezzo con EMA50/EMA200 e RSI(14) con soglie di
  ipercomprato/ipervenduto, per il ticker appena analizzato.
- **Watchlist** — una lista di ticker salvata tra le sessioni: "Analizza
  tutti" li scarica e valuta uno alla volta su un thread separato,
  popolando una tabella ordinabile con direzione/confidenza/conferme (le
  righe in errore restano visibili invece di interrompere il resto).

Ticker, periodo, intervallo, watchlist e tema vengono ricordati tra un
avvio e l'altro. Il fetch dati e il calcolo girano sempre su un thread
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
