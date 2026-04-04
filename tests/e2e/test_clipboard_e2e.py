"""E2E tests for clipboard subsystem -- real xclip + xdotool in VM."""

from __future__ import annotations

import os
import subprocess
import time

import pytest

pytestmark = [
    pytest.mark.skipif(
        not os.environ.get("DISPLAY"),
        reason="E2E tests require Xvfb (run in VM via 'make test-e2e')",
    ),
    pytest.mark.e2e,
]


def _run_cli(*args: str, timeout: int = 10) -> subprocess.CompletedProcess[str]:
    """Run a qt-ai-dev-tools CLI command."""
    cmd = ["python3", "-m", "qt_ai_dev_tools", *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


class TestClipboardWriteAndPaste:
    """Flow 2A: Write to clipboard + paste into app text field."""

    def test_write_to_clipboard_and_paste(self, bridge_app: subprocess.Popen[str]) -> None:
        """Write text via clipboard.write(), paste into a focused text field, verify."""
        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket
        from qt_ai_dev_tools.subsystems import clipboard

        sock = find_bridge_socket()
        assert sock is not None, "No bridge socket found"

        test_text = "hello from agent e2e"

        # Clear the text input first
        eval_code(sock, "widgets['text_input'].clear()")
        eval_code(sock, "widgets['text_input'].setFocus()")
        time.sleep(0.3)

        # Write to clipboard
        clipboard.write(test_text)

        # Paste via xdotool (ctrl+v)
        _run_cli("key", "ctrl+v")
        time.sleep(0.5)

        # Verify text field contains the pasted text
        resp = eval_code(sock, "widgets['text_input'].text()")
        assert resp.ok is True
        assert resp.result is not None
        assert test_text in resp.result


class TestClipboardCopyAndRead:
    """Flow 2B: Copy from app text field + read clipboard."""

    def test_copy_from_field_and_read(self, bridge_app: subprocess.Popen[str]) -> None:
        """Set known text in a field, select all + copy, read via clipboard.read()."""
        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket
        from qt_ai_dev_tools.subsystems import clipboard

        sock = find_bridge_socket()
        assert sock is not None, "No bridge socket found"

        known_text = "clipboard read test 42"

        # Set text into the text input
        eval_code(sock, f"widgets['text_input'].setText('{known_text}')")
        eval_code(sock, "widgets['text_input'].setFocus()")
        eval_code(sock, "widgets['text_input'].selectAll()")
        time.sleep(0.3)

        # Copy via xdotool (ctrl+c)
        _run_cli("key", "ctrl+c")
        time.sleep(0.3)

        # Read clipboard
        result = clipboard.read()
        assert known_text in result
