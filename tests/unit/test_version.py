"""Tests for package version module."""

from __future__ import annotations

import re

import pytest

from qt_ai_dev_tools.__version__ import __commit__, __version__

pytestmark = pytest.mark.unit


class TestVersion:
    def test_version_is_nonempty_string(self) -> None:
        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_version_matches_semver_or_dev(self) -> None:
        """Version is either semver-like (x.y.z) or the dev fallback."""
        assert re.match(r"\d+\.\d+\.\d+", __version__) or __version__ == "0.0.0-dev"


class TestCommit:
    def test_commit_is_string(self) -> None:
        assert isinstance(__commit__, str)

    def test_commit_is_dev_or_hex_hash(self) -> None:
        """Commit is 'dev' during development, or a short hex hash in production."""
        assert __commit__ == "dev" or re.fullmatch(r"[0-9a-f]{7,12}", __commit__)
