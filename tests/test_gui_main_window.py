from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QMessageBox, QTextBrowser

from stockanalyzer.engine import AnalysisResult, Leg
from stockanalyzer.gui.main_window import DARK_STYLESHEET, MainWindow
from stockanalyzer.updater import UpdateInfo

SETTINGS_ORG = "StockAnalyzer"
SETTINGS_APP = "StockAnalyzer"


@pytest.fixture(autouse=True)
def _clean_settings():
    QSettings(SETTINGS_ORG, SETTINGS_APP).clear()
    yield
    QSettings(SETTINGS_ORG, SETTINGS_APP).clear()


def _make_df(n=250):
    t = np.arange(n)
    close = 100 + 0.3 * t + 3 * np.sin(t / 5.0)
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    return pd.DataFrame(
        {
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": np.full(n, 1000.0),
        },
        index=dates,
    )


def _make_result(direction="bullish", score=80.0):
    return AnalysisResult(
        direction=direction,
        score=score,
        confirmations=2,
        total_legs=3,
        legs=[
            Leg("trend", "confirm", "x"),
            Leg("momentum", "confirm", "y"),
            Leg("volume", "neutral", "z"),
        ],
        price=100.0,
        ema50=95.0,
        ema200=90.0,
        rsi=55.0,
        relative_volume=1.0,
        atr=2.0,
        suggested_stop_distance=3.0,
    )


