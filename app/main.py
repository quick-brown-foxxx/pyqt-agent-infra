"""
Минимальное PySide6 приложение для проверки тестовой инфраструктуры.
Намеренно содержит несколько виджетов с разным state для полезных тестов.
"""

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Qt Dev Proto")
        self.setMinimumSize(480, 320)
        self.setObjectName("MainWindow")

        # --- центральный виджет ---
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # статус — меняется при действиях
        self.status_label = QLabel("Готов")
        self.status_label.setObjectName("status_label")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # ввод + добавление в список
        input_row = QHBoxLayout()
        self.text_input = QLineEdit()
        self.text_input.setObjectName("text_input")
        self.text_input.setPlaceholderText("Введите элемент...")
        self.add_btn = QPushButton("Добавить")
        self.add_btn.setObjectName("add_btn")
        self.add_btn.clicked.connect(self._on_add)
        self.text_input.returnPressed.connect(self._on_add)
        input_row.addWidget(self.text_input)
        input_row.addWidget(self.add_btn)
        layout.addLayout(input_row)

        # список элементов
        self.item_list = QListWidget()
        self.item_list.setObjectName("item_list")
        layout.addWidget(self.item_list)

        # кнопки управления
        btn_row = QHBoxLayout()
        self.clear_btn = QPushButton("Очистить")
        self.clear_btn.setObjectName("clear_btn")
        self.clear_btn.clicked.connect(self._on_clear)
        self.count_label = QLabel("Элементов: 0")
        self.count_label.setObjectName("count_label")
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.count_label)
        layout.addLayout(btn_row)

        # счётчик кликов — проверяем что state обновляется
        self._click_count = 0

    def _on_add(self):
        text = self.text_input.text().strip()
        if not text:
            self.status_label.setText("⚠ Введите текст")
            return
        self.item_list.addItem(text)
        self.text_input.clear()
        self._click_count += 1
        count = self.item_list.count()
        self.count_label.setText(f"Элементов: {count}")
        self.status_label.setText(f"Добавлено: «{text}»")

    def _on_clear(self):
        self.item_list.clear()
        self.count_label.setText("Элементов: 0")
        self.status_label.setText("Список очищен")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    # Enable bridge for AI agent eval access (requires QT_AI_DEV_TOOLS_BRIDGE=1)
    from qt_ai_dev_tools.bridge import start

    start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
