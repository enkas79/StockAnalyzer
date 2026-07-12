import sys

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..engine import AnalysisResult
from .worker import AnalysisWorker

LEG_COLORS = {
    "confirm": QColor("#2e7d32"),
    "neutral": QColor("#757575"),
    "veto": QColor("#c62828"),
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StockAnalyzer")
        self.resize(720, 520)
        self._worker: AnalysisWorker | None = None
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        form_row = QHBoxLayout()
        self.ticker_input = QLineEdit()
        self.ticker_input.setPlaceholderText("Ticker, es. AAPL")
        self.ticker_input.returnPressed.connect(self._on_analyze_clicked)

        self.period_combo = QComboBox()
        self.period_combo.addItems(["6mo", "1y", "2y", "5y"])
        self.period_combo.setCurrentText("1y")

        self.interval_combo = QComboBox()
        self.interval_combo.addItems(["1d", "1wk"])

        self.analyze_button = QPushButton("Analizza")
        self.analyze_button.clicked.connect(self._on_analyze_clicked)

        form_row.addWidget(QLabel("Ticker:"))
        form_row.addWidget(self.ticker_input)
        form_row.addWidget(QLabel("Periodo:"))
        form_row.addWidget(self.period_combo)
        form_row.addWidget(QLabel("Intervallo:"))
        form_row.addWidget(self.interval_combo)
        form_row.addWidget(self.analyze_button)
        layout.addLayout(form_row)

        self.direction_label = QLabel("-")
        self.direction_label.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(self.direction_label)

        score_row = QHBoxLayout()
        self.score_bar = QProgressBar()
        self.score_bar.setRange(0, 100)
        self.score_bar.setFormat("Confidenza: %v/100")
        self.confirmations_label = QLabel("Conferme: -")
        score_row.addWidget(self.score_bar, stretch=1)
        score_row.addWidget(self.confirmations_label)
        layout.addLayout(score_row)

        self.legs_table = QTableWidget(0, 3)
        self.legs_table.setHorizontalHeaderLabels(["Leg", "Stato", "Dettaglio"])
        self.legs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.legs_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.legs_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.legs_table.verticalHeader().setVisible(False)
        self.legs_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.legs_table)

        risk_row = QHBoxLayout()
        self.price_label = QLabel("Prezzo: -")
        self.atr_label = QLabel("ATR: -")
        self.stop_label = QLabel("Stop suggerito: -")
        risk_row.addWidget(self.price_label)
        risk_row.addWidget(self.atr_label)
        risk_row.addWidget(self.stop_label)
        layout.addLayout(risk_row)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _on_analyze_clicked(self):
        ticker = self.ticker_input.text().strip().upper()
        if not ticker:
            self.status_bar.showMessage("Inserisci un ticker.")
            return

        self.analyze_button.setEnabled(False)
        self.status_bar.showMessage(f"Analisi di {ticker} in corso...")

        self._worker = AnalysisWorker(
            ticker, self.period_combo.currentText(), self.interval_combo.currentText()
        )
        self._worker.succeeded.connect(self._on_result)
        self._worker.failed.connect(self._on_error)
        self._worker.start()

    def _on_result(self, result: AnalysisResult):
        self.analyze_button.setEnabled(True)
        self.status_bar.showMessage("Analisi completata.")

        self.direction_label.setText(result.direction.upper())
        self.score_bar.setValue(int(result.score))
        self.confirmations_label.setText(f"Conferme: {result.confirmations}/{result.total_legs}")

        self.legs_table.setRowCount(len(result.legs))
        for row, leg in enumerate(result.legs):
            color = LEG_COLORS.get(leg.state, QColor("black"))
            items = [
                QTableWidgetItem(leg.name),
                QTableWidgetItem(leg.state),
                QTableWidgetItem(leg.detail),
            ]
            for col, item in enumerate(items):
                item.setForeground(color)
                self.legs_table.setItem(row, col, item)

        self.price_label.setText(f"Prezzo: {result.price:.2f}")
        self.atr_label.setText(f"ATR: {result.atr:.2f}")
        self.stop_label.setText(f"Stop suggerito: {result.suggested_stop_distance:.2f}")

    def _on_error(self, message: str):
        self.analyze_button.setEnabled(True)
        self.status_bar.showMessage(f"Errore: {message}")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
