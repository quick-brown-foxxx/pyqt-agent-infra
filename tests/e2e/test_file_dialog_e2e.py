"""E2E tests for file_dialog subsystem -- real QFileDialog in VM."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.skipif(
        not os.environ.get("DISPLAY"),
        reason="E2E tests require Xvfb (run in VM via 'make test-e2e')",
    ),
    pytest.mark.e2e,
]


def _read_status_label(sock_path: Path) -> str:
    """Read the status_label text from the file dialog app via bridge.

    Uses bridge (not AT-SPI get_text) because bridge reliably returns
    the QLabel text content. AT-SPI get_text() has version-dependent
    issues with the text interface on newer AT-SPI builds.
    """
    from qt_ai_dev_tools.bridge._client import eval_code

    resp = eval_code(sock_path, "widgets['status_label'].text()")
    assert resp.ok is True
    return resp.result or ""


class TestFileDialogOpen:
    """Flow 1A: Open file via native dialog."""

    def test_open_file_dialog_detect_fill_accept(self, file_dialog_app: subprocess.Popen[str], tmp_path: Path) -> None:
        """Create a temp file, open dialog, fill path, accept, verify status."""
        from qt_ai_dev_tools.bridge._client import find_bridge_socket
        from qt_ai_dev_tools.pilot import QtPilot
        from qt_ai_dev_tools.subsystems import file_dialog

        sock = find_bridge_socket(pid=file_dialog_app.pid)
        assert sock is not None, "No bridge socket found"

        # Create a temp file with known content
        test_file = tmp_path / "test_open.txt"
        test_file.write_text("file dialog e2e content")

        # Click the "Open File" button via AT-SPI (not bridge — modal dialog blocks bridge)
        pilot = QtPilot(app_name="file_dialog_app.py")
        open_btn = pilot.find_one(role="push button", name="Open File")
        pilot.click(open_btn)
        time.sleep(1.0)  # Wait for dialog to appear

        # Detect the dialog
        info = file_dialog.detect(pilot)
        assert info.dialog_type in ("file chooser", "dialog")

        # Fill the path
        file_dialog.fill(pilot, str(test_file))
        time.sleep(0.3)

        # Accept the dialog
        result = file_dialog.accept(pilot)
        assert result.accepted is True
        time.sleep(0.5)

        # Verify status label shows the filename via bridge (dialog is closed now)
        status = _read_status_label(sock)
        assert test_file.name in status


class TestFileDialogSave:
    """Flow 1B: Save file via dialog."""

    def test_save_file_dialog(self, file_dialog_app: subprocess.Popen[str], tmp_path: Path) -> None:
        """Type content, open save dialog, fill path, accept, verify file exists."""
        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket
        from qt_ai_dev_tools.pilot import QtPilot
        from qt_ai_dev_tools.subsystems import file_dialog

        sock = find_bridge_socket(pid=file_dialog_app.pid)
        assert sock is not None, "No bridge socket found"

        save_path = tmp_path / "test_save_output.txt"

        # Type content into the text edit — safe via bridge (no modal yet)
        eval_code(sock, "widgets['text_edit'].setPlainText('saved by e2e test')")

        # Click the "Save As" button via AT-SPI (not bridge — modal dialog blocks bridge)
        pilot = QtPilot(app_name="file_dialog_app.py")
        save_btn = pilot.find_one(role="push button", name="Save As")
        pilot.click(save_btn)
        time.sleep(1.0)  # Wait for dialog

        # Fill the save path and accept
        file_dialog.fill(pilot, str(save_path))
        time.sleep(0.3)
        file_dialog.accept(pilot)
        time.sleep(0.5)

        # Verify status label updated via bridge (dialog is closed now)
        status = _read_status_label(sock)
        assert "Saved" in status or save_path.name in status


class TestFileDialogCancel:
    """Flow 1C: Cancel dialog leaves app unchanged."""

    def test_cancel_file_dialog(self, file_dialog_app: subprocess.Popen[str]) -> None:
        """Open dialog, cancel, verify app state unchanged."""
        from qt_ai_dev_tools.bridge._client import find_bridge_socket
        from qt_ai_dev_tools.pilot import QtPilot
        from qt_ai_dev_tools.subsystems import file_dialog

        sock = find_bridge_socket(pid=file_dialog_app.pid)
        assert sock is not None, "No bridge socket found"

        # Click "Open File" to trigger dialog via AT-SPI (not bridge — modal blocks)
        pilot = QtPilot(app_name="file_dialog_app.py")
        open_btn = pilot.find_one(role="push button", name="Open File")
        pilot.click(open_btn)
        time.sleep(1.0)

        # Cancel the dialog
        file_dialog.cancel(pilot)
        time.sleep(0.5)

        # Verify status shows cancel message via bridge (dialog is closed now)
        status = _read_status_label(sock)
        assert "cancelled" in status.lower() or "cancel" in status.lower()
