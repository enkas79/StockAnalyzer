import io
import json
from unittest.mock import patch

from stockanalyzer.updater import UpdateInfo, check_for_update


def _fake_response(payload: dict):
    class _CM:
        def __enter__(self_inner):
            return io.BytesIO(json.dumps(payload).encode("utf-8"))

        def __exit__(self_inner, *args):
            return False

    return _CM()


def test_check_for_update_returns_none_when_already_latest():
    payload = {"tag_name": "v0.2.0", "html_url": "https://example.invalid/releases/v0.2.0"}
    with patch("stockanalyzer.updater.urllib.request.urlopen", return_value=_fake_response(payload)):
        assert check_for_update("0.2.0") is None


def test_check_for_update_returns_info_when_newer_release_exists():
    payload = {"tag_name": "v0.3.0", "html_url": "https://example.invalid/releases/v0.3.0"}
    with patch("stockanalyzer.updater.urllib.request.urlopen", return_value=_fake_response(payload)):
        result = check_for_update("0.2.0")

    assert result == UpdateInfo(version="0.3.0", url="https://example.invalid/releases/v0.3.0")


def test_check_for_update_returns_none_when_current_is_newer():
    payload = {"tag_name": "v0.1.0", "html_url": "https://example.invalid/releases/v0.1.0"}
    with patch("stockanalyzer.updater.urllib.request.urlopen", return_value=_fake_response(payload)):
        assert check_for_update("0.2.0") is None


def test_check_for_update_returns_none_on_network_failure():
    with patch("stockanalyzer.updater.urllib.request.urlopen", side_effect=OSError("no network")):
        assert check_for_update("0.2.0") is None


def test_check_for_update_returns_none_on_malformed_payload():
    with patch("stockanalyzer.updater.urllib.request.urlopen", return_value=_fake_response({})):
        assert check_for_update("0.2.0") is None
