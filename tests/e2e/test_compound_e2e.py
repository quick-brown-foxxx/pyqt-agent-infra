"""E2E tests for compound commands: fill, do, wait.

These are the primary agent workflow commands. Tests run inside the VM
against the real sample app with bridge enabled.
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


def _run_cli(*args: str, timeout: int = 15) -> subprocess.CompletedProcess[str]:
    """Run a qt-ai-dev-tools CLI command inside the VM."""
    cmd = ["python3", "-m", "qt_ai_dev_tools", *args]
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
    count_text = "\\u042d\\u043b\\u0435\\u043c\\u0435\\u043d\\u0442\\u043e\\u0432: 0"
    eval_code(sock, f"widgets['count_label'].setText('{count_text}')")
    eval_code(sock, "widgets['status_label'].setText('\\u0413\\u043e\\u0442\\u043e\\u0432')")
    # Give Qt event loop time to process
    time.sleep(0.3)


class TestFillCommand:
    """Test the 'fill' compound command: focus + clear + type."""

    def test_fill_text_into_input(self, bridge_app: subprocess.Popen[str]) -> None:
        """Fill text into the todo input field, verify via bridge."""
        _clear_app_state(bridge_app)

        result = _run_cli("fill", "hello agent", "--role", "text", "--name", "text_input")
        assert result.returncode == 0, f"fill failed: {result.stderr}"
        assert "Filled" in result.stdout

        # Verify via bridge that the text was actually set
        time.sleep(0.3)
        text = _bridge_eval("widgets['text_input'].text()")
        assert text is not None
        assert "hello agent" in text

    def test_fill_with_no_clear(self, bridge_app: subprocess.Popen[str]) -> None:
        """Fill with --no-clear preserves existing text."""
        _clear_app_state(bridge_app)

        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket

        sock = find_bridge_socket()
        assert sock is not None
        eval_code(sock, "widgets['text_input'].setText('existing ')")
        time.sleep(0.3)

        result = _run_cli("fill", "appended", "--role", "text", "--name", "text_input", "--no-clear")
        assert result.returncode == 0, f"fill --no-clear failed: {result.stderr}"

        time.sleep(0.3)
        text = _bridge_eval("widgets['text_input'].text()")
        assert text is not None
        # With --no-clear, existing text should still be present
        assert "existing" in text

    def test_fill_nonexistent_widget_fails(self, bridge_app: subprocess.Popen[str]) -> None:
        """Fill into a widget that doesn't exist returns exit code 1."""
        result = _run_cli("fill", "text", "--role", "text", "--name", "nonexistent_widget_xyz")
        assert result.returncode == 1
        assert "Error" in result.stderr


class TestDoCommand:
    """Test the 'do' compound command: click + verify + screenshot."""

    def test_do_click_add_button(self, bridge_app: subprocess.Popen[str]) -> None:
        """Click the Add button via 'do click' and verify side effect."""
        _clear_app_state(bridge_app)

        # First fill in some text so clicking Add does something
        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket

        sock = find_bridge_socket()
        assert sock is not None
        eval_code(sock, "widgets['text_input'].setText('do-test-item')")
        time.sleep(0.3)

        # Use the Russian button name from the app
        result = _run_cli(
            "do",
            "click",
            "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c",
            "--role",
            "push button",
        )
        assert result.returncode == 0, f"do click failed: {result.stderr}"
        assert "Clicked" in result.stdout

        # Verify item was added via bridge
        time.sleep(0.3)
        count = _bridge_eval("widgets['item_list'].count()")
        assert count is not None
        assert int(count) >= 1

    def test_do_click_with_verify_pass(self, bridge_app: subprocess.Popen[str]) -> None:
        """Click Add with --verify checking the status label succeeds."""
        _clear_app_state(bridge_app)

        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket

        sock = find_bridge_socket()
        assert sock is not None
        eval_code(sock, "widgets['text_input'].setText('verify-item')")
        time.sleep(0.3)

        result = _run_cli(
            "do",
            "click",
            "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c",
            "--role",
            "push button",
            "--verify",
            "label:status_label contains verify-item",
        )
        assert result.returncode == 0, f"do click --verify failed: {result.stderr}"
        assert "Verify OK" in result.stdout

    def test_do_click_with_verify_fail(self, bridge_app: subprocess.Popen[str]) -> None:
        """Click with --verify that doesn't match returns exit code 1."""
        _clear_app_state(bridge_app)

        result = _run_cli(
            "do",
            "click",
            "\u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c",
            "--role",
            "push button",
            "--verify",
            "label:status_label contains NONEXISTENT_TEXT_XYZ",
        )
        assert result.returncode == 1
        assert "Verify FAILED" in result.stderr

    def test_do_click_with_screenshot(self, bridge_app: subprocess.Popen[str]) -> None:
        """Click with --screenshot creates a screenshot file."""
        _clear_app_state(bridge_app)

        result = _run_cli(
            "do",
            "click",
            "\u041e\u0447\u0438\u0441\u0442\u0438\u0442\u044c",
            "--role",
            "push button",
            "--screenshot",
        )
        assert result.returncode == 0, f"do click --screenshot failed: {result.stderr}"
        assert "Screenshot" in result.stdout
        assert ".png" in result.stdout

    def test_do_unknown_action_fails(self, bridge_app: subprocess.Popen[str]) -> None:
        """An unknown action (not 'click') returns exit code 1."""
        result = _run_cli("do", "drag", "something")
        assert result.returncode == 1
        assert "Unknown action" in result.stderr


class TestWaitCommand:
    """Test the 'wait' command: wait for app on AT-SPI bus."""

    def test_wait_for_running_app(self, bridge_app: subprocess.Popen[str]) -> None:
        """Wait for main.py which is already running exits 0."""
        result = _run_cli("wait", "--app", "main.py", "--timeout", "5")
        assert result.returncode == 0, f"wait failed: {result.stderr}"
        assert "Found" in result.stdout

    def test_wait_for_nonexistent_app_times_out(self, bridge_app: subprocess.Popen[str]) -> None:
        """Wait for an app that doesn't exist times out with exit code 1."""
        result = _run_cli("wait", "--app", "nonexistent_app_xyz", "--timeout", "2")
        assert result.returncode == 1
        assert "Timeout" in result.stderr
