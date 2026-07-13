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

    succeeded = Signal(object, str, str)
    failed = Signal(str)

    def __init__(
        self,
        query: str,
        period: str,
        interval: str,
        resolved: tuple[str, str] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.query = query
        self.period = period
        self.interval = interval
        self.resolved = resolved  # (symbol, name) if already picked from the search list

    def run(self):
        try:
            symbol, name = self.resolved if self.resolved else resolve_ticker(self.query)
            df = fetch_ohlcv(symbol, period=self.period, interval=self.interval)
            result = analyze(df)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(result, symbol, name)
