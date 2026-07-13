from unittest.mock import patch

from stockanalyzer.data import resolve_ticker, search_candidates


class _FakeSearch:
    def __init__(self, quotes):
        self.quotes = quotes


def test_search_candidates_maps_yahoo_quotes():
    quotes = [
        {"symbol": "ENI.MI", "shortname": "Eni S.p.A.", "exchDisp": "Milan"},
        {"symbol": "E", "shortname": "Eni SpA", "exchDisp": "NYSE"},
        {"shortname": "No symbol here"},  # should be skipped
    ]
    with patch("stockanalyzer.data.yf.Search", return_value=_FakeSearch(quotes)):
        candidates = search_candidates("eni")

    assert candidates == [
        {"symbol": "ENI.MI", "name": "Eni S.p.A.", "exchange": "Milan"},
        {"symbol": "E", "name": "Eni SpA", "exchange": "NYSE"},
    ]


def test_search_candidates_returns_empty_list_on_no_query():
    assert search_candidates("   ") == []


def test_search_candidates_returns_empty_list_on_network_failure():
    with patch("stockanalyzer.data.yf.Search", side_effect=RuntimeError("boom")):
        assert search_candidates("eni") == []


def test_resolve_ticker_picks_best_match_from_search():
    quotes = [{"symbol": "ENI.MI", "shortname": "Eni S.p.A.", "exchDisp": "Milan"}]
    with patch("stockanalyzer.data.yf.Search", return_value=_FakeSearch(quotes)):
        symbol, name = resolve_ticker("eni")

    assert symbol == "ENI.MI"
    assert name == "Eni S.p.A."


def test_resolve_ticker_falls_back_to_uppercased_query_when_no_match():
    with patch("stockanalyzer.data.yf.Search", return_value=_FakeSearch([])):
        symbol, name = resolve_ticker("madeupticker")

    assert symbol == "MADEUPTICKER"
    assert name == "MADEUPTICKER"
