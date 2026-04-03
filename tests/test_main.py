"""
Тесты для проверки инфраструктуры:
1. pytest-qt — юнит-тесты виджетов без AT-SPI
2. AT-SPI smoke test — проверяем что дерево доступности работает
3. Screenshot test — проверяем что scrot видит Xvfb
"""
import os
import subprocess
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.main import MainWindow


# ── pytest-qt тесты ──────────────────────────────────────────────────────────

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
        qtbot.mouseClick(win.add_btn, __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.LeftButton)

        assert win.item_list.count() == 1
        assert win.item_list.item(0).text() == "тест"
        assert win.count_label.text() == "Элементов: 1"
        assert "тест" in win.status_label.text()

    def test_add_empty_shows_warning(self, qtbot):
        win = MainWindow()
        qtbot.addWidget(win)

        win.text_input.clear()
        qtbot.mouseClick(win.add_btn, __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.LeftButton)

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
        from PySide6.QtCore import Qt
        win = MainWindow()
        qtbot.addWidget(win)

        win.text_input.setText("enter-test")
        qtbot.keyClick(win.text_input, Qt.Key_Return)

        assert win.item_list.count() == 1


# ── AT-SPI smoke test ─────────────────────────────────────────────────────────
# Запускать только если есть DISPLAY и at-spi доступен

@pytest.mark.skipif(
    not os.environ.get("DISPLAY"),
    reason="DISPLAY не задан, AT-SPI недоступен"
)
def test_atspi_accessibility_tree(qtbot):
    """
    Проверяем что Qt экспортирует accessibility tree и AT-SPI его видит.
    Это smoke test — если он проходит, агент может использовать gi.repository.Atspi.
    """
    try:
        import gi
        gi.require_version("Atspi", "2.0")
        from gi.repository import Atspi
    except (ImportError, ValueError):
        pytest.skip("gi.repository.Atspi недоступен")

    win = MainWindow()
    win.show()
    qtbot.addWidget(win)
    qtbot.waitExposed(win)

    # даём AT-SPI время зарегистрировать приложение
    qtbot.wait(500)

    desktop = Atspi.get_desktop(0)
    app_names = []
    for i in range(desktop.get_child_count()):
        app = desktop.get_child_at_index(i)
        if app:
            app_names.append(app.get_name())

    # приложение должно быть видно в дереве
    assert len(app_names) > 0, f"AT-SPI desktop пуст. Дерево: {app_names}"
    print(f"\nAT-SPI видит приложения: {app_names}")


# ── Screenshot smoke test ─────────────────────────────────────────────────────

@pytest.mark.skipif(
    not os.environ.get("DISPLAY"),
    reason="DISPLAY не задан, scrot недоступен"
)
def test_screenshot_via_scrot(qtbot, tmp_path):
    """
    Проверяем что scrot видит Xvfb и делает скриншот.
    Критично для workflow агента: visual feedback.
    """
    win = MainWindow()
    win.show()
    qtbot.addWidget(win)
    qtbot.waitExposed(win)
    qtbot.wait(200)

    screenshot_path = str(tmp_path / "screen.png")
    result = subprocess.run(
        ["scrot", screenshot_path],
        capture_output=True, text=True
    )

    assert result.returncode == 0, f"scrot завершился с ошибкой: {result.stderr}"
    assert os.path.exists(screenshot_path), "Файл скриншота не создан"
    size = os.path.getsize(screenshot_path)
    assert size > 1000, f"Скриншот подозрительно маленький: {size} байт"
    print(f"\nСкриншот сохранён: {screenshot_path} ({size} байт)")


# ── Qt-internal screenshot (работает без DISPLAY) ────────────────────────────

def test_widget_grab(qtbot, tmp_path):
    """
    Qt-internal grab — работает даже в offscreen режиме.
    Fallback для CI без Xvfb.
    """
    win = MainWindow()
    win.show()
    qtbot.addWidget(win)

    screenshot_path = str(tmp_path / "grab.png")
    pixmap = win.grab()
    saved = pixmap.save(screenshot_path)

    assert saved, "widget.grab() не смог сохранить файл"
    assert os.path.getsize(screenshot_path) > 500
    print(f"\nWidget grab сохранён: {screenshot_path}")
