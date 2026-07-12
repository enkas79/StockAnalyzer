from PySide6.QtCore import QThread, Signal

from ..data import fetch_ohlcv
from ..engine import analyze


class AnalysisWorker(QThread):
    """Runs the network fetch + rule engine off the UI thread."""

    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, ticker: str, period: str, interval: str, parent=None):
        super().__init__(parent)
        self.ticker = ticker
        self.period = period
        self.interval = interval

    def run(self):
        try:
            df = fetch_ohlcv(self.ticker, period=self.period, interval=self.interval)
            result = analyze(df)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(result)
