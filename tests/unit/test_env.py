"""Tests for centralized env var registry."""

from __future__ import annotations

import pytest

from qt_ai_dev_tools._env import (
    ALLOW_VERSION_MISMATCH,
    BRIDGE,
    DISPLAY,
    VM,
    get_bool,
    get_str,
)

pytestmark = pytest.mark.unit


class TestEnvVarDefinitions:
    def test_vm_var(self) -> None:
        assert VM.name == "QT_AI_DEV_TOOLS_VM"
        assert VM.description != ""

    def test_bridge_var(self) -> None:
        assert BRIDGE.name == "QT_AI_DEV_TOOLS_BRIDGE"
        assert BRIDGE.description != ""

    def test_allow_version_mismatch_var(self) -> None:
        assert ALLOW_VERSION_MISMATCH.name == "QT_AI_DEV_TOOLS_ALLOW_VERSION_MISMATCH"
        assert ALLOW_VERSION_MISMATCH.description != ""

    def test_display_var(self) -> None:
        assert DISPLAY.name == "DISPLAY"
        assert DISPLAY.description != ""

    def test_frozen(self) -> None:
        with pytest.raises(AttributeError):
            VM.name = "OTHER"  # type: ignore[misc]


class TestGetBool:
    def test_returns_true_for_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("QT_AI_DEV_TOOLS_VM", "1")
        assert get_bool(VM) is True

    def test_returns_false_for_0(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("QT_AI_DEV_TOOLS_VM", "0")
        assert get_bool(VM) is False

    def test_returns_false_for_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("QT_AI_DEV_TOOLS_VM", "")
        assert get_bool(VM) is False

    def test_returns_false_for_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("QT_AI_DEV_TOOLS_VM", raising=False)
        assert get_bool(VM) is False

    def test_returns_true_for_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("QT_AI_DEV_TOOLS_VM", "true")
        assert get_bool(VM) is True

    def test_returns_true_for_true_uppercase(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("QT_AI_DEV_TOOLS_VM", "TRUE")
        assert get_bool(VM) is True

    def test_returns_true_for_yes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("QT_AI_DEV_TOOLS_VM", "yes")
        assert get_bool(VM) is True

    def test_returns_true_for_yes_mixed_case(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("QT_AI_DEV_TOOLS_VM", "Yes")
        assert get_bool(VM) is True


class TestGetStr:
    def test_returns_set_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DISPLAY", ":99")
        assert get_str(DISPLAY) == ":99"

    def test_returns_envvar_default_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DISPLAY", raising=False)
        assert get_str(DISPLAY) == ""

    def test_returns_custom_default_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DISPLAY", raising=False)
        assert get_str(DISPLAY, default=":0") == ":0"

    def test_custom_default_none_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DISPLAY", raising=False)
        assert get_str(DISPLAY, default=None) == ""
