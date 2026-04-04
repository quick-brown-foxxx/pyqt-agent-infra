"""Minimal PySide6 app for testing file dialog automation."""

from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class FileDialogTestWindow(QMainWindow):
    """Test window with Open File and Save As buttons."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("File Dialog Test App")
        self.setMinimumSize(400, 300)
        self.setObjectName("FileDialogTestWindow")

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("status_label")
        self.status_label.setAccessibleName("status_label")
        layout.addWidget(self.status_label)

        self.open_btn = QPushButton("Open File")
        self.open_btn.setObjectName("open_btn")
        self.open_btn.setAccessibleName("Open File")
        self.open_btn.clicked.connect(self._on_open)
        layout.addWidget(self.open_btn)

        self.save_btn = QPushButton("Save As")
        self.save_btn.setObjectName("save_btn")
        self.save_btn.setAccessibleName("Save As")
        self.save_btn.clicked.connect(self._on_save)
        layout.addWidget(self.save_btn)

        self.text_edit = QTextEdit()
        self.text_edit.setObjectName("text_edit")
        self.text_edit.setAccessibleName("text_edit")
        layout.addWidget(self.text_edit)

    def _on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open File")
        if path:
            self.status_label.setText(f"Opened: {path}")
        else:
            self.status_label.setText("Open cancelled")

    def _on_save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save File As")
        if path:
            self.status_label.setText(f"Saved: {path}")
        else:
            self.status_label.setText("Save cancelled")


def main() -> None:
    """Run the file dialog test app."""
    app = QApplication(sys.argv)
    window = FileDialogTestWindow()
    window.show()

    # Enable bridge for AI agent eval access (requires QT_AI_DEV_TOOLS_BRIDGE=1)
    if os.environ.get("QT_AI_DEV_TOOLS_BRIDGE") == "1":
        from qt_ai_dev_tools.bridge import start

        start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
