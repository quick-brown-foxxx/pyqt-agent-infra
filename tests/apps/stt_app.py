"""Minimal PySide6 app for testing STT (speech-to-text) workflow.

This is a fake STT app: it returns hardcoded text for any "audio input",
simulating a real STT pipeline without requiring a model.
"""

from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# Hardcoded STT result — simulates transcription output
_FAKE_TRANSCRIPTION = "the quick brown fox jumps over the lazy dog"


class SttTestWindow(QMainWindow):
    """Test window with Record and Transcribe buttons."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("STT Test App")
        self.setMinimumSize(400, 300)
        self.setObjectName("SttTestWindow")

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("status_label")
        self.status_label.setAccessibleName("status_label")
        layout.addWidget(self.status_label)

        self.record_btn = QPushButton("Record Audio")
        self.record_btn.setObjectName("record_btn")
        self.record_btn.setAccessibleName("Record Audio")
        self.record_btn.clicked.connect(self._on_record)
        layout.addWidget(self.record_btn)

        self.transcribe_btn = QPushButton("Transcribe")
        self.transcribe_btn.setObjectName("transcribe_btn")
        self.transcribe_btn.setAccessibleName("Transcribe")
        self.transcribe_btn.clicked.connect(self._on_transcribe)
        layout.addWidget(self.transcribe_btn)

        self.result_text = QTextEdit()
        self.result_text.setObjectName("result_text")
        self.result_text.setAccessibleName("result_text")
        self.result_text.setReadOnly(True)
        layout.addWidget(self.result_text)

        self._has_recording = False

    def _on_record(self) -> None:
        self._has_recording = True
        self.status_label.setText("Recording captured")

    def _on_transcribe(self) -> None:
        if not self._has_recording:
            self.status_label.setText("No recording — record first")
            return
        self.result_text.setPlainText(_FAKE_TRANSCRIPTION)
        self.status_label.setText("Transcription complete")


def main() -> None:
    """Run the STT test app."""
    app = QApplication(sys.argv)
    window = SttTestWindow()
    window.show()

    # Enable bridge for AI agent eval access (requires QT_AI_DEV_TOOLS_BRIDGE=1)
    if os.environ.get("QT_AI_DEV_TOOLS_BRIDGE") == "1":
        from qt_ai_dev_tools.bridge import start

        start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
