"""Tests for Qt/AT-SPI infrastructure:
1. pytest-qt — widget unit tests without AT-SPI
2. AT-SPI smoke test — accessibility tree works
3. Screenshot test — scrot sees Xvfb
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import Qt

pytestmark = pytest.mark.unit

# app/ is not a package — add project root to path for test discovery
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.main import MainWindow  # noqa: E402, I001


# -- pytest-qt tests ----------------------------------------------------------


class TestMainWindowLogic:
    def test_initial_state(self, qtbot):
        win = MainWindow()
        qtbot.addWidget(win)

        assert win.status_label.text() == "Готов"
        assert win.item_list.count() == 0
        assert win.count_label.text() == "Элементов: 0"

    def test_add_item(self, qtbot):
        win = MainWindow()
        qtbot.addWidget(win)

        win.text_input.setText("тест")
        qtbot.mouseClick(win.add_btn, Qt.MouseButton.LeftButton)

        assert win.item_list.count() == 1
        assert win.item_list.item(0).text() == "тест"
        assert win.count_label.text() == "Элементов: 1"
        assert "тест" in win.status_label.text()

    def test_add_empty_shows_warning(self, qtbot):
        win = MainWindow()
        qtbot.addWidget(win)

        win.text_input.clear()
        qtbot.mouseClick(win.add_btn, Qt.MouseButton.LeftButton)

        assert win.item_list.count() == 0
        assert "⚠" in win.status_label.text()

    def test_clear(self, qtbot):
        win = MainWindow()
        qtbot.addWidget(win)

        for text in ["a", "b", "c"]:
            win.text_input.setText(text)
            win.add_btn.click()

        assert win.item_list.count() == 3
        win.clear_btn.click()
        assert win.item_list.count() == 0
        assert win.status_label.text() == "Список очищен"

    def test_enter_key_adds_item(self, qtbot):
        win = MainWindow()
        qtbot.addWidget(win)

        win.text_input.setText("enter-test")
        qtbot.keyClick(win.text_input, Qt.Key.Key_Return)

        assert win.item_list.count() == 1


# -- AT-SPI smoke test --------------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("DISPLAY"),
    reason="DISPLAY not set, AT-SPI unavailable",
)
def test_atspi_accessibility_tree(qtbot):
    try:
        import gi

        gi.require_version("Atspi", "2.0")
        from gi.repository import Atspi
    except (ImportError, ValueError):
        pytest.skip("gi.repository.Atspi unavailable")

    win = MainWindow()
    win.show()
    qtbot.addWidget(win)
    qtbot.waitExposed(win)
    qtbot.wait(500)

    desktop = Atspi.get_desktop(0)
    app_names = []
    for i in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(i)
        if app:
            app_names.append(app.get_name())

    assert len(app_names) > 0, f"AT-SPI desktop empty. Tree: {app_names}"
    print(f"\nAT-SPI sees apps: {app_names}")


# -- Screenshot smoke test ----------------------------------------------------


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("DISPLAY"),
    reason="DISPLAY not set, scrot unavailable",
)
def test_screenshot_via_scrot(qtbot, tmp_path):
    win = MainWindow()
    win.show()
    qtbot.addWidget(win)
    qtbot.waitExposed(win)
    qtbot.wait(200)

    screenshot_path = str(tmp_path / "screen.png")
    result = subprocess.run(
        ["scrot", screenshot_path],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"scrot failed: {result.stderr}"
    assert os.path.exists(screenshot_path), "Screenshot file not created"
    size = os.path.getsize(screenshot_path)
    assert size > 1000, f"Screenshot suspiciously small: {size} bytes"
    print(f"\nScreenshot saved: {screenshot_path} ({size} bytes)")


# -- Qt-internal screenshot (works without DISPLAY) ----------------------------


def test_widget_grab(qtbot, tmp_path):
    win = MainWindow()
    win.show()
    qtbot.addWidget(win)

    screenshot_path = str(tmp_path / "grab.png")
    pixmap = win.grab()
    saved = pixmap.save(screenshot_path)

    assert saved, "widget.grab() could not save file"
    assert os.path.getsize(screenshot_path) > 500
    print(f"\nWidget grab saved: {screenshot_path}")
