"""Minimal PySide6 app for testing audio interaction."""

from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class AudioTestWindow(QMainWindow):
    """Test window with Record and Play buttons."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Audio Test App")
        self.setMinimumSize(300, 200)
        self.setObjectName("AudioTestWindow")

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("status_label")
        self.status_label.setAccessibleName("status_label")
        layout.addWidget(self.status_label)

        self.record_btn = QPushButton("Record")
        self.record_btn.setObjectName("record_btn")
        self.record_btn.setAccessibleName("Record")
        self.record_btn.clicked.connect(self._on_record)
        layout.addWidget(self.record_btn)

        self.play_btn = QPushButton("Play")
        self.play_btn.setObjectName("play_btn")
        self.play_btn.setAccessibleName("Play")
        self.play_btn.clicked.connect(self._on_play)
        layout.addWidget(self.play_btn)

    def _on_record(self) -> None:
        self.status_label.setText("Recording...")

    def _on_play(self) -> None:
        self.status_label.setText("Playing...")


def main() -> None:
    """Run the audio test app."""
    app = QApplication(sys.argv)
    window = AudioTestWindow()
    window.show()

    # Enable bridge for AI agent eval access (requires QT_AI_DEV_TOOLS_BRIDGE=1)
    if os.environ.get("QT_AI_DEV_TOOLS_BRIDGE") == "1":
        from qt_ai_dev_tools.bridge import start

        start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
