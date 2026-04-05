"""Minimal PySide6 app for testing system tray interaction."""

from __future__ import annotations

import os
import sys

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)


def _create_icon() -> QIcon:
    """Create a simple colored pixmap icon (no file needed)."""
    pixmap = QPixmap(QSize(32, 32))
    pixmap.fill(QColor("blue"))
    return QIcon(pixmap)


class TrayTestWindow(QMainWindow):
    """Test window with system tray icon and context menu."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Tray Test App")
        self.setMinimumSize(300, 200)
        self.setObjectName("TrayTestWindow")

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("status_label")
        self.status_label.setAccessibleName("status_label")
        layout.addWidget(self.status_label)

        self.notify_btn = QPushButton("Send Notification")
        self.notify_btn.setObjectName("notify_btn")
        self.notify_btn.setAccessibleName("Send Notification")
        self.notify_btn.clicked.connect(self._on_notify)
        layout.addWidget(self.notify_btn)

        # System tray icon
        self.tray_icon = QSystemTrayIcon(_create_icon(), self)
        self.tray_icon.setToolTip("Tray Test App")

        # Context menu
        tray_menu = QMenu()
        show_action = tray_menu.addAction("Show")
        show_action.setObjectName("show_action")
        settings_action = tray_menu.addAction("Settings")
        settings_action.setObjectName("settings_action")
        tray_menu.addSeparator()
        quit_action = tray_menu.addAction("Quit")
        quit_action.setObjectName("quit_action")

        show_action.triggered.connect(self._on_show)
        settings_action.triggered.connect(self._on_settings)
        quit_action.triggered.connect(QApplication.quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation (e.g. left-click via D-Bus Activate)."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._on_show()

    def _on_show(self) -> None:
        self.show()
        self.activateWindow()
        self.status_label.setText("Shown from tray")

    def _on_settings(self) -> None:
        self.status_label.setText("Settings opened")

    def _on_notify(self) -> None:
        self.tray_icon.showMessage("Test", "Notification from tray app", QSystemTrayIcon.MessageIcon.Information, 3000)
        self.status_label.setText("Notification sent")


def main() -> None:
    """Run the tray test app."""
    app = QApplication(sys.argv)
    window = TrayTestWindow()
    window.show()

    # Enable bridge for AI agent eval access (requires QT_AI_DEV_TOOLS_BRIDGE=1)
    if os.environ.get("QT_AI_DEV_TOOLS_BRIDGE") == "1":
        from qt_ai_dev_tools.bridge import start

        start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
