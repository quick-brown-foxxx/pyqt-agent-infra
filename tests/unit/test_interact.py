"""Tests for widget interaction helpers (xdotool and AT-SPI actions)."""

from __future__ import annotations

import os
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock gi and Atspi before importing interact, since gi is a system package.
_mock_gi = MagicMock()
_mock_atspi_module = MagicMock()
_mock_gi.require_version = MagicMock()
_mock_gi.repository.Atspi = _mock_atspi_module

with patch.dict(sys.modules, {"gi": _mock_gi, "gi.repository": _mock_gi.repository}):
    from qt_ai_dev_tools import interact as _interact_mod
    from qt_ai_dev_tools._atspi import AtspiNode
    from qt_ai_dev_tools.interact import (
        _xdotool_env,
        click,
        focus,
        press_key,
        type_text,
    )

_COMPLETED_OK = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
_MOUSELOCATION_RESULT = subprocess.CompletedProcess(
    args=[], returncode=0, stdout="X=125\nY=215\nSCREEN=0\nWINDOW=12345\n", stderr=""
)

pytestmark = pytest.mark.unit


class TestXdotoolEnv:
    """Test environment setup for xdotool."""

    def test_sets_display_default(self) -> None:
        """Should set DISPLAY to :99 if not already set."""
        with patch.dict(os.environ, {}, clear=True):
            env = _xdotool_env()
            assert env["DISPLAY"] == ":99"

    def test_preserves_existing_display(self) -> None:
        """Should not override an existing DISPLAY variable."""
        with patch.dict(os.environ, {"DISPLAY": ":0"}, clear=False):
            env = _xdotool_env()
            assert env["DISPLAY"] == ":0"


class TestClick:
    """Test xdotool click on widget center."""

    def test_click_computes_center_and_calls_xdotool(self) -> None:
        """Should compute widget center and invoke xdotool mousemove + focus + click."""
        native = MagicMock()
        ext = MagicMock()
        ext.x = 100
        ext.y = 200
        ext.width = 50
        ext.height = 30
        native.get_extents.return_value = ext
        node = AtspiNode(native)

        def _side_effect(args: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
            if "getmouselocation" in args:
                return _MOUSELOCATION_RESULT
            return _COMPLETED_OK

        with patch.object(_interact_mod, "run_command") as mock_run:
            mock_run.side_effect = _side_effect
            click(node, pause=0.0)

            # Center should be (125, 215)
            calls = mock_run.call_args_list
            assert len(calls) == 4
            # 1. mousemove
            assert calls[0][0][0][:2] == ["xdotool", "mousemove"]
            assert "125" in calls[0][0][0]
            assert "215" in calls[0][0][0]
            # 2. getmouselocation
            assert calls[1][0][0] == ["xdotool", "getmouselocation", "--shell"]
            # 3. windowfocus
            assert calls[2][0][0] == ["xdotool", "windowfocus", "12345"]
            # 4. click
            assert calls[3][0][0] == ["xdotool", "click", "1"]


class TestTypeText:
    """Test xdotool text typing."""

    def test_type_text_calls_xdotool(self) -> None:
        """Should invoke xdotool type with the given text."""
        with patch.object(_interact_mod, "run_command") as mock_run:
            mock_run.return_value = _COMPLETED_OK
            type_text("hello world", delay_ms=10, pause=0.0)

            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == "xdotool"
            assert args[1] == "type"
            assert "hello world" in args


class TestPressKey:
    """Test xdotool key press."""

    def test_press_key_calls_xdotool(self) -> None:
        """Should invoke xdotool key with the key name."""
        with patch.object(_interact_mod, "run_command") as mock_run:
            mock_run.return_value = _COMPLETED_OK
            press_key("Return", pause=0.0)

            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args == ["xdotool", "key", "Return"]

    def test_press_key_combo(self) -> None:
        """Should handle key combinations like ctrl+a."""
        with patch.object(_interact_mod, "run_command") as mock_run:
            mock_run.return_value = _COMPLETED_OK
            press_key("ctrl+a", pause=0.0)

            args = mock_run.call_args[0][0]
            assert args == ["xdotool", "key", "ctrl+a"]


class TestFocus:
    """Test widget focus via AT-SPI action with click fallback."""

    def test_focus_uses_setfocus_action(self) -> None:
        """Should try AT-SPI SetFocus action first."""
        native = MagicMock()
        action_iface = MagicMock()
        native.get_action_iface.return_value = action_iface
        action_iface.get_n_actions.return_value = 1
        action_iface.get_action_name.return_value = "SetFocus"
        node = AtspiNode(native)

        with patch.object(_interact_mod.time, "sleep"):
            focus(node, pause=0.0)
            action_iface.do_action.assert_called_once_with(0)

    def test_focus_falls_back_to_click(self) -> None:
        """Should fall back to click when SetFocus action fails."""
        native = MagicMock()
        native.get_action_iface.return_value = None  # No action interface

        ext = MagicMock()
        ext.x = 10
        ext.y = 20
        ext.width = 100
        ext.height = 50
        native.get_extents.return_value = ext

        node = AtspiNode(native)

        focus_mouselocation = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="X=60\nY=45\nSCREEN=0\nWINDOW=99999\n", stderr=""
        )

        def _side_effect(args: list[str], **_kw: object) -> subprocess.CompletedProcess[str]:
            if "getmouselocation" in args:
                return focus_mouselocation
            return _COMPLETED_OK

        with patch.object(_interact_mod, "run_command") as mock_run:
            mock_run.side_effect = _side_effect
            focus(node, pause=0.0)

            # Should have called xdotool mousemove + getmouselocation + windowfocus + click
            # Center of (10, 20, 100, 50) = (60, 45)
            calls = mock_run.call_args_list
            assert len(calls) == 4
            assert calls[0][0][0][:2] == ["xdotool", "mousemove"]
            assert "60" in calls[0][0][0]
            assert "45" in calls[0][0][0]
            assert calls[1][0][0] == ["xdotool", "getmouselocation", "--shell"]
            assert calls[2][0][0] == ["xdotool", "windowfocus", "99999"]
            assert calls[3][0][0] == ["xdotool", "click", "1"]
