"""Tests for PyPI update check module."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from qt_ai_dev_tools import _update_check
from qt_ai_dev_tools._update_check import (
    _parse_version,
    _read_cache,
    _write_cache,
    check_for_update,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# _parse_version
# ---------------------------------------------------------------------------


class TestParseVersion:
    def test_three_part(self) -> None:
        assert _parse_version("1.2.3") == (1, 2, 3)

    def test_prerelease_suffix(self) -> None:
        assert _parse_version("1.2.3rc1") == (1, 2)

    def test_two_part(self) -> None:
        assert _parse_version("1.2") == (1, 2)

    def test_single_segment(self) -> None:
        assert _parse_version("1") == (1,)

    def test_empty_string(self) -> None:
        assert _parse_version("") == ()


# ---------------------------------------------------------------------------
# _read_cache / _write_cache
# ---------------------------------------------------------------------------


class TestCacheRoundTrip:
    def test_write_then_read(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(_update_check, "_CACHE_DIR", tmp_path)
        monkeypatch.setattr(_update_check, "_CACHE_FILE", tmp_path / "version-check.json")

        _write_cache("2.0.0")
        cached = _read_cache()

        assert cached is not None
        assert cached.latest_version == "2.0.0"

    def test_missing_file_returns_none(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(_update_check, "_CACHE_DIR", tmp_path)
        monkeypatch.setattr(_update_check, "_CACHE_FILE", tmp_path / "nonexistent.json")

        assert _read_cache() is None

    def test_expired_cache_returns_none(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        cache_file = tmp_path / "version-check.json"
        monkeypatch.setattr(_update_check, "_CACHE_DIR", tmp_path)
        monkeypatch.setattr(_update_check, "_CACHE_FILE", cache_file)

        old_time = datetime.now(UTC) - timedelta(hours=25)
        payload = {
            "latest_version": "2.0.0",
            "checked_at": old_time.isoformat(),
        }
        cache_file.write_text(json.dumps(payload), encoding="utf-8")

        assert _read_cache() is None

    def test_corrupted_json_returns_none(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        cache_file = tmp_path / "version-check.json"
        monkeypatch.setattr(_update_check, "_CACHE_DIR", tmp_path)
        monkeypatch.setattr(_update_check, "_CACHE_FILE", cache_file)

        cache_file.write_text("not valid json {{{", encoding="utf-8")

        assert _read_cache() is None


# ---------------------------------------------------------------------------
# check_for_update
# ---------------------------------------------------------------------------


class TestCheckForUpdate:
    """Monkeypatch _fetch_latest_version, cache dir, and __version__."""

    @pytest.fixture(autouse=True)
    def _isolate(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Redirect cache to tmp_path and pin __version__ to 1.0.0."""
        monkeypatch.setattr(_update_check, "_CACHE_DIR", tmp_path)
        monkeypatch.setattr(_update_check, "_CACHE_FILE", tmp_path / "version-check.json")
        monkeypatch.setattr(_update_check, "__version__", "1.0.0")

    def test_newer_version_returns_notice(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(_update_check, "_fetch_latest_version", lambda: "2.0.0")

        result = check_for_update()

        assert result is not None
        assert "2.0.0" in result
        assert "1.0.0" in result

    def test_same_version_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(_update_check, "_fetch_latest_version", lambda: "1.0.0")

        assert check_for_update() is None

    def test_current_is_newer_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(_update_check, "_fetch_latest_version", lambda: "0.9.0")

        assert check_for_update() is None

    def test_network_failure_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(_update_check, "_fetch_latest_version", lambda: None)

        assert check_for_update() is None

    def test_fresh_cache_skips_fetch(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Write a fresh cache entry for version 2.0.0
        _write_cache("2.0.0")

        fetch_called = False

        def _fake_fetch() -> str | None:
            nonlocal fetch_called
            fetch_called = True
            return "2.0.0"

        monkeypatch.setattr(_update_check, "_fetch_latest_version", _fake_fetch)

        result = check_for_update()

        assert not fetch_called, "_fetch_latest_version should not be called when cache is fresh"
        assert result is not None
        assert "2.0.0" in result

    def test_expired_cache_calls_fetch(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Write an expired cache entry
        cache_file = tmp_path / "version-check.json"
        old_time = datetime.now(UTC) - timedelta(hours=25)
        payload = {
            "latest_version": "1.5.0",
            "checked_at": old_time.isoformat(),
        }
        cache_file.write_text(json.dumps(payload), encoding="utf-8")

        fetch_called = False

        def _fake_fetch() -> str | None:
            nonlocal fetch_called
            fetch_called = True
            return "2.0.0"

        monkeypatch.setattr(_update_check, "_fetch_latest_version", _fake_fetch)

        result = check_for_update()

        assert fetch_called, "_fetch_latest_version should be called when cache is expired"
        assert result is not None
        assert "2.0.0" in result
