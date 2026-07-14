from importlib.metadata import PackageNotFoundError
from unittest.mock import patch

from stockanalyzer import _read_version


def test_read_version_uses_installed_package_metadata():
    with patch("stockanalyzer._pkg_version", return_value="1.2.3"):
        assert _read_version() == "1.2.3"


def test_read_version_falls_back_to_bundled_version_txt_when_metadata_missing(tmp_path):
    (tmp_path / "version.txt").write_text("9.9.9\n", encoding="utf-8")
    with (
        patch("stockanalyzer._pkg_version", side_effect=PackageNotFoundError("stockanalyzer")),
        patch("stockanalyzer.sys") as mock_sys,
    ):
        mock_sys._MEIPASS = str(tmp_path)
        assert _read_version() == "9.9.9"


def test_read_version_falls_back_to_0_0_0_when_nothing_available(tmp_path):
    with (
        patch("stockanalyzer._pkg_version", side_effect=PackageNotFoundError("stockanalyzer")),
        patch("stockanalyzer.sys") as mock_sys,
    ):
        mock_sys._MEIPASS = str(tmp_path)  # empty dir, no version.txt in it
        assert _read_version() == "0.0.0"
