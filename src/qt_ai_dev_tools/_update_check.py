"""Check PyPI for a newer version and return a notice if available.

Caches the result in ``~/.local/state/qt-ai-dev-tools/version-check.json``
so PyPI is hit at most once per day.  Network/parse failures are silently
swallowed — the version check must never break the actual command.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from qt_ai_dev_tools.__version__ import __version__

logger = logging.getLogger(__name__)

_PYPI_URL = "https://pypi.org/pypi/qt-ai-dev-tools/json"
_TIMEOUT_SECONDS = 3
_CACHE_TTL = timedelta(hours=24)
_CACHE_DIR = Path("~/.local/state/qt-ai-dev-tools").expanduser()
_CACHE_FILE = _CACHE_DIR / "version-check.json"


@dataclass(frozen=True, slots=True)
class _CachedCheck:
    """Result of a previous PyPI version check."""

    latest_version: str
    checked_at: str  # ISO-8601 UTC timestamp


def _parse_version(version_str: str) -> tuple[int, ...]:
    """Split a version string into a comparable tuple of ints.

    Non-numeric segments (e.g. ``"rc1"``) are dropped so that pre-release
    versions compare lower than their release counterpart.
    """
    parts: list[int] = []
    for segment in version_str.split("."):
        try:
            parts.append(int(segment))
        except ValueError:
            break
    return tuple(parts)


def _parse_json_dict(raw: str | bytes) -> dict[str, object] | None:
    """Parse JSON, returning a str-keyed dict or ``None`` if it isn't one.

    Typed boundary for ``json.loads`` — isolates the ``Any`` return.
    """
    data: dict[str, object] = json.loads(raw)  # type: ignore[reportAny]  # rationale: json.loads returns Any; JSON objects always have str keys
    if not isinstance(data, dict):
        return None
    return data


def _read_cache() -> _CachedCheck | None:
    """Read the cached version check, returning ``None`` if stale or absent."""
    try:
        raw = _CACHE_FILE.read_text(encoding="utf-8")
        data = _parse_json_dict(raw)
        if data is None:
            return None
        latest = data.get("latest_version")
        checked = data.get("checked_at")
        if not isinstance(latest, str) or not isinstance(checked, str):
            return None
        checked_dt = datetime.fromisoformat(checked)
        if datetime.now(UTC) - checked_dt > _CACHE_TTL:
            return None
        return _CachedCheck(latest_version=latest, checked_at=checked)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _write_cache(latest_version: str) -> None:
    """Persist a version check result to disk."""
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "latest_version": latest_version,
            "checked_at": datetime.now(UTC).isoformat(),
        }
        _CACHE_FILE.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        pass  # best-effort


def _fetch_latest_version() -> str | None:
    """Query PyPI for the latest version, returning ``None`` on any failure."""
    try:
        req = urllib.request.Request(_PYPI_URL, headers={"Accept": "application/json"})  # noqa: S310
        resp = urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS)  # type: ignore[reportAny]  # rationale: urlopen returns HTTPResponse typed as Any in stubs  # noqa: S310
        try:
            body: bytes = resp.read()  # type: ignore[reportAny]  # rationale: urlopen returns http.client.HTTPResponse; read() typed as Any in stubs
        finally:
            resp.close()  # type: ignore[reportAny]  # rationale: same Any boundary as read()
        data = _parse_json_dict(body)
        if data is None:
            return None
        info = data.get("info")
        if not isinstance(info, dict):
            return None
        # info is dict[str | int | float | bool | None, object] after isinstance;
        # we only access string keys which always exist in JSON objects
        version = info.get("version")  # type: ignore[reportUnknownMemberType]  # rationale: isinstance narrows to dict[Unknown, Unknown]; JSON dicts always have str keys
        if not isinstance(version, str):
            return None
        return version
    except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError, KeyError):
        logger.debug("PyPI version check failed", exc_info=True)
        return None


def check_for_update() -> str | None:
    """Return a one-line update notice, or ``None`` if up-to-date / check skipped.

    Safe to call unconditionally — all errors are suppressed.
    """
    try:
        cached = _read_cache()
        if cached is not None:
            latest = cached.latest_version
        else:
            latest = _fetch_latest_version()
            if latest is None:
                return None
            _write_cache(latest)

        if _parse_version(latest) > _parse_version(__version__):
            return (
                f"Notice: qt-ai-dev-tools {latest} is available (current: {__version__}). "
                f"Update: uv tool install --upgrade qt-ai-dev-tools, "
                f"or uvx qt-ai-dev-tools@latest, or update with your package manager."
            )
        return None
    except Exception:
        logger.debug("Update check failed unexpectedly", exc_info=True)
        return None
