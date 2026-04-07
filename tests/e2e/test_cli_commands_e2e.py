"""E2E tests for CLI commands: type, key, text, state.

Exercises the basic interaction and state-reading commands against
the real sample app via AT-SPI and xdotool inside the VM.
"""

from __future__ import annotations

import os
import subprocess
import time

import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not os.environ.get("DISPLAY"),
        reason="E2E tests require Xvfb (run in VM via 'make test-e2e')",
    ),
]


def _run_cli(*args: str, timeout: int = 15, app: str | None = "main.py") -> subprocess.CompletedProcess[str]:
    """Run a qt-ai-dev-tools CLI command.

    By default injects ``--app main.py`` so the command targets the test's
    Qt app.  Pass ``app=None`` for commands that don't accept ``--app``.
    """
    app_args: tuple[str, ...] = ("--app", app) if app is not None else ()
    cmd = ["python3", "-m", "qt_ai_dev_tools", *args, *app_args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


def _bridge_eval(code: str) -> str | None:
    """Eval code via bridge and return the result string, or None on error."""
    from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket

    sock = find_bridge_socket()
    if sock is None:
        return None
    resp = eval_code(sock, code)
    if not resp.ok:
        return None
    return resp.result


def _clear_app_state(bridge_app: subprocess.Popen[str]) -> None:
    """Reset the sample app to a clean state via bridge."""
    from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket

    _ = bridge_app  # ensure fixture is active
    sock = find_bridge_socket()
    assert sock is not None, "No bridge socket found"
    eval_code(sock, "widgets['text_input'].clear()")
    eval_code(sock, "widgets['item_list'].clear()")
    count_text = "\u042d\u043b\u0435\u043c\u0435\u043d\u0442\u043e\u0432: 0"
    eval_code(sock, f"widgets['count_label'].setText('{count_text}')")
    eval_code(sock, "widgets['status_label'].setText('\u0413\u043e\u0442\u043e\u0432')")
    time.sleep(0.3)


class TestTypeCommand:
    """Test the 'type' CLI command for typing text into widgets."""

    def test_type_text_into_input(self, bridge_app: subprocess.Popen[str]) -> None:
        """Focus the text input via fill, type text, verify via bridge."""
        _clear_app_state(bridge_app)

        # Use fill to focus and type (fill = focus + clear + type)
        result = _run_cli("fill", "hello from type test", "--role", "text")
        assert result.returncode == 0, f"fill failed: {result.stderr}"

        time.sleep(0.3)
        text = _bridge_eval("widgets['text_input'].text()")
        assert text is not None
        assert "hello from type test" in text

    def test_key_press_return(self, bridge_app: subprocess.Popen[str]) -> None:
        """Type text then press Return to add a todo item."""
        _clear_app_state(bridge_app)

        # Fill text into input
        fill_result = _run_cli("fill", "key-test-item", "--role", "text")
        assert fill_result.returncode == 0, f"fill failed: {fill_result.stderr}"
        time.sleep(0.3)

        # Press Return to submit (the app's returnPressed signal triggers _on_add)
        key_result = _run_cli("key", "Return", app=None)
        assert key_result.returncode == 0, f"key failed: {key_result.stderr}"

        time.sleep(0.5)
        count = _bridge_eval("widgets['item_list'].count()")
        assert count is not None
        assert int(count) >= 1, f"Expected at least 1 item after Return, got {count}"

    def test_type_with_app_targeting(self, bridge_app: subprocess.Popen[str]) -> None:
        """Activate the app window by name, then type into it."""
        _clear_app_state(bridge_app)

        from qt_ai_dev_tools.interact import activate_app_window

        # Activate window to ensure focus
        activate_app_window("Qt Dev Proto")
        time.sleep(0.3)

        # Focus the input field and type
        result = _run_cli("fill", "targeted-text", "--role", "text")
        assert result.returncode == 0, f"fill failed: {result.stderr}"

        time.sleep(0.3)
        text = _bridge_eval("widgets['text_input'].text()")
        assert text is not None
        assert "targeted-text" in text


class TestTextAndState:
    """Test reading text content and widget state via AT-SPI."""

    def test_get_text_content(self, bridge_app: subprocess.Popen[str]) -> None:
        """Read text from a label widget using pilot.get_text()."""
        _clear_app_state(bridge_app)

        from qt_ai_dev_tools.pilot import QtPilot

        pilot = QtPilot(app_name="main.py")
        # Find the status label — its initial text is "Готов" (Ready)
        labels = pilot.find(role="label", name="\u0413\u043e\u0442\u043e\u0432")
        assert len(labels) >= 1, "Expected to find the status label with text '\u0413\u043e\u0442\u043e\u0432'"

        text = pilot.get_text(labels[0])
        assert "\u0413\u043e\u0442\u043e\u0432" in text

    def test_get_widget_state(self, bridge_app: subprocess.Popen[str]) -> None:
        """Read widget state (name, role, extents) and verify values."""
        from qt_ai_dev_tools import state
        from qt_ai_dev_tools.pilot import QtPilot

        pilot = QtPilot(app_name="main.py")
        # Find the Add button (Добавить)
        buttons = pilot.find(role="push button", name="\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c")
        assert len(buttons) >= 1, "Expected to find the Add button"

        btn = buttons[0]
        name = state.get_name(btn)
        role = state.get_role(btn)
        extents = state.get_extents(btn)

        assert "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c" in name
        assert role == "push button"
        assert extents.width > 0
        assert extents.height > 0
        assert extents.x >= 0
        assert extents.y >= 0

    def test_state_cli_json_output(self, bridge_app: subprocess.Popen[str]) -> None:
        """The state --json CLI command returns valid JSON with widget info."""
        import json

        result = _run_cli(
            "state", "--role", "push button",
            "--name", "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c", "--json",
        )
        assert result.returncode == 0, f"state --json failed: {result.stderr}"

        data = json.loads(result.stdout)
        assert "name" in data
        assert "role" in data
        assert "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c" in data["name"]
        assert data["role"] == "push button"
