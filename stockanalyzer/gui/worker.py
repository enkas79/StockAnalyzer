from PySide6.QtCore import QThread, Signal

from ..data import fetch_ohlcv, resolve_ticker, search_candidates
from ..engine import analyze


class SearchWorker(QThread):
    """Looks up ticker candidates for a query off the UI thread."""

    found = Signal(str, list)

    def __init__(self, query: str, parent=None):
        super().__init__(parent)
        self.query = query

    def run(self):
        candidates = search_candidates(self.query)
        self.found.emit(self.query, candidates)


class AnalysisWorker(QThread):
    """Runs the network fetch + rule engine off the UI thread."""

    succeeded = Signal(object, str, str, object)  # AnalysisResult, symbol, name, OHLCV DataFrame
    failed = Signal(str)

    def __init__(
        self,
        query: str,
        period: str,
        interval: str,
        resolved: tuple[str, str] | None = None,
        extra_legs: frozenset[str] = frozenset(),
        parent=None,
    ):
        super().__init__(parent)
        self.query = query
        self.period = period
        self.interval = interval
        self.resolved = resolved  # (symbol, name) if already picked from the search list
        self.extra_legs = extra_legs

    def run(self):
        try:
            symbol, name = self.resolved if self.resolved else resolve_ticker(self.query)
            df = fetch_ohlcv(symbol, period=self.period, interval=self.interval)
            result = analyze(df, extra_legs=self.extra_legs)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(result, symbol, name, df)


class WatchlistWorker(QThread):
    """Runs resolve+fetch+analyze for a list of tickers, one at a time, off the UI thread."""

    item_done = Signal(str, str, object, str)  # query, name (or query on error), AnalysisResult|None, error

    def __init__(
        self,
        queries: list[str],
        period: str,
        interval: str,
        extra_legs: frozenset[str] = frozenset(),
        parent=None,
    ):
        super().__init__(parent)
        self.queries = queries
        self.period = period
        self.interval = interval
        self.extra_legs = extra_legs

    def run(self):
        for query in self.queries:
            try:
                symbol, name = resolve_ticker(query)
                df = fetch_ohlcv(symbol, period=self.period, interval=self.interval)
                result = analyze(df, extra_legs=self.extra_legs)
            except Exception as exc:  # noqa: BLE001 - keep going with the rest of the watchlist
                self.item_done.emit(query, query, None, str(exc))
                continue
            self.item_done.emit(symbol, name, result, "")