def test_period_change_updates_interval_options_and_default(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    idx = next(i for i in range(window.period_combo.count()) if window.period_combo.itemData(i) == "6mo")
    window.period_combo.setCurrentIndex(idx)

    options = [window.interval_combo.itemData(i) for i in range(window.interval_combo.count())]
    assert options == ["60m"]
    assert window.interval_combo.currentData() == "60m"
    assert "200" in window.candles_label.text()


def test_search_results_populate_list_and_selection_fills_ticker(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    window.ticker_input.setText("eni")

    candidates = [
        {"symbol": "ENI.MI", "name": "Eni S.p.A.", "exchange": "Milan"},
        {"symbol": "E", "name": "Eni SpA", "exchange": "NYSE"},
    ]
    window._on_search_results("eni", candidates)

    assert window.results_list.isVisible()
    assert window.results_list.count() == 2

    item = window.results_list.item(0)
    window._on_candidate_selected(item)

    assert window.ticker_input.text() == "ENI.MI"
    assert window._resolved == ("ENI.MI", "Eni S.p.A.")
    assert not window.results_list.isVisible()


def test_editing_ticker_after_selection_clears_resolved_symbol(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window._resolved = ("ENI.MI", "Eni S.p.A.")
    window.ticker_input.setText("ENI.MI extra")
    window._on_ticker_text_edited("ENI.MI extra")

    assert window._resolved is None


def test_analyze_flow_updates_result_panel_and_chart(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.ticker_input.setText("AAPL")

    df = _make_df()
    result = _make_result()

    with (
        patch("stockanalyzer.gui.worker.resolve_ticker", return_value=("AAPL", "Apple Inc.")),
        patch("stockanalyzer.gui.worker.fetch_ohlcv", return_value=df),
        patch("stockanalyzer.gui.worker.analyze", return_value=result),
    ):
        window._on_analyze_clicked()
        with qtbot.waitSignal(window._worker.succeeded, timeout=5000):
            pass

    assert window.direction_label.text() == "BULLISH"
    assert window.symbol_label.text() == "AAPL — Apple Inc."
    assert len(window.chart_ax_price.get_lines()) == 3
    assert window.chart_ax_price.get_title() == "AAPL"


def test_watchlist_run_populates_table(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.watchlist_tickers_list.addItems(["AAPL", "MSFT"])

    df = _make_df()
    result = _make_result()

    with (
        patch(
            "stockanalyzer.gui.worker.resolve_ticker",
            side_effect=lambda q: (q.upper(), f"{q.upper()} Inc."),
        ),
        patch("stockanalyzer.gui.worker.fetch_ohlcv", return_value=df),
        patch("stockanalyzer.gui.worker.analyze", return_value=result),
    ):
        window._on_watchlist_run()
        qtbot.waitUntil(lambda: window.watchlist_table.rowCount() == 2, timeout=5000)

    assert window.watchlist_run_button.isEnabled()
    tickers_in_table = {window.watchlist_table.item(r, 0).text() for r in range(2)}
    assert tickers_in_table == {"AAPL", "MSFT"}


def test_watchlist_run_reports_errors_without_stopping(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.watchlist_tickers_list.addItems(["BADTICKER"])

    with patch("stockanalyzer.gui.worker.resolve_ticker", side_effect=ValueError("boom")):
        window._on_watchlist_run()
        qtbot.waitUntil(lambda: window.watchlist_table.rowCount() == 1, timeout=5000)

    assert "Errore" in window.watchlist_table.item(0, 1).text()


def test_settings_persist_across_windows(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.ticker_input.setText("MSFT")
    idx = next(i for i in range(window.period_combo.count()) if window.period_combo.itemData(i) == "6mo")
    window.period_combo.setCurrentIndex(idx)
    window.watchlist_tickers_list.addItems(["AAPL", "MSFT"])
    window._save_settings()

    restored = MainWindow()
    qtbot.addWidget(restored)

    assert restored.ticker_input.text() == "MSFT"
    assert restored.period_combo.currentData() == "6mo"
    assert restored.interval_combo.currentData() == "60m"
    assert restored._watchlist_tickers() == ["AAPL", "MSFT"]


def test_defaults_to_light_theme(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    assert window._theme == "light"
    assert window.light_theme_action.isChecked()
    assert not window.dark_theme_action.isChecked()


def test_switching_to_dark_theme_updates_app_stylesheet_and_menu(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.dark_theme_action.trigger()

    assert window._theme == "dark"
    assert window.dark_theme_action.isChecked()
    assert not window.light_theme_action.isChecked()
    assert QApplication.instance().styleSheet() == DARK_STYLESHEET


def test_theme_choice_persists_across_windows(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.dark_theme_action.trigger()
    window._save_settings()

    restored = MainWindow()
    qtbot.addWidget(restored)

    assert restored._theme == "dark"
    assert restored.dark_theme_action.isChecked()


def test_guide_dialog_is_a_fixed_size_scrollable_dialog_not_fullscreen(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    dialog = window._build_guide_dialog()
    qtbot.addWidget(dialog)

    assert dialog.size().width() < 1000
    assert dialog.size().height() < 1000
    text_browsers = dialog.findChildren(QTextBrowser)
    assert len(text_browsers) == 1
    assert "Backtest" in text_browsers[0].toHtml()


def test_update_notification_shown_when_newer_version_available(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    info = UpdateInfo(version="9.9.9", url="https://example.invalid/releases/v9.9.9")

    with patch.object(QMessageBox, "exec", return_value=QMessageBox.StandardButton.Ok) as mock_exec:
        window._on_update_checked(info)

    mock_exec.assert_called_once()


def test_no_notification_when_already_up_to_date(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    with patch.object(QMessageBox, "exec") as mock_exec:
        window._on_update_checked(None)

    mock_exec.assert_not_called()


def test_check_for_updates_runs_off_the_ui_thread_and_reports_back(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    info = UpdateInfo(version="9.9.9", url="https://example.invalid/releases/v9.9.9")

    with (
        patch("stockanalyzer.gui.worker.check_for_update", return_value=info),
        patch.object(QMessageBox, "exec", return_value=QMessageBox.StandardButton.Ok) as mock_exec,
    ):
        window._check_for_updates()
        # isFinished() only means the worker thread's run() returned; the
        # checked signal it emits is delivered to _on_update_checked via a
        # queued cross-thread connection, so wait for that slot's own
        # observable effect instead of the thread state, or the still-queued
        # (and by then unpatched) QMessageBox.exec() fires during a later test.
        qtbot.waitUntil(lambda: mock_exec.called, timeout=5000)


def test_double_clicking_watchlist_row_loads_it_into_analysis_and_chart(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.watchlist_tickers_list.addItems(["AAPL"])

    df = _make_df()
    result = _make_result()

    with (
        patch("stockanalyzer.gui.worker.resolve_ticker", return_value=("AAPL", "Apple Inc.")),
        patch("stockanalyzer.gui.worker.fetch_ohlcv", return_value=df),
        patch("stockanalyzer.gui.worker.analyze", return_value=result),
    ):
        window._on_watchlist_run()
        qtbot.waitUntil(lambda: window.watchlist_table.rowCount() == 1, timeout=5000)

        window._on_watchlist_row_double_clicked(0, 0)
        qtbot.waitUntil(lambda: window.direction_label.text() == "BULLISH", timeout=5000)

    assert window.tabs.currentIndex() == 0
    assert window.ticker_input.text() == "AAPL"
    assert len(window.chart_ax_price.get_lines()) == 3


def test_load_selected_watchlist_row_button(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.watchlist_tickers_list.addItems(["MSFT"])

    df = _make_df()
    result = _make_result()

    with (
        patch("stockanalyzer.gui.worker.resolve_ticker", return_value=("MSFT", "Microsoft Corp.")),
        patch("stockanalyzer.gui.worker.fetch_ohlcv", return_value=df),
        patch("stockanalyzer.gui.worker.analyze", return_value=result),
    ):
        window._on_watchlist_run()
        qtbot.waitUntil(lambda: window.watchlist_table.rowCount() == 1, timeout=5000)

        window.watchlist_table.selectRow(0)
        window._on_watchlist_load_selected()
        qtbot.waitUntil(lambda: window.direction_label.text() == "BULLISH", timeout=5000)

    assert window.tabs.currentIndex() == 0
    assert window.ticker_input.text() == "MSFT"


def test_loading_errored_watchlist_row_shows_status_message_without_switching_tabs(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.watchlist_tickers_list.addItems(["BADTICKER"])
    window.tabs.setCurrentIndex(2)

    with patch("stockanalyzer.gui.worker.resolve_ticker", side_effect=ValueError("boom")):
        window._on_watchlist_run()
        qtbot.waitUntil(lambda: window.watchlist_table.rowCount() == 1, timeout=5000)

        window._on_watchlist_row_double_clicked(0, 0)

    assert window.tabs.currentIndex() == 2  # unchanged, no valid result to load
