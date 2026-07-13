import sys

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QDoubleSpinBox,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import __version__, indicators
from ..data import INTERVAL_LABELS, PERIOD_CHOICES, default_interval, estimated_bars, valid_intervals
from ..engine import AnalysisResult, RSI_OVERBOUGHT, RSI_OVERSOLD
from ..risk import position_size
from .worker import AnalysisWorker, SearchWorker, WatchlistWorker

SEARCH_DEBOUNCE_MS = 350
SEARCH_MIN_CHARS = 2

LEG_COLORS = {
    "confirm": QColor("#2e7d32"),
    "neutral": QColor("#757575"),
    "veto": QColor("#c62828"),
}

GUIDE_TEXT = """\
<b>Come cercare</b><br>
Nel campo in alto puoi inserire un ticker (es. <i>AAPL</i>) oppure il nome
dell'azienda (es. <i>Eni</i>). Dopo un paio di lettere compare un elenco
di aziende corrispondenti con simbolo e borsa (es. <i>ENI.MI</i> — Eni
S.p.A., Milan): seleziona quella giusta dall'elenco prima di premere
"Analizza". Se scrivi un ticker esatto già noto (es. <i>AAPL</i>) puoi
anche analizzare direttamente senza scegliere dall'elenco.<br><br>

<b>Come leggere il risultato</b><br>
- <b>Direzione</b>: bullish/bearish/neutral, stabilita dal trend primario
(EMA 50/200 + posizione del prezzo).<br>
- <b>Confidenza (0-100)</b> e <b>conferme</b>: quanto gli altri leg
confermano la direzione. Non è un segnale binario di buy/sell: un
punteggio basso o ambiguo significa che il mercato non dà un'indicazione
chiara.<br><br>

<b>I tre leg</b><br>
- <b>trend</b> (EMA 50/200): l'unico che stabilisce la direzione.<br>
- <b>momentum</b> (RSI 14): filtro, non trigger. Conferma il trend,
resta neutro, oppure mette veto se il trend è già esteso in
ipercomprato/ipervenduto.<br>
- <b>volume</b> (relativo alla media a 20 giorni): conferma se il
movimento è supportato da volume, veto se è sottile e quindi a rischio
falso segnale.<br><br>

Verde = conferma, grigio = neutro, rosso = veto.<br><br>

<b>Rischio</b><br>
L'ATR(14) non entra nel punteggio: fornisce solo la distanza di stop
suggerita, mostrata in basso insieme a prezzo e ATR.
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StockAnalyzer")
        self.resize(720, 520)
        self._worker: AnalysisWorker | None = None
        self._search_worker: SearchWorker | None = None
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._run_search)
        self._resolved: tuple[str, str] | None = None  # (symbol, name) picked from search list
        self._last_result: AnalysisResult | None = None
        self._watchlist_worker: WatchlistWorker | None = None
        self._watchlist_done = 0
        self._watchlist_total = 0
        self._settings = QSettings("StockAnalyzer", "StockAnalyzer")
        self._build_menu()
        self._build_ui()
        self._load_settings()

    def _build_menu(self):
        self.help_menu = self.menuBar().addMenu("&Aiuto")

        self.guide_action = QAction("&Guida", self)
        self.guide_action.triggered.connect(self._show_guide)
        self.help_menu.addAction(self.guide_action)

        self.about_action = QAction("&Informazioni su StockAnalyzer", self)
        self.about_action.triggered.connect(self._show_about)
        self.help_menu.addAction(self.about_action)

    def _show_guide(self):
        QMessageBox.information(self, "Guida", GUIDE_TEXT)

    def _show_about(self):
        QMessageBox.about(
            self,
            "Informazioni su StockAnalyzer",
            f"<b>StockAnalyzer</b> v{__version__}<br><br>"
            "Motore di trend-confirmation basato su regole "
            "(EMA 50/200, RSI, ATR, volume) con GUI Qt6.",
        )

    def _build_ui(self):
        tabs = QTabWidget()
        self.setCentralWidget(tabs)
        tabs.addTab(self._build_analysis_tab(), "Analisi")
        tabs.addTab(self._build_chart_tab(), "Grafico")
        tabs.addTab(self._build_watchlist_tab(), "Watchlist")

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _build_analysis_tab(self) -> QWidget:
        central = QWidget()
        layout = QVBoxLayout(central)

        form_row = QHBoxLayout()
        self.ticker_input = QLineEdit()
        self.ticker_input.setPlaceholderText("Ticker o nome azienda, es. AAPL oppure Eni")
        self.ticker_input.returnPressed.connect(self._on_analyze_clicked)
        self.ticker_input.textEdited.connect(self._on_ticker_text_edited)

        self.period_combo = QComboBox()
        for code, label, _days in PERIOD_CHOICES:
            self.period_combo.addItem(label, code)
        self.period_combo.setCurrentIndex(
            next(i for i, (code, _, _) in enumerate(PERIOD_CHOICES) if code == "1y")
        )
        self.period_combo.currentIndexChanged.connect(self._on_period_changed)

        self.interval_combo = QComboBox()
        self.interval_combo.currentIndexChanged.connect(self._update_candles_label)

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

        self.results_list = QListWidget()
        self.results_list.setMaximumHeight(120)
        self.results_list.itemClicked.connect(self._on_candidate_selected)
        self.results_list.hide()
        layout.addWidget(self.results_list)

        self.candles_label = QLabel("")
        self.candles_label.setStyleSheet("color: #757575;")
        layout.addWidget(self.candles_label)

        extra_legs_row = QHBoxLayout()
        extra_legs_row.addWidget(QLabel("Leg opzionali:"))
        self.macd_checkbox = QCheckBox("MACD")
        self.bollinger_checkbox = QCheckBox("Bollinger Bands")
        extra_legs_row.addWidget(self.macd_checkbox)
        extra_legs_row.addWidget(self.bollinger_checkbox)
        extra_legs_row.addStretch(1)
        layout.addLayout(extra_legs_row)

        self._on_period_changed()

        self.symbol_label = QLabel("")
        self.symbol_label.setStyleSheet("color: #757575;")
        layout.addWidget(self.symbol_label)

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

        sizing_row = QHBoxLayout()
        self.account_size_input = QDoubleSpinBox()
        self.account_size_input.setRange(0, 1_000_000_000)
        self.account_size_input.setDecimals(2)
        self.account_size_input.setValue(10_000)
        self.account_size_input.valueChanged.connect(self._update_position_size)

        self.risk_pct_input = QDoubleSpinBox()
        self.risk_pct_input.setRange(0.01, 100)
        self.risk_pct_input.setDecimals(2)
        self.risk_pct_input.setValue(1.0)
        self.risk_pct_input.setSuffix(" %")
        self.risk_pct_input.valueChanged.connect(self._update_position_size)

        self.position_size_label = QLabel("Size suggerita: -")

        sizing_row.addWidget(QLabel("Capitale:"))
        sizing_row.addWidget(self.account_size_input)
        sizing_row.addWidget(QLabel("Rischio per trade:"))
        sizing_row.addWidget(self.risk_pct_input)
        sizing_row.addWidget(self.position_size_label, stretch=1)
        layout.addLayout(sizing_row)

        return central

    def _build_chart_tab(self) -> QWidget:
        central = QWidget()
        layout = QVBoxLayout(central)

        self.chart_figure = Figure(figsize=(6, 5))
        self.chart_canvas = FigureCanvasQTAgg(self.chart_figure)
        self.chart_ax_price = self.chart_figure.add_subplot(2, 1, 1)
        self.chart_ax_rsi = self.chart_figure.add_subplot(2, 1, 2, sharex=self.chart_ax_price)
        self.chart_figure.tight_layout()
        layout.addWidget(self.chart_canvas)

        self._clear_chart()
        return central

    def _clear_chart(self):
        self.chart_ax_price.clear()
        self.chart_ax_rsi.clear()
        self.chart_ax_price.set_title("Analizza un ticker per vedere il grafico")
        self.chart_canvas.draw()

    def _update_chart(self, symbol: str, df):
        close = df["close"]
        ema50 = indicators.ema(close, 50)
        ema200 = indicators.ema(close, 200)
        rsi14 = indicators.rsi(close, 14)

        self.chart_ax_price.clear()
        self.chart_ax_price.plot(df.index, close, label="Prezzo", color="#1f77b4", linewidth=1)
        self.chart_ax_price.plot(df.index, ema50, label="EMA50", color="#ff7f0e", linewidth=1)
        self.chart_ax_price.plot(df.index, ema200, label="EMA200", color="#2ca02c", linewidth=1)
        self.chart_ax_price.set_title(symbol)
        self.chart_ax_price.legend(loc="upper left", fontsize="small")
        self.chart_ax_price.tick_params(labelbottom=False)

        self.chart_ax_rsi.clear()
        self.chart_ax_rsi.plot(df.index, rsi14, label="RSI(14)", color="#9467bd", linewidth=1)
        self.chart_ax_rsi.axhline(RSI_OVERBOUGHT, color="#c62828", linestyle="--", linewidth=0.8)
        self.chart_ax_rsi.axhline(RSI_OVERSOLD, color="#2e7d32", linestyle="--", linewidth=0.8)
        self.chart_ax_rsi.set_ylim(0, 100)
        self.chart_ax_rsi.legend(loc="upper left", fontsize="small")

        self.chart_figure.autofmt_xdate()
        self.chart_canvas.draw()

    def _build_watchlist_tab(self) -> QWidget:
        central = QWidget()
        layout = QVBoxLayout(central)

        add_row = QHBoxLayout()
        self.watchlist_input = QLineEdit()
        self.watchlist_input.setPlaceholderText("Ticker da aggiungere, es. AAPL")
        self.watchlist_input.returnPressed.connect(self._on_watchlist_add)
        self.watchlist_add_button = QPushButton("Aggiungi")
        self.watchlist_add_button.clicked.connect(self._on_watchlist_add)
        self.watchlist_remove_button = QPushButton("Rimuovi selezionato")
        self.watchlist_remove_button.clicked.connect(self._on_watchlist_remove)
        add_row.addWidget(QLabel("Ticker:"))
        add_row.addWidget(self.watchlist_input)
        add_row.addWidget(self.watchlist_add_button)
        add_row.addWidget(self.watchlist_remove_button)
        layout.addLayout(add_row)

        self.watchlist_tickers_list = QListWidget()
        self.watchlist_tickers_list.setMaximumHeight(100)
        layout.addWidget(self.watchlist_tickers_list)

        self.watchlist_run_button = QPushButton("Analizza tutti")
        self.watchlist_run_button.clicked.connect(self._on_watchlist_run)
        layout.addWidget(self.watchlist_run_button)

        self.watchlist_progress_label = QLabel("")
        self.watchlist_progress_label.setStyleSheet("color: #757575;")
        layout.addWidget(self.watchlist_progress_label)

        self.watchlist_table = QTableWidget(0, 5)
        self.watchlist_table.setHorizontalHeaderLabels(
            ["Ticker", "Nome", "Direzione", "Confidenza", "Conferme"]
        )
        self.watchlist_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.watchlist_table.verticalHeader().setVisible(False)
        self.watchlist_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.watchlist_table.setSortingEnabled(True)
        layout.addWidget(self.watchlist_table)

        return central

    def _selected_period_days(self) -> int:
        code = self.period_combo.currentData()
        return next(days for c, _label, days in PERIOD_CHOICES if c == code)

    def _on_period_changed(self):
        days = self._selected_period_days()
        options = valid_intervals(days) or [default_interval(days)]
        default = default_interval(days)

        self.interval_combo.blockSignals(True)
        self.interval_combo.clear()
        for code in options:
            self.interval_combo.addItem(INTERVAL_LABELS.get(code, code), code)
        default_index = options.index(default) if default in options else 0
        self.interval_combo.setCurrentIndex(default_index)
        self.interval_combo.blockSignals(False)

        self._update_candles_label()

    def _update_candles_label(self):
        days = self._selected_period_days()
        interval = self.interval_combo.currentData()
        if interval is None:
            return
        bars = int(estimated_bars(days, interval))
        self.candles_label.setText(f"≈ {bars} candele stimate (minimo richiesto: 200)")

    def _load_settings(self):
        ticker = self._settings.value("ticker", "")
        if ticker:
            self.ticker_input.setText(ticker)

        period_code = self._settings.value("period", "1y")
        period_index = next(
            (i for i in range(self.period_combo.count()) if self.period_combo.itemData(i) == period_code),
            None,
        )
        if period_index is not None:
            self.period_combo.setCurrentIndex(period_index)  # triggers _on_period_changed

        interval_code = self._settings.value("interval")
        if interval_code:
            interval_index = next(
                (i for i in range(self.interval_combo.count()) if self.interval_combo.itemData(i) == interval_code),
                None,
            )
            if interval_index is not None:
                self.interval_combo.setCurrentIndex(interval_index)

        watchlist = self._settings.value("watchlist", "")
        if watchlist:
            self.watchlist_tickers_list.addItems(watchlist.split("|"))

    def _save_settings(self):
        self._settings.setValue("ticker", self.ticker_input.text().strip())
        self._settings.setValue("period", self.period_combo.currentData())
        self._settings.setValue("interval", self.interval_combo.currentData())
        self._settings.setValue("watchlist", "|".join(self._watchlist_tickers()))

    def closeEvent(self, event):
        self._save_settings()
        super().closeEvent(event)

    def _on_ticker_text_edited(self, _text: str):
        self._resolved = None  # any earlier pick no longer matches what's typed
        self.results_list.hide()
        self._search_timer.stop()
        if len(self.ticker_input.text().strip()) >= SEARCH_MIN_CHARS:
            self._search_timer.start(SEARCH_DEBOUNCE_MS)

    def _run_search(self):
        query = self.ticker_input.text().strip()
        if len(query) < SEARCH_MIN_CHARS:
            return
        self._search_worker = SearchWorker(query)
        self._search_worker.found.connect(self._on_search_results)
        self._search_worker.start()

    def _on_search_results(self, query: str, candidates: list[dict]):
        # Discard stale results if the user kept typing after this search started.
        if query != self.ticker_input.text().strip():
            return

        self.results_list.clear()
        if not candidates:
            self.results_list.hide()
            return

        for candidate in candidates:
            exchange = f" ({candidate['exchange']})" if candidate["exchange"] else ""
            label = f"{candidate['symbol']} — {candidate['name']}{exchange}"
            self.results_list.addItem(label)
            self.results_list.item(self.results_list.count() - 1).setData(
                Qt.UserRole, (candidate["symbol"], candidate["name"])
            )
        self.results_list.show()

    def _on_candidate_selected(self, item):
        symbol, name = item.data(Qt.UserRole)
        self._resolved = (symbol, name)
        self.ticker_input.blockSignals(True)
        self.ticker_input.setText(symbol)
        self.ticker_input.blockSignals(False)
        self.results_list.hide()

    def _on_analyze_clicked(self):
        query = self.ticker_input.text().strip()
        if not query:
            self.status_bar.showMessage("Inserisci un ticker o il nome di un'azienda.")
            return

        self.results_list.hide()
        self.analyze_button.setEnabled(False)
        self.status_bar.showMessage(f"Ricerca di '{query}' e analisi in corso...")

        extra_legs = set()
        if self.macd_checkbox.isChecked():
            extra_legs.add("macd")
        if self.bollinger_checkbox.isChecked():
            extra_legs.add("bollinger")

        self._worker = AnalysisWorker(
            query,
            self.period_combo.currentData(),
            self.interval_combo.currentData(),
            resolved=self._resolved,
            extra_legs=frozenset(extra_legs),
        )
        self._worker.succeeded.connect(self._on_result)
        self._worker.failed.connect(self._on_error)
        self._worker.start()

    def _on_result(self, result: AnalysisResult, symbol: str, name: str, df):
        self.analyze_button.setEnabled(True)
        self.status_bar.showMessage("Analisi completata.")

        self.symbol_label.setText(f"{symbol} — {name}" if name != symbol else symbol)
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

        self._last_result = result
        self._update_position_size()
        self._update_chart(symbol, df)

    def _update_position_size(self, *_args):
        if self._last_result is None:
            return
        sizing = position_size(
            account_size=self.account_size_input.value(),
            risk_pct=self.risk_pct_input.value(),
            stop_distance=self._last_result.suggested_stop_distance,
            price=self._last_result.price,
        )
        self.position_size_label.setText(
            f"Size suggerita: {sizing.shares} azioni (~{sizing.position_value:.2f}, "
            f"rischio {sizing.risk_amount:.2f})"
        )

    def _on_error(self, message: str):
        self.analyze_button.setEnabled(True)
        self.status_bar.showMessage(f"Errore: {message}")

    def _on_watchlist_add(self):
        query = self.watchlist_input.text().strip()
        if not query:
            return
        existing = {
            self.watchlist_tickers_list.item(i).text() for i in range(self.watchlist_tickers_list.count())
        }
        if query.upper() not in existing:
            self.watchlist_tickers_list.addItem(query.upper())
        self.watchlist_input.clear()

    def _on_watchlist_remove(self):
        for item in self.watchlist_tickers_list.selectedItems():
            self.watchlist_tickers_list.takeItem(self.watchlist_tickers_list.row(item))

    def _watchlist_tickers(self) -> list[str]:
        return [self.watchlist_tickers_list.item(i).text() for i in range(self.watchlist_tickers_list.count())]

    def _on_watchlist_run(self):
        tickers = self._watchlist_tickers()
        if not tickers:
            self.status_bar.showMessage("Aggiungi almeno un ticker alla watchlist.")
            return

        extra_legs = set()
        if self.macd_checkbox.isChecked():
            extra_legs.add("macd")
        if self.bollinger_checkbox.isChecked():
            extra_legs.add("bollinger")

        self.watchlist_run_button.setEnabled(False)
        self.watchlist_table.setSortingEnabled(False)
        self.watchlist_table.setRowCount(0)
        self._watchlist_done = 0
        self._watchlist_total = len(tickers)
        self.watchlist_progress_label.setText(f"0/{self._watchlist_total} completati...")

        self._watchlist_worker = WatchlistWorker(
            tickers,
            self.period_combo.currentData(),
            self.interval_combo.currentData(),
            extra_legs=frozenset(extra_legs),
        )
        self._watchlist_worker.item_done.connect(self._on_watchlist_item_done)
        self._watchlist_worker.finished.connect(self._on_watchlist_finished)
        self._watchlist_worker.start()

    def _on_watchlist_item_done(self, symbol: str, name: str, result: AnalysisResult | None, error: str):
        self._watchlist_done += 1
        self.watchlist_progress_label.setText(f"{self._watchlist_done}/{self._watchlist_total} completati...")

        row = self.watchlist_table.rowCount()
        self.watchlist_table.insertRow(row)

        if result is None:
            for col, text in enumerate([symbol, f"Errore: {error}", "-", "-", "-"]):
                self.watchlist_table.setItem(row, col, QTableWidgetItem(text))
            return

        leg_state = {"bullish": "confirm", "bearish": "veto"}.get(result.direction, "neutral")
        color = LEG_COLORS.get(leg_state, QColor("black"))

        score_item = QTableWidgetItem()
        score_item.setData(Qt.DisplayRole, result.score)

        items = [
            QTableWidgetItem(symbol),
            QTableWidgetItem(name),
            QTableWidgetItem(result.direction.upper()),
            score_item,
            QTableWidgetItem(f"{result.confirmations}/{result.total_legs}"),
        ]
        for col, item in enumerate(items):
            item.setForeground(color)
            self.watchlist_table.setItem(row, col, item)

    def _on_watchlist_finished(self):
        self.watchlist_run_button.setEnabled(True)
        self.watchlist_table.setSortingEnabled(True)
        self.watchlist_progress_label.setText(f"Completato: {self._watchlist_total} ticker analizzati.")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
