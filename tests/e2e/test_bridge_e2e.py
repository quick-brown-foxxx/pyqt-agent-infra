"""E2E tests for bridge eval -- runs inside VM against real PySide6 app."""

from __future__ import annotations

import json
import os
import subprocess

import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not os.environ.get("DISPLAY"),
        reason="E2E tests require Xvfb (run in VM via 'make test-e2e')",
    ),
]


class TestBridgeEval:
    """Test eval via bridge client API against real running app."""

    def test_simple_expression(self, bridge_app: subprocess.Popen[str]) -> None:
        """Eval a math expression."""
        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket

        sock = find_bridge_socket()
        assert sock is not None, "No bridge socket found"
        resp = eval_code(sock, "1 + 1")
        assert resp.ok is True
        assert resp.result == "2"
        assert resp.type_name == "int"

    def test_app_window_title(self, bridge_app: subprocess.Popen[str]) -> None:
        """Access the main window title via bridge."""
        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket

        sock = find_bridge_socket()
        assert sock is not None
        resp = eval_code(sock, "widgets['MainWindow'].windowTitle()")
        assert resp.ok is True
        assert resp.result is not None
        assert "Qt Dev Proto" in resp.result

    def test_widgets_dict_populated(self, bridge_app: subprocess.Popen[str]) -> None:
        """The widgets dict contains expected widget names."""
        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket

        sock = find_bridge_socket()
        assert sock is not None
        resp = eval_code(sock, "sorted(widgets.keys())")
        assert resp.ok is True
        assert resp.result is not None
        # Sample app defines these objectNames
        for name in ["MainWindow", "status_label", "text_input", "add_btn", "item_list"]:
            assert name in resp.result, f"Expected '{name}' in widgets dict"

    def test_read_widget_text(self, bridge_app: subprocess.Popen[str]) -> None:
        """Read a label's text content."""
        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket

        sock = find_bridge_socket()
        assert sock is not None
        resp = eval_code(sock, "widgets['status_label'].text()")
        assert resp.ok is True
        assert resp.result is not None

    def test_manipulate_widget(self, bridge_app: subprocess.Popen[str]) -> None:
        """Set text on a QLineEdit and read it back."""
        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket

        sock = find_bridge_socket()
        assert sock is not None
        # Set text
        resp = eval_code(sock, "widgets['text_input'].setText('bridge test')")
        assert resp.ok is True
        # Read back
        resp = eval_code(sock, "widgets['text_input'].text()")
        assert resp.ok is True
        assert resp.result == "'bridge test'"

    def test_click_button(self, bridge_app: subprocess.Popen[str]) -> None:
        """Click a button programmatically and verify side effects."""
        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket

        sock = find_bridge_socket()
        assert sock is not None
        # Ensure text input has content
        eval_code(sock, "widgets['text_input'].setText('click test item')")
        # Get current count
        resp = eval_code(sock, "widgets['item_list'].count()")
        assert resp.ok is True
        before_count = int(resp.result or "0")
        # Click add button
        resp = eval_code(sock, "widgets['add_btn'].click()")
        assert resp.ok is True
        # Verify count increased
        resp = eval_code(sock, "widgets['item_list'].count()")
        assert resp.ok is True
        after_count = int(resp.result or "0")
        assert after_count == before_count + 1

    def test_exec_with_stdout(self, bridge_app: subprocess.Popen[str]) -> None:
        """Execute a statement with print output captured."""
        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket

        sock = find_bridge_socket()
        assert sock is not None
        resp = eval_code(sock, "x = 42; print(f'answer={x}')", mode="exec")
        assert resp.ok is True
        assert "answer=42" in resp.stdout

    def test_error_handling(self, bridge_app: subprocess.Popen[str]) -> None:
        """Runtime errors return ok=False with traceback."""
        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket

        sock = find_bridge_socket()
        assert sock is not None
        resp = eval_code(sock, "undefined_variable_xyz")
        assert resp.ok is False
        assert resp.error is not None
        assert "NameError" in resp.error

    def test_find_helper(self, bridge_app: subprocess.Popen[str]) -> None:
        """The find() namespace helper works."""
        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket

        sock = find_bridge_socket()
        assert sock is not None
        resp = eval_code(sock, "find(QPushButton, 'add_btn') is not None")
        assert resp.ok is True
        assert resp.result == "True"

    def test_underscore_variable(self, bridge_app: subprocess.Popen[str]) -> None:
        """The _ variable tracks the last eval result."""
        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket

        sock = find_bridge_socket()
        assert sock is not None
        eval_code(sock, "42")
        resp = eval_code(sock, "_")
        assert resp.ok is True
        assert resp.result == "42"


class TestBridgeCLI:
    """Test bridge CLI commands via subprocess (still inside VM)."""

    def _run_cli(self, *args: str, timeout: int = 15) -> subprocess.CompletedProcess[str]:
        """Run a qt-ai-dev-tools CLI command."""
        cmd = ["python3", "-m", "qt_ai_dev_tools", *args]
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)

    def test_eval_cli_expression(self, bridge_app: subprocess.Popen[str]) -> None:
        """CLI eval command returns result."""
        result = self._run_cli("eval", "1 + 1")
        assert result.returncode == 0
        assert "2" in result.stdout

    def test_eval_cli_json(self, bridge_app: subprocess.Popen[str]) -> None:
        """CLI eval --json returns valid JSON."""
        result = self._run_cli("eval", "--json", "1 + 1")
        assert result.returncode == 0
        data: dict[str, object] = json.loads(result.stdout)
        assert data["ok"] is True
        assert data["result"] == "2"

    def test_eval_cli_error(self, bridge_app: subprocess.Popen[str]) -> None:
        """CLI eval with bad code exits non-zero."""
        result = self._run_cli("eval", "nonexistent_var")
        assert result.returncode == 1
        assert "NameError" in result.stderr

    def test_bridge_status(self, bridge_app: subprocess.Popen[str]) -> None:
        """CLI bridge status shows active bridge."""
        result = self._run_cli("bridge", "status")
        assert result.returncode == 0
        assert "pid" in result.stdout.lower()
