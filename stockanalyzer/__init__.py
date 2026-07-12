from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from .data import fetch_ohlcv, resolve_ticker
from .engine import AnalysisResult, Leg, analyze

try:
    __version__ = _pkg_version("stockanalyzer")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = ["fetch_ohlcv", "resolve_ticker", "analyze", "AnalysisResult", "Leg", "__version__"]
