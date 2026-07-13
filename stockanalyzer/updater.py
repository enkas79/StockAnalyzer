"""Startup update check against GitHub Releases.

Deliberately does not download or replace anything on its own: replacing an
installed binary automatically is platform-specific and risky, so this only
tells the caller a newer version exists and where to get it.
"""

import json
import urllib.request
from dataclasses import dataclass

GITHUB_REPO = "enkas79/StockAnalyzer"
_RELEASES_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


@dataclass
class UpdateInfo:
    version: str
    url: str


def _parse_version(tag: str) -> tuple[int, ...]:
    """"v1.2.3" / "1.2.3" -> (1, 2, 3); non-numeric segments become 0."""
    cleaned = tag.lstrip("vV")
    parts = []
    for chunk in cleaned.split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def check_for_update(current_version: str, timeout: float = 5.0) -> UpdateInfo | None:
    """Return the latest GitHub release if it's newer than `current_version`.

    Best-effort: any failure (offline, rate-limited, no releases yet, ...)
    returns None instead of raising, so a broken check never blocks or
    crashes startup.
    """
    try:
        request = urllib.request.Request(
            _RELEASES_API_URL, headers={"Accept": "application/vnd.github+json"}
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed https host
            payload = json.load(response)
    except Exception:
        return None

    tag = payload.get("tag_name")
    url = payload.get("html_url")
    if not tag or not url:
        return None

    if _parse_version(tag) > _parse_version(current_version):
        return UpdateInfo(version=tag.lstrip("vV"), url=url)
    return None
