"""Tests for stability classification."""

from __future__ import annotations

import pytest

from qt_ai_dev_tools._stability import Stability, get_stability, warn_if_alpha

pytestmark = pytest.mark.unit


class TestGetStability:
    """Tests for get_stability()."""

    def test_core_commands_are_beta(self) -> None:
        assert get_stability("tree") == Stability.BETA
        assert get_stability("click") == Stability.BETA
        assert get_stability("fill") == Stability.BETA

    def test_subsystem_commands_are_alpha(self) -> None:
        assert get_stability("clipboard read") == Stability.ALPHA
        assert get_stability("clipboard write") == Stability.ALPHA
        assert get_stability("tray list") == Stability.ALPHA
        assert get_stability("tray click") == Stability.ALPHA
        assert get_stability("tray menu") == Stability.ALPHA
        assert get_stability("tray select") == Stability.ALPHA
        assert get_stability("audio record") == Stability.ALPHA
        assert get_stability("audio verify") == Stability.ALPHA
        assert get_stability("audio sources") == Stability.ALPHA
        assert get_stability("audio status") == Stability.ALPHA
        assert get_stability("audio virtual-mic start") == Stability.ALPHA
        assert get_stability("audio virtual-mic stop") == Stability.ALPHA
        assert get_stability("audio virtual-mic play") == Stability.ALPHA
        assert get_stability("notify listen") == Stability.ALPHA
        assert get_stability("notify dismiss") == Stability.ALPHA
        assert get_stability("notify action") == Stability.ALPHA
        assert get_stability("file-dialog detect") == Stability.ALPHA
        assert get_stability("file-dialog fill") == Stability.ALPHA
        assert get_stability("file-dialog accept") == Stability.ALPHA
        assert get_stability("file-dialog cancel") == Stability.ALPHA

    def test_unknown_commands_default_to_beta(self) -> None:
        assert get_stability("nonexistent") == Stability.BETA


class TestWarnIfAlpha:
    """Tests for warn_if_alpha()."""

    def test_alpha_command_prints_warning(self, capsys: pytest.CaptureFixture[str]) -> None:
        warn_if_alpha("clipboard read")
        captured = capsys.readouterr()
        assert "alpha" in captured.err
        assert "clipboard read" in captured.err

    def test_beta_command_prints_nothing(self, capsys: pytest.CaptureFixture[str]) -> None:
        warn_if_alpha("tree")
        captured = capsys.readouterr()
        assert captured.err == ""
