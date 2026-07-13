import sys

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QColor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
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
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .. import __version__, indicators
from ..data import INTERVAL_LABELS, PERIOD_CHOICES, default_interval, estimated_bars, valid_intervals
from ..engine import AnalysisResult, RSI_OVERBOUGHT, RSI_OVERSOLD
from ..risk import position_size
from .worker import AnalysisWorker, SearchWorker, UpdateCheckWorker, WatchlistWorker

SEARCH_DEBOUNCE_MS = 350
SEARCH_MIN_CHARS = 2

LEG_COLORS = {
    "confirm": QColor("#2e7d32"),
    "neutral": QColor("#757575"),
    "veto": QColor("#c62828"),
}

DIRECTION_COLORS = {
    "bullish": LEG_COLORS["confirm"],
    "bearish": LEG_COLORS["veto"],
    "neutral": LEG_COLORS["neutral"],
}

LIGHT_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #eef0f2;
    color: #24262a;
    font-size: 13px;
}
QTabWidget::pane {
    border: 1px solid #d6d9dd;
    border-radius: 8px;
    background: #ffffff;
    top: -1px;
}
QTabBar::tab {
    background: #e2e4e7;
    color: #45484d;
    padding: 8px 18px;
    border: 1px solid #d6d9dd;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #101113;
    font-weight: 600;
}
QTabBar::tab:hover { background: #eef0f3; }
QGroupBox {
    background: #ffffff;
    border: 1px solid #d6d9dd;
    border-radius: 10px;
    margin-top: 16px;
    padding: 14px 10px 10px 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: #101113;
    font-weight: 600;
}
QPushButton {
    background-color: #2f6fed;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 7px 18px;
    font-weight: 600;
}
QPushButton:hover { background-color: #255ed1; }
QPushButton:pressed { background-color: #1d4bab; }
QPushButton:disabled { background-color: #aab8d6; color: #eef1f8; }
QLineEdit, QComboBox, QDoubleSpinBox, QListWidget, QTableWidget {
    background: #ffffff;
    border: 1px solid #d6d9dd;
    border-radius: 6px;
    padding: 4px 6px;
    selection-background-color: #2f6fed;
    selection-color: #ffffff;
}
QListWidget, QTableWidget {
    alternate-background-color: #f4f5f7;
}
QTableWidget {
    gridline-color: #e3e5e8;
}
QTableWidget::item, QListWidget::item {
    padding: 4px;
}
QHeaderView::section {
    background: #f2f3f5;
    color: #33363b;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #d6d9dd;
    font-weight: 600;
}
QProgressBar {
    border: 1px solid #d6d9dd;
    border-radius: 6px;
    text-align: center;
    background-color: #ffffff;
    min-height: 20px;
    color: #101113;
}
QProgressBar::chunk {
    background-color: #2f6fed;
    border-radius: 5px;
}
QStatusBar {
    background: #f2f3f5;
    border-top: 1px solid #d6d9dd;
}
QCheckBox { spacing: 6px; }
QMenuBar { background: #eef0f2; }
QMenuBar::item:selected { background: #e2e4e7; }
QMenu {
    background: #ffffff;
    border: 1px solid #d6d9dd;
}
QMenu::item:selected {
    background: #2f6fed;
    color: #ffffff;
}
"""

DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #1e1f22;
    color: #dfe1e4;
    font-size: 13px;
}
QTabWidget::pane {
    border: 1px solid #35373c;
    border-radius: 8px;
    background: #26282c;
    top: -1px;
}
QTabBar::tab {
    background: #2a2c30;
    color: #a9adb3;
    padding: 8px 18px;
    border: 1px solid #35373c;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #26282c;
    color: #f0f1f2;
    font-weight: 600;
}
QTabBar::tab:hover { background: #303236; }
QGroupBox {
    background: #26282c;
    border: 1px solid #35373c;
    border-radius: 10px;
    margin-top: 16px;
    padding: 14px 10px 10px 10px;
    color: #dfe1e4;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: #f0f1f2;
    font-weight: 600;
}
QPushButton {
    background-color: #4c86ff;
    color: #0c0d0e;
    border: none;
    border-radius: 6px;
    padding: 7px 18px;
    font-weight: 600;
}
QPushButton:hover { background-color: #6b9bff; }
QPushButton:pressed { background-color: #3a6fe0; }
QPushButton:disabled { background-color: #3d4552; color: #7d8794; }
QLineEdit, QComboBox, QDoubleSpinBox, QListWidget, QTableWidget {
    background: #1e1f22;
    color: #dfe1e4;
    border: 1px solid #35373c;
    border-radius: 6px;
    padding: 4px 6px;
    selection-background-color: #4c86ff;
    selection-color: #0c0d0e;
}
QListWidget, QTableWidget {
    alternate-background-color: #28292d;
}
QTableWidget {
    gridline-color: #303236;
}
QTableWidget::item, QListWidget::item {
    padding: 4px;
}
QHeaderView::section {
    background: #2a2c30;
    color: #dfe1e4;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #35373c;
    font-weight: 600;
}
QProgressBar {
    border: 1px solid #35373c;
    border-radius: 6px;
    text-align: center;
    background-color: #1e1f22;
    min-height: 20px;
    color: #dfe1e4;
}
QProgressBar::chunk {
    background-color: #4c86ff;
    border-radius: 5px;
}
QStatusBar {
    background: #2a2c30;
    border-top: 1px solid #35373c;
    color: #dfe1e4;
}
QCheckBox { spacing: 6px; }
QMenuBar { background: #1e1f22; color: #dfe1e4; }
QMenuBar::item:selected { background: #303236; }
QMenu {
    background: #26282c;
    color: #dfe1e4;
    border: 1px solid #35373c;
}
QMenu::item:selected {
    background: #4c86ff;
    color: #0c0d0e;
}
"""

THEMES = {"light": LIGHT_STYLESHEET, "dark": DARK_STYLESHEET}
MUTED_TEXT_COLOR = {"light": "#54585f", "dark": "#aeb4bd"}
CHART_THEME = {
    "light": {"bg": "#ffffff", "text": "#17181a", "grid": "#d3d7dc"},
    "dark": {"bg": "#1b1c1f", "text": "#e8e9eb", "grid": "#34363c"},
}

GUIDE_TEXT = """\
<b>1. Come cercare un titolo</b><br>
Nel campo Ticker puoi inserire un ticker (es. <i>AAPL</i>) oppure il nome
dell'azienda (es. <i>Eni</i>). Dopo un paio di lettere compare un elenco
di aziende corrispondenti con simbolo e borsa (es. <i>ENI.MI</i> — Eni
S.p.A., Milan): seleziona quella giusta dall'elenco prima di premere
"Analizza", così il ticker usato è esattamente quello scelto. Se scrivi
un ticker esatto già noto (es. <i>AAPL</i>) puoi anche analizzare
direttamente senza passare dall'elenco.<br><br>

<b>2. Periodo e intervallo</b><br>
Il periodo va da una settimana a 5 anni. L'elenco degli intervalli
disponibili si aggiorna automaticamente in base al periodo scelto, in
modo da garantire sempre almeno 200 candele (necessarie per calcolare
l'EMA200 in modo affidabile): per i periodi corti (settimana, mese, 3/6
mesi) vengono proposti solo intervalli intraday (es. 5m, 30m, 1h),
mentre da 1 anno in su resta disponibile anche il giornaliero. La stima
del numero di candele è mostrata sotto i menu.<br><br>

<b>3. Leg opzionali</b><br>
Le caselle MACD e Bollinger Bands aggiungono due leg di conferma
facoltativi (disattivati di default). Se li attivi, il punteggio si
ricalcola automaticamente includendo il loro peso, quindi il punteggio a
3 leg di default non cambia finché restano spenti.<br><br>

<b>4. Come leggere il risultato</b><br>
- <b>Direzione</b> (bullish/bearish/neutral): stabilita <u>solo</u> dal
leg trend (EMA50 rispetto a EMA200). Gli altri leg — momentum, volume,
ed eventualmente macd/bollinger — non possono cambiarla: possono solo
confermarla, restare neutri, o metterle veto. Per questo la direzione
può restare "bullish"/"bearish" anche con punteggio basso e 0
conferme: indica il regime di fondo (EMA50 sopra o sotto EMA200), non
che sia il momento di agire.<br>
- <b>Confidenza (0-100)</b> e <b>conferme</b>: quanto gli altri leg
supportano quella direzione <i>adesso</i>. Un punteggio basso o
ambiguo — anche con direzione bullish/bearish — significa che il
mercato non dà un'indicazione chiara: non è un segnale binario di
buy/sell.<br>
- <b>Esempio</b>: EMA50 sopra EMA200 (struttura rialzista) ma prezzo
sotto EMA50 (pullback), RSI neutro e volume sottile → puoi vedere
"BULLISH" con punteggio 37/100 e 0/3 conferme. Non è un errore: la
direzione riflette solo la struttura EMA50/200, mentre il punteggio
basso dice che nessun altro leg conferma un ingresso adesso.<br><br>

<b>5. I leg</b><br>
- <b>trend</b> (EMA 50/200): l'unico che stabilisce la direzione
(bullish se EMA50 > EMA200, bearish se EMA50 < EMA200). Il suo stato
può essere solo confirm (prezzo anche lui sopra/sotto EMA50, in
accordo) o neutral (prezzo in pullback/rimbalzo): mai veto, perché è
lui a definire la direzione stessa.<br>
- <b>momentum</b> (RSI 14): filtro, non trigger. Conferma il trend,
resta neutro, oppure mette veto se il trend è già esteso in
ipercomprato/ipervenduto.<br>
- <b>volume</b> (relativo alla media a 20 giorni): conferma se il
movimento è supportato da volume, veto se è sottile e quindi a rischio
falso segnale.<br>
- <b>macd</b> (opzionale): confronta la MACD line con la signal line;
conferma se concorde con la direzione del trend, veto se in contrasto.<br>
- <b>bollinger</b> (opzionale): veto se il prezzo è già oltre la banda
nella direzione del trend (movimento troppo esteso, rischio
ritracciamento/rimbalzo), altrimenti conferma.<br><br>

Verde = conferma, grigio = neutro, rosso = veto.<br><br>

<b>6. Rischio e position sizing</b><br>
- <b>Prezzo</b>: ultima chiusura disponibile per il ticker.<br>
- <b>ATR</b> (Average True Range, 14 periodi): volatilità media
recente in valuta. Non entra nel punteggio di confidenza — serve solo
a dimensionare il rischio.<br>
- <b>Stop suggerito</b>: distanza dal prezzo per un eventuale
stop-loss, pari ad ATR × 1.5 di default. È una distanza basata sulla
volatilità storica, non un livello garantito né legato a
supporti/resistenze specifici del titolo.<br>
- <b>Capitale</b> e <b>Rischio per trade (%)</b>: quanto sei disposto
a perdere in valuta se lo stop viene toccato (es. capitale 10.000 e
rischio 1% = 100 di perdita massima accettata).<br>
- <b>Size suggerita</b>: azioni = (capitale × rischio%) ÷ stop
suggerito, arrotondato per difetto. Esempio: capitale 10.000, rischio
1% (cioè 100), stop 3.00 → 33 azioni. A parità di rischio in valuta,
uno stop più stretto (titolo meno volatile) alza la size, uno più
largo (titolo più volatile) la abbassa.<br>
- Questi numeri sono un calcolo meccanico sui parametri che inserisci,
non una raccomandazione di investimento.<br><br>

<b>7. Scheda Grafico</b><br>
Mostra il prezzo con EMA50/EMA200 sovrapposte e, sotto, l'RSI(14) con le
soglie di ipercomprato (70) e ipervenduto (30), per l'ultimo ticker
analizzato nella scheda Analisi.<br><br>

<b>8. Scheda Watchlist</b><br>
Aggiungi più ticker a una lista salvata tra le sessioni. "Analizza
tutti" li scarica e valuta uno alla volta su un thread separato, senza
bloccare l'interfaccia, e popola una tabella ordinabile (clicca
sull'intestazione di una colonna per ordinare) con direzione,
confidenza e conferme. Un ticker che fallisce (es. non trovato) resta
visibile in tabella con l'errore, senza interrompere l'analisi degli
altri. Doppio click su una riga (o selezionala e premi "Carica
selezionato") per aprirla nella scheda Analisi e nel Grafico.<br><br>

<b>9. Backtest (da codice, non ancora in questa finestra)</b><br>
Il modulo <i>stockanalyzer.backtest</i> fa scorrere il motore su una
finestra storica crescente e confronta ogni chiamata direzionale
(bullish/bearish; i casi neutral non contano) con il rendimento
realizzato un certo numero di candele dopo, per verificare quanto le
chiamate del motore siano state coerenti con i movimenti successivi.
Non è un simulatore di trading: nessun costo, slippage o size viene
modellato, è solo un controllo di coerenza del punteggio. Si usa così:<br>
<code>from stockanalyzer.backtest import run_backtest<br>
result = run_backtest(df, forward_bars=10, step=5)<br>
print(result.hit_rate, result.avg_forward_return)<br>
print(result.by_score_bucket)  # dettaglio per fascia di punteggio</code><br>
<i>forward_bars</i> è quante candele dopo si misura il rendimento,
<i>step</i> ogni quante candele si ripete il test (per velocità).
<i>result.by_score_bucket</i> suddivide i risultati in tre fasce di
punteggio (0-33, 34-66, 67-100) per vedere se un punteggio più alto
corrisponde davvero a un tasso di successo migliore.<br><br>

<b>10. Impostazioni salvate e aggiornamenti</b><br>
Ticker, periodo, intervallo, watchlist e tema (menu Visualizza) vengono
ricordati automaticamente alla chiusura e ripristinati al riavvio.
All'avvio l'app controlla in background, su GitHub, se è disponibile
una versione più recente: se sì, mostra un avviso con il link alla
release, senza scaricare o installare nulla in automatico.
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StockAnalyzer")
        self._apply_screen_aware_minimum_size()
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
        self._update_worker: UpdateCheckWorker | None = None
        self._theme = "light"
        self._last_chart: tuple[str, object] | None = None  # (symbol, df) for theme redraws
        self._settings = QSettings("StockAnalyzer", "StockAnalyzer")
        self._build_menu()
        self._build_ui()
        self._apply_theme(self._theme)
        self._load_settings()

    def _apply_screen_aware_minimum_size(self):
        """A fixed minimum size can exceed a small screen's own resolution,
        which would stop showMaximized() from actually filling it. Cap the
        floor to whatever the screen the window opens on can offer."""
        preferred_width, preferred_height = 900, 600
        screen = QApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            preferred_width = min(preferred_width, available.width())
            preferred_height = min(preferred_height, available.height())
        self.setMinimumSize(preferred_width, preferred_height)

    def _build_menu(self):
        self.view_menu = self.menuBar().addMenu("&Visualizza")

        self.theme_action_group = QActionGroup(self)
        self.theme_action_group.setExclusive(True)

        self.light_theme_action = QAction("Tema &chiaro", self, checkable=True)
        self.light_theme_action.triggered.connect(lambda: self._apply_theme("light"))
        self.theme_action_group.addAction(self.light_theme_action)
        self.view_menu.addAction(self.light_theme_action)

        self.dark_theme_action = QAction("Tema &scuro", self, checkable=True)
        self.dark_theme_action.triggered.connect(lambda: self._apply_theme("dark"))
        self.theme_action_group.addAction(self.dark_theme_action)
        self.view_menu.addAction(self.dark_theme_action)

        self.help_menu = self.menuBar().addMenu("&Aiuto")

        self.guide_action = QAction("&Guida", self)
        self.guide_action.triggered.connect(self._show_guide)
        self.help_menu.addAction(self.guide_action)

        self.about_action = QAction("&Informazioni su StockAnalyzer", self)
        self.about_action.triggered.connect(self._show_about)
        self.help_menu.addAction(self.about_action)

    def _apply_theme(self, theme: str):
        theme = theme if theme in THEMES else "light"
        self._theme = theme

        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(THEMES[theme])

        muted = MUTED_TEXT_COLOR[theme]
        self.candles_label.setStyleSheet(f"color: {muted}; font-weight: normal;")
        self.symbol_label.setStyleSheet(f"color: {muted}; font-weight: normal;")
        self.watchlist_progress_label.setStyleSheet(f"color: {muted}; font-weight: normal;")

        self.light_theme_action.setChecked(theme == "light")
        self.dark_theme_action.setChecked(theme == "dark")

        self._style_chart_axes()
        self.chart_canvas.draw()

    def _build_guide_dialog(self) -> QDialog:
        dialog = QDialog(self)
        dialog.setWindowTitle("Guida")
        dialog.resize(640, 560)  # fixed, centered dialog - not fullscreen

        layout = QVBoxLayout(dialog)
        text_browser = QTextBrowser()  # QAbstractScrollArea: scrolls instead of growing
        text_browser.setOpenExternalLinks(True)
        text_browser.setHtml(GUIDE_TEXT)
        layout.addWidget(text_browser)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.accept)
        layout.addWidget(buttons)
        return dialog

    def _show_guide(self):
        self._build_guide_dialog().exec()

    def _show_about(self):
        QMessageBox.about(
            self,
            "Informazioni su StockAnalyzer",
            f"<b>StockAnalyzer</b> v{__version__}<br><br>"
            "Motore di trend-confirmation basato su regole "
            "(EMA 50/200, RSI, ATR, volume) con GUI Qt6.",
        )

    def _check_for_updates(self):
        """Best-effort startup check against GitHub Releases; a no-op on any
        failure (offline, rate-limited, ...) since it must never block or
        break startup. Only notifies - it never downloads or installs
        anything on its own."""
        self._update_worker = UpdateCheckWorker(__version__)
        self._update_worker.checked.connect(self._on_update_checked)
        self._update_worker.start()

    def _on_update_checked(self, info):
        if info is None:
            return
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Information)
        box.setWindowTitle("Aggiornamento disponibile")
        box.setText(f"È disponibile StockAnalyzer v{info.version} (in uso: v{__version__}).")
        box.setInformativeText(info.url)
        box.exec()

    def _build_ui(self):
        tabs = QTabWidget()
        self.tabs = tabs
        self.setCentralWidget(tabs)
        tabs.addTab(self._build_analysis_tab(), "Analisi")
        tabs.addTab(self._build_chart_tab(), "Grafico")
        tabs.addTab(self._build_watchlist_tab(), "Watchlist")

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _build_analysis_tab(self) -> QWidget:
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setSpacing(14)

        search_group = QGroupBox("Ricerca e parametri")
        search_layout = QVBoxLayout(search_group)

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
        form_row.addWidget(self.ticker_input, stretch=1)
        form_row.addWidget(QLabel("Periodo:"))
        form_row.addWidget(self.period_combo)
        form_row.addWidget(QLabel("Intervallo:"))
        form_row.addWidget(self.interval_combo)
        form_row.addWidget(self.analyze_button)
        search_layout.addLayout(form_row)

        self.results_list = QListWidget()
        self.results_list.setMaximumHeight(120)
        self.results_list.itemClicked.connect(self._on_candidate_selected)
        self.results_list.hide()
        search_layout.addWidget(self.results_list)

        self.candles_label = QLabel("")
        self.candles_label.setStyleSheet("color: #757575;")
        search_layout.addWidget(self.candles_label)

        extra_legs_row = QHBoxLayout()
        extra_legs_row.addWidget(QLabel("Leg opzionali:"))
        self.macd_checkbox = QCheckBox("MACD")
        self.bollinger_checkbox = QCheckBox("Bollinger Bands")
        extra_legs_row.addWidget(self.macd_checkbox)
        extra_legs_row.addWidget(self.bollinger_checkbox)
        extra_legs_row.addStretch(1)
        search_layout.addLayout(extra_legs_row)

        layout.addWidget(search_group)
        self._on_period_changed()

        result_group = QGroupBox("Risultato")
        result_layout = QVBoxLayout(result_group)

        self.symbol_label = QLabel("")
        self.symbol_label.setStyleSheet("color: #757575; font-weight: normal;")
        result_layout.addWidget(self.symbol_label)

        self.direction_label = QLabel("-")
        self.direction_label.setStyleSheet("font-size: 26px; font-weight: bold;")
        result_layout.addWidget(self.direction_label)

        score_row = QHBoxLayout()
        self.score_bar = QProgressBar()
        self.score_bar.setRange(0, 100)
        self.score_bar.setFormat("Confidenza: %v/100")
        self.confirmations_label = QLabel("Conferme: -")
        self.confirmations_label.setStyleSheet("font-weight: normal;")
        score_row.addWidget(self.score_bar, stretch=1)
        score_row.addWidget(self.confirmations_label)
        result_layout.addLayout(score_row)

        self.legs_table = QTableWidget(0, 3)
        self.legs_table.setHorizontalHeaderLabels(["Leg", "Stato", "Dettaglio"])
        self.legs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.legs_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.legs_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.legs_table.verticalHeader().setVisible(False)
        self.legs_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.legs_table.setAlternatingRowColors(True)
        result_layout.addWidget(self.legs_table)
        self._fit_legs_table_height()

        layout.addWidget(result_group)

        risk_group = QGroupBox("Rischio e position sizing")
        risk_layout = QVBoxLayout(risk_group)

        risk_row = QHBoxLayout()
        self.price_label = QLabel("Prezzo: -")
        self.atr_label = QLabel("ATR: -")
        self.stop_label = QLabel("Stop suggerito: -")
        for label in (self.price_label, self.atr_label, self.stop_label):
            label.setStyleSheet("font-weight: normal;")
        risk_row.addWidget(self.price_label)
        risk_row.addWidget(self.atr_label)
        risk_row.addWidget(self.stop_label)
        risk_layout.addLayout(risk_row)

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
        self.position_size_label.setStyleSheet("font-weight: normal;")

        sizing_row.addWidget(QLabel("Capitale:"))
        sizing_row.addWidget(self.account_size_input)
        sizing_row.addWidget(QLabel("Rischio per trade:"))
        sizing_row.addWidget(self.risk_pct_input)
        sizing_row.addWidget(self.position_size_label, stretch=1)
        risk_layout.addLayout(sizing_row)

        layout.addWidget(risk_group)
        layout.addStretch(1)  # leftover space collects here, not stretched into a group

        return central

    def _fit_legs_table_height(self):
        """Size legs_table to its (small, bounded 3-5) row count instead of
        letting it stretch to fill the tab, which left a large empty gap
        below the last row on tall/maximized windows."""
        self.legs_table.resizeRowsToContents()
        row_count = max(self.legs_table.rowCount(), 3)
        row_height = self.legs_table.rowHeight(0) if self.legs_table.rowCount() else 30
        header_height = self.legs_table.horizontalHeader().height()
        frame = 2 * self.legs_table.frameWidth()
        # setMaximumHeight alone isn't enough: the layout still allocates the
        # table its (smaller, generic) sizeHint unless the height is fixed.
        self.legs_table.setFixedHeight(header_height + row_count * (row_height + 1) + frame + 10)

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

    def _style_chart_axes(self):
        colors = CHART_THEME[self._theme]
        self.chart_figure.set_facecolor(colors["bg"])
        for ax in (self.chart_ax_price, self.chart_ax_rsi):
            ax.set_facecolor(colors["bg"])
            ax.tick_params(colors=colors["text"], labelcolor=colors["text"])
            ax.title.set_color(colors["text"])
            ax.xaxis.label.set_color(colors["text"])
            ax.yaxis.label.set_color(colors["text"])
            ax.grid(color=colors["grid"], alpha=0.5)
            for spine in ax.spines.values():
                spine.set_color(colors["grid"])
            legend = ax.get_legend()
            if legend is not None:
                legend.get_frame().set_facecolor(colors["bg"])
                legend.get_frame().set_edgecolor(colors["grid"])
                for text in legend.get_texts():
                    text.set_color(colors["text"])

    def _clear_chart(self):
        self.chart_ax_price.clear()
        self.chart_ax_rsi.clear()
        self.chart_ax_price.set_title("Analizza un ticker per vedere il grafico")
        self._style_chart_axes()
        self.chart_canvas.draw()

    def _update_chart(self, symbol: str, df):
        self._last_chart = (symbol, df)
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
        self._style_chart_axes()
        self.chart_canvas.draw()

    def _build_watchlist_tab(self) -> QWidget:
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setSpacing(14)

        manage_group = QGroupBox("Gestisci watchlist")
        manage_layout = QVBoxLayout(manage_group)

        add_row = QHBoxLayout()
        self.watchlist_input = QLineEdit()
        self.watchlist_input.setPlaceholderText("Ticker da aggiungere, es. AAPL")
        self.watchlist_input.returnPressed.connect(self._on_watchlist_add)
        self.watchlist_add_button = QPushButton("Aggiungi")
        self.watchlist_add_button.clicked.connect(self._on_watchlist_add)
        self.watchlist_remove_button = QPushButton("Rimuovi selezionato")
        self.watchlist_remove_button.clicked.connect(self._on_watchlist_remove)
        add_row.addWidget(QLabel("Ticker:"))
        add_row.addWidget(self.watchlist_input, stretch=1)
        add_row.addWidget(self.watchlist_add_button)
        add_row.addWidget(self.watchlist_remove_button)
        manage_layout.addLayout(add_row)

        self.watchlist_tickers_list = QListWidget()
        self.watchlist_tickers_list.setMaximumHeight(100)
        manage_layout.addWidget(self.watchlist_tickers_list)

        self.watchlist_run_button = QPushButton("Analizza tutti")
        manage_layout.addWidget(self.watchlist_run_button)
        self.watchlist_run_button.clicked.connect(self._on_watchlist_run)

        self.watchlist_progress_label = QLabel("")
        self.watchlist_progress_label.setStyleSheet("color: #757575; font-weight: normal;")
        manage_layout.addWidget(self.watchlist_progress_label)

        layout.addWidget(manage_group)

        table_hint_row = QHBoxLayout()
        table_hint_row.addWidget(QLabel("Doppio click su una riga per caricarla in Analisi/Grafico."))
        table_hint_row.addStretch(1)
        self.watchlist_load_button = QPushButton("Carica selezionato")
        self.watchlist_load_button.clicked.connect(self._on_watchlist_load_selected)
        table_hint_row.addWidget(self.watchlist_load_button)
        layout.addLayout(table_hint_row)

        self.watchlist_table = QTableWidget(0, 5)
        self.watchlist_table.setHorizontalHeaderLabels(
            ["Ticker", "Nome", "Direzione", "Confidenza", "Conferme"]
        )
        self.watchlist_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.watchlist_table.verticalHeader().setVisible(False)
        self.watchlist_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.watchlist_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.watchlist_table.setSortingEnabled(True)
        self.watchlist_table.setAlternatingRowColors(True)
        self.watchlist_table.cellDoubleClicked.connect(self._on_watchlist_row_double_clicked)
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
        self._apply_theme(self._settings.value("theme", "light"))

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
        self._settings.setValue("theme", self._theme)

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
        direction_color = DIRECTION_COLORS.get(result.direction, QColor("black")).name()
        self.direction_label.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {direction_color};")
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
        self._fit_legs_table_height()

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

    def _on_watchlist_row_double_clicked(self, row: int, _column: int):
        self._load_watchlist_row_into_analysis(row)

    def _on_watchlist_load_selected(self):
        row = self.watchlist_table.currentRow()
        if row < 0:
            self.status_bar.showMessage("Seleziona una riga della watchlist da caricare.")
            return
        self._load_watchlist_row_into_analysis(row)

    def _load_watchlist_row_into_analysis(self, row: int):
        ticker_item = self.watchlist_table.item(row, 0)
        name_item = self.watchlist_table.item(row, 1)
        if ticker_item is None or name_item is None:
            return
        if name_item.text().startswith("Errore"):
            self.status_bar.showMessage(
                f"'{ticker_item.text()}' non è stato analizzato correttamente nella watchlist."
            )
            return

        symbol = ticker_item.text()
        name = name_item.text()

        self._resolved = (symbol, name)
        self.ticker_input.blockSignals(True)
        self.ticker_input.setText(symbol)
        self.ticker_input.blockSignals(False)
        self.tabs.setCurrentIndex(0)  # Analisi tab, where the chart update also follows
        self._on_analyze_clicked()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()  # applies the saved (or default light) theme itself
    # Open maximized so the window fills whatever screen it lands on, rather
    # than a fixed pixel size that's oversized on small displays or tiny on
    # large/high-DPI ones; setMinimumSize still protects very small screens.
    window.showMaximized()
    window._check_for_updates()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
