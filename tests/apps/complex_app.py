"""Kitchen-sink PySide6 app for testing complex widget interactions.

Exercises: QTabWidget, QComboBox, QCheckBox, QRadioButton, QSlider,
QSpinBox, QTableWidget, QListWidget, QMenuBar, QScrollArea, QDialog.
All widgets have objectName set for bridge access and AT-SPI identification.
"""

from __future__ import annotations

import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMenuBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class ComplexApp(QMainWindow):
    """Main window with tabs containing various complex widgets."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Complex Test App")
        self.setObjectName("ComplexApp")
        self.setMinimumSize(640, 480)

        self._setup_menubar()
        self._setup_statusbar()
        self._setup_tabs()

    def _setup_menubar(self) -> None:
        menubar = self.menuBar()
        assert isinstance(menubar, QMenuBar)

        file_menu = menubar.addMenu("File")
        assert file_menu is not None
        file_menu.setObjectName("file_menu")

        new_action = file_menu.addAction("New")
        assert new_action is not None
        new_action.setObjectName("action_new")
        new_action.triggered.connect(lambda: self._set_status("New clicked"))

        save_action = file_menu.addAction("Save")
        assert save_action is not None
        save_action.setObjectName("action_save")
        save_action.triggered.connect(lambda: self._set_status("Save clicked"))

        file_menu.addSeparator()

        quit_action = file_menu.addAction("Quit")
        assert quit_action is not None
        quit_action.setObjectName("action_quit")
        quit_action.triggered.connect(self.close)

        edit_menu = menubar.addMenu("Edit")
        assert edit_menu is not None
        edit_menu.setObjectName("edit_menu")

        undo_action = edit_menu.addAction("Undo")
        assert undo_action is not None
        undo_action.setObjectName("action_undo")
        undo_action.triggered.connect(lambda: self._set_status("Undo clicked"))

        help_menu = menubar.addMenu("Help")
        assert help_menu is not None
        help_menu.setObjectName("help_menu")

        about_action = help_menu.addAction("About")
        assert about_action is not None
        about_action.setObjectName("action_about")
        about_action.triggered.connect(self._show_about_dialog)

    def _setup_statusbar(self) -> None:
        status_bar = QStatusBar()
        status_bar.setObjectName("status_bar")
        self.setStatusBar(status_bar)
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("status_label")
        status_bar.addPermanentWidget(self.status_label)

    def _setup_tabs(self) -> None:
        self.tabs = QTabWidget()
        self.tabs.setObjectName("main_tabs")
        self.setCentralWidget(self.tabs)

        self.tabs.addTab(self._create_inputs_tab(), "Inputs")
        self.tabs.addTab(self._create_data_tab(), "Data")
        self.tabs.addTab(self._create_settings_tab(), "Settings")

    def _create_inputs_tab(self) -> QWidget:
        tab = QWidget()
        tab.setObjectName("inputs_tab")
        layout = QVBoxLayout(tab)

        # Combo box
        layout.addWidget(QLabel("Select fruit:"))
        self.combo = QComboBox()
        self.combo.setObjectName("fruit_combo")
        self.combo.addItems(["Apple", "Banana", "Cherry", "Date", "Elderberry"])
        self.combo.currentTextChanged.connect(lambda t: self._set_status(f"Fruit: {t}"))
        layout.addWidget(self.combo)

        # Checkbox
        self.checkbox = QCheckBox("Enable notifications")
        self.checkbox.setObjectName("notify_checkbox")
        self.checkbox.toggled.connect(lambda c: self._set_status(f"Notifications: {'on' if c else 'off'}"))
        layout.addWidget(self.checkbox)

        # Radio buttons
        radio_layout = QHBoxLayout()
        self.radio_group = QButtonGroup(tab)
        self.radio_group.setObjectName("size_group")
        for i, label in enumerate(["Small", "Medium", "Large"]):
            radio = QRadioButton(label)
            radio.setObjectName(f"radio_{label.lower()}")
            self.radio_group.addButton(radio, i)
            radio_layout.addWidget(radio)
        medium_btn = self.radio_group.button(1)
        assert medium_btn is not None
        medium_btn.setChecked(True)
        self.radio_group.idToggled.connect(self._on_radio_toggled)
        layout.addLayout(radio_layout)

        # Slider
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("Volume:"))
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setObjectName("volume_slider")
        self.slider.setRange(0, 100)
        self.slider.setValue(50)
        self.slider_value_label = QLabel("50")
        self.slider_value_label.setObjectName("slider_value")
        self.slider.valueChanged.connect(self._on_slider_changed)
        slider_layout.addWidget(self.slider)
        slider_layout.addWidget(self.slider_value_label)
        layout.addLayout(slider_layout)

        # Spin box
        spin_layout = QHBoxLayout()
        spin_layout.addWidget(QLabel("Quantity:"))
        self.spinbox = QSpinBox()
        self.spinbox.setObjectName("quantity_spin")
        self.spinbox.setRange(1, 99)
        self.spinbox.setValue(5)
        self.spinbox.valueChanged.connect(lambda v: self._set_status(f"Quantity: {v}"))
        spin_layout.addWidget(self.spinbox)
        layout.addLayout(spin_layout)

        # Text input
        self.text_input = QLineEdit()
        self.text_input.setObjectName("text_input")
        self.text_input.setPlaceholderText("Type something...")
        layout.addWidget(self.text_input)

        layout.addStretch()
        return tab

    def _create_data_tab(self) -> QWidget:
        tab = QWidget()
        tab.setObjectName("data_tab")
        layout = QVBoxLayout(tab)

        # Table
        self.table = QTableWidget(5, 3)
        self.table.setObjectName("data_table")
        self.table.setHorizontalHeaderLabels(["Name", "Value", "Status"])
        sample_data = [
            ("Alpha", "100", "Active"),
            ("Beta", "200", "Inactive"),
            ("Gamma", "300", "Active"),
            ("Delta", "400", "Pending"),
            ("Epsilon", "500", "Active"),
        ]
        for row, (n, v, s) in enumerate(sample_data):
            self.table.setItem(row, 0, QTableWidgetItem(n))
            self.table.setItem(row, 1, QTableWidgetItem(v))
            self.table.setItem(row, 2, QTableWidgetItem(s))
        self.table.cellClicked.connect(self._on_cell_clicked)
        layout.addWidget(self.table)

        # List with selection
        self.data_list = QListWidget()
        self.data_list.setObjectName("data_list")
        self.data_list.addItems(["Item A", "Item B", "Item C", "Item D", "Item E"])
        self.data_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.data_list.itemSelectionChanged.connect(
            lambda: self._set_status(f"Selected: {[item.text() for item in self.data_list.selectedItems()]}")
        )
        layout.addWidget(self.data_list)

        return tab

    def _create_settings_tab(self) -> QWidget:
        tab = QWidget()
        tab.setObjectName("settings_tab")
        layout = QVBoxLayout(tab)

        # Scroll area with many widgets
        scroll = QScrollArea()
        scroll.setObjectName("settings_scroll")
        scroll.setWidgetResizable(True)

        scroll_content = QWidget()
        scroll_content.setObjectName("scroll_content")
        scroll_layout = QVBoxLayout(scroll_content)

        for i in range(15):
            row = QHBoxLayout()
            label = QLabel(f"Setting {i + 1}:")
            label.setObjectName(f"setting_label_{i}")
            checkbox = QCheckBox(f"Option {i + 1}")
            checkbox.setObjectName(f"setting_option_{i}")
            row.addWidget(label)
            row.addWidget(checkbox)
            scroll_layout.addLayout(row)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Dialog trigger button
        dialog_btn = QPushButton("Show Dialog")
        dialog_btn.setObjectName("dialog_btn")
        dialog_btn.clicked.connect(self._show_test_dialog)
        layout.addWidget(dialog_btn)

        return tab

    def _on_radio_toggled(self, button_id: int, checked: bool) -> None:
        """Handle radio button toggle."""
        if not checked:
            return
        btn = self.radio_group.button(button_id)
        if btn is not None:
            self._set_status(f"Size: {btn.text()}")

    def _on_slider_changed(self, value: int) -> None:
        """Handle slider value change."""
        self.slider_value_label.setText(str(value))
        self._set_status(f"Volume: {value}")

    def _on_cell_clicked(self, row: int, col: int) -> None:
        """Handle table cell click."""
        item = self.table.item(row, col)
        text = item.text() if item else ""
        self._set_status(f"Cell ({row},{col}): {text}")

    def _show_about_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("About")
        dialog.setObjectName("about_dialog")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Complex Test App v1.0"))
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        btn_box.accepted.connect(dialog.accept)
        layout.addWidget(btn_box)
        dialog.exec()
        self._set_status("About dialog closed")

    def _show_test_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Test Dialog")
        dialog.setObjectName("test_dialog")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("This is a test dialog."))
        input_field = QLineEdit()
        input_field.setObjectName("dialog_input")
        input_field.setPlaceholderText("Enter value...")
        layout.addWidget(input_field)
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            self._set_status(f"Dialog accepted: {input_field.text()}")
        else:
            self._set_status("Dialog cancelled")

    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)


def main() -> None:
    """Run the complex test app."""
    app = QApplication(sys.argv)
    window = ComplexApp()
    window.show()

    # Enable bridge for AI agent eval access (requires QT_AI_DEV_TOOLS_BRIDGE=1)
    if os.environ.get("QT_AI_DEV_TOOLS_BRIDGE") == "1":
        from qt_ai_dev_tools.bridge import start

        start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
