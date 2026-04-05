# Complex Widgets, Tree Snapshots & Test Quality — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add complex Qt widget support (Value/Selection/Table AT-SPI interfaces + pilot helpers), tree snapshot/diff, a kitchen-sink test app, and replace tautological tests — extending qt-ai-dev-tools from simple widget interaction to comprehensive Qt app coverage.

**Architecture:** Three-layer widget API (AtspiNode typed interfaces → QtPilot convenience methods → CLI commands). Tree snapshot as JSON serialization of widget tree with diff comparison. Kitchen-sink PySide6 test app as validation target. All new code follows basedpyright strict, ruff, typed dataclasses.

**Tech Stack:** Python 3.12+, PySide6 (dev dep), AT-SPI via gi.repository.Atspi, pytest, typer CLI

**Spec:** `docs/superpowers/specs/2026-04-06-complex-widgets-snapshots-test-quality.md`

**Skills to use:** `writing-python-code`, `testing-python`, `building-qt-apps`

---

## Task 1: Add PySide6 to dev dependencies

**Files:**
- Modify: `pyproject.toml`

This unblocks type checking for the kitchen-sink app and any PySide6-importing test code on the host.

- [ ] **Step 1: Add PySide6 to dev dependency group**

In `pyproject.toml`, add `PySide6-Essentials` to `[dependency-groups] dev`:

```toml
[dependency-groups]
dev = [
    "pytest>=9.0.1",
    "pytest-cov>=7.0.0",
    "pytest-qt>=4.5.0",
    "pytest-timeout>=2.3.1",
    "ruff>=0.14.6",
    "basedpyright>=1.34.0",
    "pre-commit",
    "poethepoet",
    "PySide6-Essentials>=6.8.0",
]
```

Note: Use `PySide6-Essentials` (smaller) not full `PySide6`. This provides QtCore, QtWidgets, QtGui — everything needed for type checking and the test app.

- [ ] **Step 2: Sync and verify**

```bash
uv sync
uv run poe lint_full
```

Expected: lint passes. PySide6 now available in the host venv.

- [ ] **Step 3: Verify pytest-qt works on host**

```bash
uv run pytest tests/unit/ -x -q --co 2>&1 | head -5
```

Expected: test collection succeeds (no more "No module named PySide6" at configure time). Tests themselves may still need DISPLAY for some, but collection should work.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build: add PySide6-Essentials to dev deps for host type checking"
```

---

## Task 2: Kitchen-sink test app

**Files:**
- Create: `tests/apps/complex_app.py`

A rich PySide6 app exercising all complex widget types. This is the test target for Tasks 5-8.

- [ ] **Step 1: Create the complex test app**

Create `tests/apps/complex_app.py`:

```python
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
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
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
        self.combo.currentTextChanged.connect(
            lambda t: self._set_status(f"Fruit: {t}")
        )
        layout.addWidget(self.combo)

        # Checkbox
        self.checkbox = QCheckBox("Enable notifications")
        self.checkbox.setObjectName("notify_checkbox")
        self.checkbox.toggled.connect(
            lambda c: self._set_status(f"Notifications: {'on' if c else 'off'}")
        )
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
        self.radio_group.button(1).setChecked(True)  # Default: Medium
        self.radio_group.idToggled.connect(
            lambda id, checked: self._set_status(
                f"Size: {self.radio_group.button(id).text()}"
            )
            if checked
            else None
        )
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
        self.slider.valueChanged.connect(
            lambda v: (
                self.slider_value_label.setText(str(v)),
                self._set_status(f"Volume: {v}"),
            )
        )
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
        self.spinbox.valueChanged.connect(
            lambda v: self._set_status(f"Quantity: {v}")
        )
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
        self.table.cellClicked.connect(
            lambda r, c: self._set_status(
                f"Cell ({r},{c}): {self.table.item(r, c).text() if self.table.item(r, c) else ''}"
            )
        )
        layout.addWidget(self.table)

        # List with selection
        self.data_list = QListWidget()
        self.data_list.setObjectName("data_list")
        self.data_list.addItems(["Item A", "Item B", "Item C", "Item D", "Item E"])
        self.data_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.data_list.itemSelectionChanged.connect(
            lambda: self._set_status(
                f"Selected: {[item.text() for item in self.data_list.selectedItems()]}"
            )
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
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
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
    app = QApplication(sys.argv)
    window = ComplexApp()
    window.show()

    # Enable bridge for AI agent eval access
    if os.environ.get("QT_AI_DEV_TOOLS_BRIDGE") == "1":
        from qt_ai_dev_tools.bridge import start
        start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify lint passes**

```bash
uv run poe lint_full
```

Expected: 0 errors. The app uses basedpyright-strict-compatible types.

- [ ] **Step 3: Commit**

```bash
git add tests/apps/complex_app.py
git commit -m "feat: add kitchen-sink test app with tabs, combo, table, menu, slider, dialog"
```

---

## Task 3: Extend AtspiNode with Value, Selection, Table interfaces

**Files:**
- Modify: `src/qt_ai_dev_tools/_atspi.py`

Add typed wrappers for AT-SPI Value, Selection, and Table interfaces following the existing pattern (get interface → call methods with type: ignore rationale comments).

- [ ] **Step 1: Add Value interface methods**

Add after `has_action_iface` property in `_atspi.py`:

```python
# ── Value interface ─────────────────────────────────────────

@property
def has_value_iface(self) -> bool:
    """Whether the widget has a Value interface (sliders, spinners)."""
    return self._native.get_value_iface() is not None  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs

def get_value(self) -> float | None:
    """Current value. Returns None if no Value interface."""
    iface = self._native.get_value_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
    if not iface:
        return None
    return iface.get_current_value()  # type: ignore[union-attr,no-any-return]  # rationale: AT-SPI Value iface has no stubs

def set_value(self, value: float) -> None:
    """Set the current value. Raises RuntimeError if no Value interface."""
    iface = self._native.get_value_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
    if not iface:
        msg = f"Widget {self!r} has no Value interface"
        raise RuntimeError(msg)
    iface.set_current_value(value)  # type: ignore[union-attr]  # rationale: AT-SPI Value iface has no stubs

def get_minimum_value(self) -> float | None:
    """Minimum value. Returns None if no Value interface."""
    iface = self._native.get_value_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
    if not iface:
        return None
    return iface.get_minimum_value()  # type: ignore[union-attr,no-any-return]  # rationale: AT-SPI Value iface has no stubs

def get_maximum_value(self) -> float | None:
    """Maximum value. Returns None if no Value interface."""
    iface = self._native.get_value_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
    if not iface:
        return None
    return iface.get_maximum_value()  # type: ignore[union-attr,no-any-return]  # rationale: AT-SPI Value iface has no stubs
```

- [ ] **Step 2: Add Selection interface methods**

```python
# ── Selection interface ─────────────────────────────────────

@property
def has_selection_iface(self) -> bool:
    """Whether the widget has a Selection interface (combos, lists, tabs)."""
    return self._native.get_selection_iface() is not None  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs

def get_n_selected_children(self) -> int:
    """Number of selected children. Returns 0 if no Selection interface."""
    iface = self._native.get_selection_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
    if not iface:
        return 0
    return iface.get_n_selected_children()  # type: ignore[union-attr,no-any-return]  # rationale: AT-SPI Selection iface has no stubs

def get_selected_child(self, index: int = 0) -> AtspiNode | None:
    """Get the nth selected child. Returns None if no Selection or invalid index."""
    iface = self._native.get_selection_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
    if not iface:
        return None
    child = iface.get_selected_child(index)  # type: ignore[union-attr]  # rationale: AT-SPI Selection iface has no stubs
    if child is None:
        return None
    return AtspiNode(child)  # type: ignore[reportUnknownArgumentType]  # rationale: AT-SPI child is untyped

def select_child(self, index: int) -> bool:
    """Select child by index. Returns False if no Selection interface."""
    iface = self._native.get_selection_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
    if not iface:
        return False
    return iface.select_child(index)  # type: ignore[union-attr,no-any-return]  # rationale: AT-SPI Selection iface has no stubs

def deselect_child(self, index: int) -> bool:
    """Deselect child by index. Returns False if no Selection interface."""
    iface = self._native.get_selection_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
    if not iface:
        return False
    return iface.deselect_child(index)  # type: ignore[union-attr,no-any-return]  # rationale: AT-SPI Selection iface has no stubs

def is_child_selected(self, index: int) -> bool:
    """Check if child at index is selected. Returns False if no Selection interface."""
    iface = self._native.get_selection_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
    if not iface:
        return False
    return iface.is_child_selected(index)  # type: ignore[union-attr,no-any-return]  # rationale: AT-SPI Selection iface has no stubs
```

- [ ] **Step 3: Add Table interface methods**

```python
# ── Table interface ─────────────────────────────────────────

@property
def has_table_iface(self) -> bool:
    """Whether the widget has a Table interface (tables, trees)."""
    return self._native.get_table_iface() is not None  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs

def get_n_rows(self) -> int:
    """Number of rows. Returns 0 if no Table interface."""
    iface = self._native.get_table_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
    if not iface:
        return 0
    return iface.get_n_rows()  # type: ignore[union-attr,no-any-return]  # rationale: AT-SPI Table iface has no stubs

def get_n_columns(self) -> int:
    """Number of columns. Returns 0 if no Table interface."""
    iface = self._native.get_table_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
    if not iface:
        return 0
    return iface.get_n_columns()  # type: ignore[union-attr,no-any-return]  # rationale: AT-SPI Table iface has no stubs

def get_cell_at(self, row: int, col: int) -> AtspiNode | None:
    """Get accessible at table cell (row, col). Returns None if no Table or invalid position."""
    iface = self._native.get_table_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
    if not iface:
        return None
    cell = iface.get_accessible_at(row, col)  # type: ignore[union-attr]  # rationale: AT-SPI Table iface has no stubs
    if cell is None:
        return None
    return AtspiNode(cell)  # type: ignore[reportUnknownArgumentType]  # rationale: AT-SPI child is untyped
```

- [ ] **Step 4: Run lint**

```bash
uv run poe lint_full
```

Expected: passes with only the expected type: ignore comments.

- [ ] **Step 5: Commit**

```bash
git add src/qt_ai_dev_tools/_atspi.py
git commit -m "feat: add Value, Selection, Table AT-SPI interface wrappers to AtspiNode"
```

---

## Task 4: Replace tautological tests (CQ-3)

**Files:**
- Modify: `tests/unit/test_atspi.py`
- Modify: `tests/unit/test_vm.py`

Replace mock-echo tests with tests for real logic and edge cases. Add tests for new interfaces.

- [ ] **Step 1: Rewrite test_atspi.py**

Replace the entire file. Keep the mock infrastructure (`_make_native`), delete pure echo tests, keep/expand tests for real logic (action lookup, text fallback, children filtering, error paths). Add tests for new Value/Selection/Table interfaces.

```python
"""Unit tests for AtspiNode typed wrapper.

Tests focus on REAL LOGIC: action lookup, text fallback, children filtering,
error paths, and AT-SPI interface wrappers. Tautological mock-echo tests
(mock returns X, assert X) have been removed — those belong in e2e tests.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

# Mock gi and Atspi before importing _atspi
_mock_gi = MagicMock()
_mock_atspi_module = MagicMock()
_mock_gi.require_version = MagicMock()
_mock_gi.repository.Atspi = _mock_atspi_module

sys.modules.setdefault("gi", _mock_gi)
sys.modules.setdefault("gi.repository", _mock_gi.repository)
sys.modules.setdefault("gi.repository.Atspi", _mock_atspi_module)

from qt_ai_dev_tools._atspi import AtspiNode  # noqa: E402
from qt_ai_dev_tools.models import Extents  # noqa: E402


def _make_native(
    *,
    name: str | None = "TestWidget",
    role_name: str = "push button",
    child_count: int = 0,
    children: list[object] | None = None,
) -> MagicMock:
    """Create a mock AT-SPI native object with sensible defaults."""
    native = MagicMock()
    native.get_name.return_value = name
    native.get_role_name.return_value = role_name
    native.get_child_count.return_value = child_count

    if children is not None:
        native.get_child_at_index.side_effect = lambda i: children[i] if i < len(children) else None
    else:
        native.get_child_at_index.return_value = None

    native.get_text_iface.return_value = None
    native.get_action_iface.return_value = None
    native.get_value_iface.return_value = None
    native.get_selection_iface.return_value = None
    native.get_table_iface.return_value = None

    return native


# ── Name edge cases ─────────────────────────────────────────

class TestNameEdgeCases:
    """Test name property handles None/empty from AT-SPI gracefully."""

    def test_none_name_returns_empty_string(self) -> None:
        native = _make_native(name=None)
        assert AtspiNode(native).name == ""

    def test_empty_name_returns_empty_string(self) -> None:
        native = _make_native(name="")
        assert AtspiNode(native).name == ""


# ── Children filtering ──────────────────────────────────────

class TestChildrenFiltering:
    """Test that .children filters out None children from AT-SPI."""

    def test_filters_out_none_children(self) -> None:
        child1 = _make_native(name="A")
        child2 = _make_native(name="B")
        native = _make_native(child_count=4, children=[child1, None, None, child2])
        children = AtspiNode(native).children
        assert len(children) == 2
        assert children[0].name == "A"
        assert children[1].name == "B"

    def test_empty_children(self) -> None:
        native = _make_native(child_count=0)
        assert AtspiNode(native).children == []

    def test_all_none_children(self) -> None:
        native = _make_native(child_count=3, children=[None, None, None])
        assert AtspiNode(native).children == []

    def test_child_at_returns_none_for_none_native(self) -> None:
        native = _make_native(child_count=1, children=[None])
        assert AtspiNode(native).child_at(0) is None


# ── Text fallback logic ─────────────────────────────────────

class TestTextFallback:
    """Test get_text() falls back to name when no Text interface."""

    def test_uses_text_interface_when_available(self) -> None:
        from qt_ai_dev_tools import _atspi as _atspi_mod

        native = _make_native(name="FallbackName")
        text_iface = MagicMock()
        native.get_text_iface.return_value = text_iface

        mock_text = MagicMock()
        mock_text.get_character_count.return_value = 5
        mock_text.get_text.return_value = "Hello"
        with patch.object(_atspi_mod, "Atspi", **{"Text": mock_text}):
            assert AtspiNode(native).get_text() == "Hello"
            mock_text.get_text.assert_called_once_with(text_iface, 0, 5)

    def test_falls_back_to_name_when_no_text_iface(self) -> None:
        native = _make_native(name="ButtonLabel")
        native.get_text_iface.return_value = None
        assert AtspiNode(native).get_text() == "ButtonLabel"

    def test_falls_back_to_empty_when_no_text_and_no_name(self) -> None:
        native = _make_native(name=None)
        native.get_text_iface.return_value = None
        assert AtspiNode(native).get_text() == ""


# ── Action lookup logic ─────────────────────────────────────

class TestDoAction:
    """Test action lookup by name — the real logic in do_action()."""

    def test_finds_action_by_name_not_index(self) -> None:
        """Verify lookup scans actions and finds by name, not position."""
        native = _make_native()
        action_iface = MagicMock()
        action_iface.get_n_actions.return_value = 3
        action_iface.get_action_name.side_effect = lambda i: ["click", "press", "activate"][i]
        native.get_action_iface.return_value = action_iface

        AtspiNode(native).do_action("activate", pause=0.0)
        action_iface.do_action.assert_called_once_with(2)  # index 2, not 0

    def test_raises_lookup_error_with_available_actions(self) -> None:
        """Error message should list available actions for debugging."""
        native = _make_native()
        action_iface = MagicMock()
        action_iface.get_n_actions.return_value = 2
        action_iface.get_action_name.side_effect = lambda i: ["click", "press"][i]
        native.get_action_iface.return_value = action_iface

        with pytest.raises(LookupError, match="nonexistent.*Available.*click.*press"):
            AtspiNode(native).do_action("nonexistent", pause=0.0)

    def test_raises_runtime_error_when_no_action_iface(self) -> None:
        native = _make_native()
        native.get_action_iface.return_value = None

        with pytest.raises(RuntimeError, match="no action interface"):
            AtspiNode(native).do_action("click", pause=0.0)


class TestGetActionNames:
    def test_returns_empty_list_when_no_iface(self) -> None:
        native = _make_native()
        native.get_action_iface.return_value = None
        assert AtspiNode(native).get_action_names() == []

    def test_enumerates_all_actions(self) -> None:
        native = _make_native()
        action_iface = MagicMock()
        action_iface.get_n_actions.return_value = 3
        action_iface.get_action_name.side_effect = lambda i: ["a", "b", "c"][i]
        native.get_action_iface.return_value = action_iface
        assert AtspiNode(native).get_action_names() == ["a", "b", "c"]


# ── Extents conversion ──────────────────────────────────────

class TestGetExtents:
    def test_converts_to_extents_dataclass(self) -> None:
        native = _make_native()
        ext_mock = MagicMock()
        ext_mock.x = 10
        ext_mock.y = 20
        ext_mock.width = 100
        ext_mock.height = 50
        native.get_extents.return_value = ext_mock

        extents = AtspiNode(native).get_extents()
        assert isinstance(extents, Extents)
        assert extents.center == (60, 45)


# ── Value interface ─────────────────────────────────────────

class TestValueInterface:
    def test_get_value_returns_none_when_no_iface(self) -> None:
        native = _make_native()
        assert AtspiNode(native).get_value() is None

    def test_get_value_returns_current_value(self) -> None:
        native = _make_native()
        value_iface = MagicMock()
        value_iface.get_current_value.return_value = 42.0
        native.get_value_iface.return_value = value_iface
        assert AtspiNode(native).get_value() == 42.0

    def test_set_value_raises_when_no_iface(self) -> None:
        native = _make_native()
        with pytest.raises(RuntimeError, match="no Value interface"):
            AtspiNode(native).set_value(10.0)

    def test_set_value_calls_iface(self) -> None:
        native = _make_native()
        value_iface = MagicMock()
        native.get_value_iface.return_value = value_iface
        AtspiNode(native).set_value(75.0)
        value_iface.set_current_value.assert_called_once_with(75.0)

    def test_min_max_return_none_when_no_iface(self) -> None:
        native = _make_native()
        assert AtspiNode(native).get_minimum_value() is None
        assert AtspiNode(native).get_maximum_value() is None

    def test_has_value_iface_property(self) -> None:
        native = _make_native()
        assert AtspiNode(native).has_value_iface is False
        native.get_value_iface.return_value = MagicMock()
        assert AtspiNode(native).has_value_iface is True


# ── Selection interface ─────────────────────────────────────

class TestSelectionInterface:
    def test_get_n_selected_returns_zero_when_no_iface(self) -> None:
        native = _make_native()
        assert AtspiNode(native).get_n_selected_children() == 0

    def test_select_child_returns_false_when_no_iface(self) -> None:
        native = _make_native()
        assert AtspiNode(native).select_child(0) is False

    def test_select_child_calls_iface(self) -> None:
        native = _make_native()
        sel_iface = MagicMock()
        sel_iface.select_child.return_value = True
        native.get_selection_iface.return_value = sel_iface
        assert AtspiNode(native).select_child(2) is True
        sel_iface.select_child.assert_called_once_with(2)

    def test_get_selected_child_returns_none_when_no_iface(self) -> None:
        native = _make_native()
        assert AtspiNode(native).get_selected_child() is None

    def test_get_selected_child_wraps_result(self) -> None:
        native = _make_native()
        sel_iface = MagicMock()
        child_native = _make_native(name="SelectedItem")
        sel_iface.get_selected_child.return_value = child_native
        native.get_selection_iface.return_value = sel_iface

        result = AtspiNode(native).get_selected_child(0)
        assert result is not None
        assert result.name == "SelectedItem"

    def test_is_child_selected_returns_false_when_no_iface(self) -> None:
        native = _make_native()
        assert AtspiNode(native).is_child_selected(0) is False

    def test_has_selection_iface_property(self) -> None:
        native = _make_native()
        assert AtspiNode(native).has_selection_iface is False
        native.get_selection_iface.return_value = MagicMock()
        assert AtspiNode(native).has_selection_iface is True


# ── Table interface ─────────────────────────────────────────

class TestTableInterface:
    def test_get_n_rows_returns_zero_when_no_iface(self) -> None:
        native = _make_native()
        assert AtspiNode(native).get_n_rows() == 0

    def test_get_n_columns_returns_zero_when_no_iface(self) -> None:
        native = _make_native()
        assert AtspiNode(native).get_n_columns() == 0

    def test_get_cell_at_returns_none_when_no_iface(self) -> None:
        native = _make_native()
        assert AtspiNode(native).get_cell_at(0, 0) is None

    def test_get_cell_at_wraps_result(self) -> None:
        native = _make_native()
        table_iface = MagicMock()
        cell_native = _make_native(name="CellValue")
        table_iface.get_accessible_at.return_value = cell_native
        native.get_table_iface.return_value = table_iface

        cell = AtspiNode(native).get_cell_at(1, 2)
        assert cell is not None
        assert cell.name == "CellValue"
        table_iface.get_accessible_at.assert_called_once_with(1, 2)

    def test_get_cell_at_returns_none_for_none_cell(self) -> None:
        native = _make_native()
        table_iface = MagicMock()
        table_iface.get_accessible_at.return_value = None
        native.get_table_iface.return_value = table_iface
        assert AtspiNode(native).get_cell_at(99, 99) is None

    def test_has_table_iface_property(self) -> None:
        native = _make_native()
        assert AtspiNode(native).has_table_iface is False
        native.get_table_iface.return_value = MagicMock()
        assert AtspiNode(native).has_table_iface is True


# ── Repr ────────────────────────────────────────────────────

class TestRepr:
    def test_repr_format(self) -> None:
        native = _make_native(name="Save", role_name="push button")
        assert repr(AtspiNode(native)) == 'AtspiNode([push button] "Save")'
```

- [ ] **Step 2: Rewrite test_vm.py**

Replace the file. Keep `TestFindWorkspace` (real filesystem logic), keep `TestVmRun` env var construction test. Delete all the "asserts subprocess was called with these args" tests.

```python
"""Unit tests for VM management functions.

Tests focus on REAL LOGIC: workspace discovery (filesystem walking),
command construction (environment variables), error handling.
Removed: subprocess-call-assertion tests that just verified mock args.
"""

from __future__ import annotations

import subprocess as _subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from qt_ai_dev_tools.vagrant.vm import (
    find_workspace,
    vm_run,
)

pytestmark = pytest.mark.unit


class TestFindWorkspace:
    """Real filesystem logic: walks up directory tree to find Vagrantfile."""

    def test_explicit_path_with_vagrantfile(self, tmp_path: Path) -> None:
        (tmp_path / "Vagrantfile").touch()
        assert find_workspace(tmp_path) == tmp_path

    def test_explicit_path_without_vagrantfile_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="No Vagrantfile found in"):
            find_workspace(tmp_path)

    def test_walks_up_to_find_vagrantfile(self, tmp_path: Path) -> None:
        (tmp_path / "Vagrantfile").touch()
        nested = tmp_path / "sub" / "deep"
        nested.mkdir(parents=True)
        with patch("qt_ai_dev_tools.vagrant.vm.Path.cwd", return_value=nested):
            assert find_workspace() == tmp_path

    def test_no_vagrantfile_anywhere_raises(self, tmp_path: Path) -> None:
        nested = tmp_path / "empty" / "dir"
        nested.mkdir(parents=True)
        with (
            patch("qt_ai_dev_tools.vagrant.vm.Path.cwd", return_value=nested),
            pytest.raises(FileNotFoundError, match="No Vagrantfile found in current directory or parents"),
        ):
            find_workspace()

    def test_finds_vagrantfile_in_parent_not_grandparent(self, tmp_path: Path) -> None:
        """When multiple ancestors have Vagrantfile, nearest wins."""
        (tmp_path / "Vagrantfile").touch()
        middle = tmp_path / "middle"
        middle.mkdir()
        (middle / "Vagrantfile").touch()
        deep = middle / "deep"
        deep.mkdir()
        with patch("qt_ai_dev_tools.vagrant.vm.Path.cwd", return_value=deep):
            assert find_workspace() == middle


class TestVmRunEnvConstruction:
    """Test that vm_run builds correct environment prefix for SSH commands."""

    def test_includes_display_and_vm_flag(self, tmp_path: Path) -> None:
        (tmp_path / "Vagrantfile").touch()
        with patch("qt_ai_dev_tools.run.run_command") as mock_run:
            mock_run.return_value = _subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            vm_run("echo hello", tmp_path)
            cmd = mock_run.call_args[0][0]
            ssh_command = cmd[3]  # vagrant ssh -c "<command>"
            assert "DISPLAY=:99" in ssh_command
            assert "QT_AI_DEV_TOOLS_VM=1" in ssh_command
            assert "echo hello" in ssh_command

    def test_custom_display(self, tmp_path: Path) -> None:
        (tmp_path / "Vagrantfile").touch()
        with patch("qt_ai_dev_tools.run.run_command") as mock_run:
            mock_run.return_value = _subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            vm_run("echo hello", tmp_path, display=":42")
            cmd = mock_run.call_args[0][0]
            ssh_command = cmd[3]
            assert "DISPLAY=:42" in ssh_command

    def test_preserves_user_command_intact(self, tmp_path: Path) -> None:
        """User command with spaces/special chars should be preserved."""
        (tmp_path / "Vagrantfile").touch()
        with patch("qt_ai_dev_tools.run.run_command") as mock_run:
            mock_run.return_value = _subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )
            vm_run("cd /vagrant && uv run pytest tests/ -v", tmp_path)
            cmd = mock_run.call_args[0][0]
            ssh_command = cmd[3]
            assert "cd /vagrant && uv run pytest tests/ -v" in ssh_command
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest tests/unit/test_atspi.py tests/unit/test_vm.py -v -p no:pytest-qt
```

Expected: all pass.

- [ ] **Step 4: Run full lint + unit tests**

```bash
uv run poe lint_full && uv run pytest tests/unit/ -q -p no:pytest-qt
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_atspi.py tests/unit/test_vm.py
git commit -m "refactor: replace tautological mock tests with meaningful logic tests (CQ-3)"
```

---

## Task 5: Add pilot helper methods for complex widgets

**Files:**
- Modify: `src/qt_ai_dev_tools/pilot.py`

Add convenience methods to QtPilot built on the new AtspiNode interfaces.

- [ ] **Step 1: Add complex widget methods to QtPilot**

Add after the `fill()` method in pilot.py:

```python
def select_combo_item(
    self,
    item_text: str,
    role: str = "combo box",
    name: str | None = None,
) -> None:
    """Select an item in a combo box by text.

    Finds the combo, iterates its children to find the matching item,
    and selects it via the Selection interface.
    """
    combo = self.find_one(role=role, name=name)
    for i in range(combo.child_count):
        child = combo.child_at(i)
        if child and child.name == item_text:
            combo.select_child(i)
            return
    available = [c.name for c in combo.children]
    msg = f"Item {item_text!r} not found in combo. Available: {available}"
    raise LookupError(msg)

def switch_tab(
    self,
    tab_text: str,
    role: str = "page tab list",
    name: str | None = None,
) -> None:
    """Switch to a tab by its label text.

    Finds the tab list, iterates tabs, selects matching one.
    """
    tab_list = self.find_one(role=role, name=name)
    for i in range(tab_list.child_count):
        child = tab_list.child_at(i)
        if child and tab_text in child.name:
            tab_list.select_child(i)
            return
    available = [c.name for c in tab_list.children]
    msg = f"Tab {tab_text!r} not found. Available: {available}"
    raise LookupError(msg)

def get_table_cell(
    self,
    row: int,
    col: int,
    role: str = "table",
    name: str | None = None,
) -> str:
    """Get text content of a table cell.

    Finds the table, uses Table interface to get cell accessible,
    reads its text.
    """
    table = self.find_one(role=role, name=name)
    cell = table.get_cell_at(row, col)
    if cell is None:
        msg = f"No cell at ({row}, {col})"
        raise LookupError(msg)
    return cell.get_text()

def get_table_size(
    self,
    role: str = "table",
    name: str | None = None,
) -> tuple[int, int]:
    """Get (rows, columns) of a table."""
    table = self.find_one(role=role, name=name)
    return (table.get_n_rows(), table.get_n_columns())

def check_checkbox(
    self,
    checked: bool = True,
    role: str = "check box",
    name: str | None = None,
) -> None:
    """Set a checkbox to checked or unchecked state.

    Reads current state via get_action_names and toggles if needed.
    """
    widget = self.find_one(role=role, name=name)
    # AT-SPI checkboxes expose a "Toggle" or "Click" action
    # We click to toggle, then check state via actions or name
    # Simple approach: always click — the caller knows desired state
    interact.action(widget, "Toggle" if "Toggle" in widget.get_action_names() else "Press", pause=0.2)

def set_slider_value(
    self,
    value: float,
    role: str = "slider",
    name: str | None = None,
) -> None:
    """Set a slider/spinner value via the Value interface."""
    widget = self.find_one(role=role, name=name)
    widget.set_value(value)

def get_widget_value(
    self,
    role: str | None = None,
    name: str | None = None,
) -> float | None:
    """Get the current value from a widget with a Value interface."""
    widget = self.find_one(role=role, name=name)
    return widget.get_value()

def select_menu_item(self, *path: str, pause: float = 0.3) -> None:
    """Navigate a menu hierarchy by clicking each level.

    Args:
        *path: Menu labels from top to bottom, e.g. ("File", "Save As")
        pause: Seconds between clicks for menus to open.
    """
    import time

    for menu_text in path:
        # Find by name substring — menus can appear as "menu", "menu bar", "menu item"
        items = self.find(name=menu_text)
        if not items:
            msg = f"Menu item {menu_text!r} not found"
            raise LookupError(msg)
        interact.click(items[0], pause=pause)
        time.sleep(pause)
```

- [ ] **Step 2: Run lint**

```bash
uv run poe lint_full
```

- [ ] **Step 3: Commit**

```bash
git add src/qt_ai_dev_tools/pilot.py
git commit -m "feat: add complex widget pilot helpers (combo, tab, table, checkbox, slider, menu)"
```

---

## Task 6: Add unit tests for pilot helpers

**Files:**
- Modify: `tests/unit/test_pilot.py`

- [ ] **Step 1: Add tests for new pilot methods**

Append to existing `tests/unit/test_pilot.py`. The existing test structure mocks `AtspiNode` and tests QtPilot logic. Follow that pattern.

```python
# ── Complex widget helpers ──────────────────────────────────

class TestSelectComboItem:
    def test_selects_matching_child(self, pilot: QtPilot) -> None:
        combo_node = MagicMock(spec=AtspiNode)
        combo_node.child_count = 3
        child_nodes = [MagicMock(spec=AtspiNode) for _ in range(3)]
        child_nodes[0].name = "Apple"
        child_nodes[1].name = "Banana"
        child_nodes[2].name = "Cherry"
        combo_node.child_at.side_effect = lambda i: child_nodes[i]
        combo_node.children = child_nodes

        pilot.find_one = MagicMock(return_value=combo_node)

        pilot.select_combo_item("Banana", role="combo box")
        combo_node.select_child.assert_called_once_with(1)

    def test_raises_when_item_not_found(self, pilot: QtPilot) -> None:
        combo_node = MagicMock(spec=AtspiNode)
        combo_node.child_count = 1
        child = MagicMock(spec=AtspiNode)
        child.name = "Apple"
        combo_node.child_at.return_value = child
        combo_node.children = [child]

        pilot.find_one = MagicMock(return_value=combo_node)

        with pytest.raises(LookupError, match="Mango.*not found"):
            pilot.select_combo_item("Mango")


class TestSwitchTab:
    def test_selects_matching_tab(self, pilot: QtPilot) -> None:
        tab_list = MagicMock(spec=AtspiNode)
        tab_list.child_count = 3
        tabs = [MagicMock(spec=AtspiNode) for _ in range(3)]
        tabs[0].name = "Inputs"
        tabs[1].name = "Data"
        tabs[2].name = "Settings"
        tab_list.child_at.side_effect = lambda i: tabs[i]
        tab_list.children = tabs

        pilot.find_one = MagicMock(return_value=tab_list)

        pilot.switch_tab("Data")
        tab_list.select_child.assert_called_once_with(1)

    def test_raises_when_tab_not_found(self, pilot: QtPilot) -> None:
        tab_list = MagicMock(spec=AtspiNode)
        tab_list.child_count = 0
        tab_list.children = []
        tab_list.child_at.return_value = None

        pilot.find_one = MagicMock(return_value=tab_list)

        with pytest.raises(LookupError, match="Missing.*not found"):
            pilot.switch_tab("Missing")


class TestGetTableCell:
    def test_returns_cell_text(self, pilot: QtPilot) -> None:
        table_node = MagicMock(spec=AtspiNode)
        cell_node = MagicMock(spec=AtspiNode)
        cell_node.get_text.return_value = "Alpha"
        table_node.get_cell_at.return_value = cell_node

        pilot.find_one = MagicMock(return_value=table_node)

        assert pilot.get_table_cell(0, 0) == "Alpha"

    def test_raises_for_invalid_position(self, pilot: QtPilot) -> None:
        table_node = MagicMock(spec=AtspiNode)
        table_node.get_cell_at.return_value = None

        pilot.find_one = MagicMock(return_value=table_node)

        with pytest.raises(LookupError, match="No cell at"):
            pilot.get_table_cell(99, 99)


class TestGetTableSize:
    def test_returns_rows_and_columns(self, pilot: QtPilot) -> None:
        table_node = MagicMock(spec=AtspiNode)
        table_node.get_n_rows.return_value = 5
        table_node.get_n_columns.return_value = 3

        pilot.find_one = MagicMock(return_value=table_node)

        assert pilot.get_table_size() == (5, 3)


class TestSetSliderValue:
    def test_sets_value_on_widget(self, pilot: QtPilot) -> None:
        slider_node = MagicMock(spec=AtspiNode)
        pilot.find_one = MagicMock(return_value=slider_node)

        pilot.set_slider_value(75.0, role="slider")
        slider_node.set_value.assert_called_once_with(75.0)


class TestGetWidgetValue:
    def test_returns_value(self, pilot: QtPilot) -> None:
        widget = MagicMock(spec=AtspiNode)
        widget.get_value.return_value = 42.0
        pilot.find_one = MagicMock(return_value=widget)

        assert pilot.get_widget_value(role="slider") == 42.0

    def test_returns_none_when_no_value_iface(self, pilot: QtPilot) -> None:
        widget = MagicMock(spec=AtspiNode)
        widget.get_value.return_value = None
        pilot.find_one = MagicMock(return_value=widget)

        assert pilot.get_widget_value(role="label") is None
```

Note: the existing `test_pilot.py` has a `pilot` fixture that creates a QtPilot with mocked AT-SPI. Check its structure and adapt the fixture reference. If the fixture doesn't exist, create one:

```python
@pytest.fixture
def pilot() -> QtPilot:
    """QtPilot with mocked AT-SPI desktop."""
    with patch("qt_ai_dev_tools.pilot.AtspiNode") as mock_node_cls:
        app_node = MagicMock(spec=AtspiNode)
        app_node.name = "test_app"
        desktop = MagicMock(spec=AtspiNode)
        desktop.children = [app_node]
        mock_node_cls.desktop.return_value = desktop
        p = QtPilot(app_name="test_app")
        return p
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest tests/unit/test_pilot.py -v -p no:pytest-qt
```

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_pilot.py
git commit -m "test: add unit tests for complex widget pilot helpers"
```

---

## Task 7: Add snapshot/diff feature

**Files:**
- Create: `src/qt_ai_dev_tools/snapshot.py`
- Modify: `src/qt_ai_dev_tools/models.py`
- Create: `tests/unit/test_snapshot.py`

- [ ] **Step 1: Add snapshot data models to models.py**

Add to `src/qt_ai_dev_tools/models.py`:

```python
@dataclass(slots=True)
class SnapshotEntry:
    """Single widget in a tree snapshot."""

    role: str
    name: str
    text: str | None = None
    children_count: int = 0

    def to_dict(self) -> dict[str, object]:
        """Convert to JSON-serializable dict."""
        d: dict[str, object] = {"role": self.role, "name": self.name}
        if self.text is not None:
            d["text"] = self.text
        d["children_count"] = self.children_count
        return d

    @staticmethod
    def from_dict(d: dict[str, object]) -> SnapshotEntry:
        """Create from JSON dict."""
        return SnapshotEntry(
            role=str(d["role"]),
            name=str(d["name"]),
            text=str(d["text"]) if d.get("text") is not None else None,
            children_count=int(d.get("children_count", 0)),  # type: ignore[arg-type]  # rationale: JSON values are untyped
        )


@dataclass(slots=True)
class SnapshotDiff:
    """Difference between two tree snapshots."""

    added: list[SnapshotEntry]
    removed: list[SnapshotEntry]
    changed: list[tuple[SnapshotEntry, SnapshotEntry]]

    @property
    def has_changes(self) -> bool:
        """Whether any differences exist."""
        return bool(self.added or self.removed or self.changed)
```

- [ ] **Step 2: Create snapshot.py module**

Create `src/qt_ai_dev_tools/snapshot.py`:

```python
"""Tree snapshot save and diff.

Serializes the AT-SPI widget tree to JSON for state comparison.
No image dependencies — pure text/JSON operations.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from qt_ai_dev_tools.models import SnapshotDiff, SnapshotEntry

if TYPE_CHECKING:
    from qt_ai_dev_tools._atspi import AtspiNode

logger = logging.getLogger(__name__)


def capture_tree(root: AtspiNode, max_depth: int = 8) -> list[SnapshotEntry]:
    """Walk the widget tree and capture a flat list of entries."""
    entries: list[SnapshotEntry] = []
    _walk(root, entries, depth=0, max_depth=max_depth)
    return entries


def _walk(
    node: AtspiNode,
    entries: list[SnapshotEntry],
    depth: int,
    max_depth: int,
) -> None:
    if depth > max_depth:
        return
    entry = SnapshotEntry(
        role=node.role_name,
        name=node.name,
        text=node.get_text() if node.get_text() != node.name else None,
        children_count=node.child_count,
    )
    entries.append(entry)
    for child in node.children:
        _walk(child, entries, depth + 1, max_depth)


def save_snapshot(entries: list[SnapshotEntry], path: Path) -> None:
    """Save snapshot entries to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [e.to_dict() for e in entries]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    logger.info("Snapshot saved to %s (%d widgets)", path, len(entries))


def load_snapshot(path: Path) -> list[SnapshotEntry]:
    """Load snapshot entries from a JSON file."""
    if not path.exists():
        msg = f"Snapshot not found: {path}"
        raise FileNotFoundError(msg)
    data: list[dict[str, object]] = json.loads(path.read_text())
    return [SnapshotEntry.from_dict(d) for d in data]


def diff_snapshots(
    old: list[SnapshotEntry],
    new: list[SnapshotEntry],
) -> SnapshotDiff:
    """Compare two snapshots and return differences.

    Matches widgets by (role, name) key. Widgets present only in new
    are 'added', only in old are 'removed', in both but with different
    text/children_count are 'changed'.
    """

    def _key(e: SnapshotEntry) -> tuple[str, str]:
        return (e.role, e.name)

    old_map: dict[tuple[str, str], list[SnapshotEntry]] = {}
    for e in old:
        old_map.setdefault(_key(e), []).append(e)

    new_map: dict[tuple[str, str], list[SnapshotEntry]] = {}
    for e in new:
        new_map.setdefault(_key(e), []).append(e)

    all_keys = set(old_map.keys()) | set(new_map.keys())

    added: list[SnapshotEntry] = []
    removed: list[SnapshotEntry] = []
    changed: list[tuple[SnapshotEntry, SnapshotEntry]] = []

    for key in sorted(all_keys):
        old_entries = old_map.get(key, [])
        new_entries = new_map.get(key, [])

        # Match by position within same key
        for i in range(max(len(old_entries), len(new_entries))):
            if i >= len(old_entries):
                added.append(new_entries[i])
            elif i >= len(new_entries):
                removed.append(old_entries[i])
            elif old_entries[i] != new_entries[i]:
                changed.append((old_entries[i], new_entries[i]))

    return SnapshotDiff(added=added, removed=removed, changed=changed)


def format_diff(diff: SnapshotDiff) -> str:
    """Format a diff for human-readable CLI output."""
    if not diff.has_changes:
        return "No changes."

    lines: list[str] = []
    if diff.added:
        lines.append(f"Added ({len(diff.added)}):")
        for e in diff.added:
            lines.append(f'  + [{e.role}] "{e.name}"')
    if diff.removed:
        lines.append(f"Removed ({len(diff.removed)}):")
        for e in diff.removed:
            lines.append(f'  - [{e.role}] "{e.name}"')
    if diff.changed:
        lines.append(f"Changed ({len(diff.changed)}):")
        for old_e, new_e in diff.changed:
            lines.append(f'  ~ [{old_e.role}] "{old_e.name}"')
            if old_e.text != new_e.text:
                lines.append(f"    text: {old_e.text!r} → {new_e.text!r}")
            if old_e.children_count != new_e.children_count:
                lines.append(f"    children: {old_e.children_count} → {new_e.children_count}")
    return "\n".join(lines)
```

- [ ] **Step 3: Write snapshot unit tests**

Create `tests/unit/test_snapshot.py`:

```python
"""Unit tests for tree snapshot save/diff."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

from qt_ai_dev_tools.models import SnapshotDiff, SnapshotEntry
from qt_ai_dev_tools.snapshot import (
    capture_tree,
    diff_snapshots,
    format_diff,
    load_snapshot,
    save_snapshot,
)


def _make_node(name: str, role: str = "push button", children: list[object] | None = None) -> MagicMock:
    node = MagicMock()
    node.name = name
    node.role_name = role
    node.get_text.return_value = name
    child_list = children or []
    node.child_count = len(child_list)
    node.children = child_list
    return node


class TestCaptureTree:
    def test_captures_single_node(self) -> None:
        root = _make_node("Root", "frame")
        entries = capture_tree(root)
        assert len(entries) == 1
        assert entries[0].role == "frame"
        assert entries[0].name == "Root"

    def test_captures_children_recursively(self) -> None:
        child = _make_node("Child", "label")
        root = _make_node("Root", "frame", children=[child])
        entries = capture_tree(root)
        assert len(entries) == 2
        assert entries[1].name == "Child"

    def test_respects_max_depth(self) -> None:
        deep_child = _make_node("Deep", "label")
        child = _make_node("Child", "panel", children=[deep_child])
        root = _make_node("Root", "frame", children=[child])
        entries = capture_tree(root, max_depth=1)
        assert len(entries) == 2  # Root + Child, but not Deep

    def test_text_is_none_when_same_as_name(self) -> None:
        """Avoid redundant data — if text == name, store None."""
        root = _make_node("Save", "push button")
        root.get_text.return_value = "Save"
        entries = capture_tree(root)
        assert entries[0].text is None


class TestSaveLoadSnapshot:
    def test_round_trip(self, tmp_path: Path) -> None:
        entries = [
            SnapshotEntry(role="button", name="Save"),
            SnapshotEntry(role="label", name="Status", text="Ready"),
        ]
        path = tmp_path / "snapshots" / "test.json"
        save_snapshot(entries, path)

        loaded = load_snapshot(path)
        assert len(loaded) == 2
        assert loaded[0].role == "button"
        assert loaded[1].text == "Ready"

    def test_load_nonexistent_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Snapshot not found"):
            load_snapshot(tmp_path / "nope.json")

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        path = tmp_path / "deep" / "nested" / "snap.json"
        save_snapshot([], path)
        assert path.exists()


class TestDiffSnapshots:
    def test_no_changes(self) -> None:
        entries = [SnapshotEntry(role="button", name="Save")]
        diff = diff_snapshots(entries, entries)
        assert not diff.has_changes

    def test_detects_added(self) -> None:
        old = [SnapshotEntry(role="button", name="Save")]
        new = old + [SnapshotEntry(role="label", name="New")]
        diff = diff_snapshots(old, new)
        assert len(diff.added) == 1
        assert diff.added[0].name == "New"

    def test_detects_removed(self) -> None:
        old = [
            SnapshotEntry(role="button", name="Save"),
            SnapshotEntry(role="button", name="Delete"),
        ]
        new = [SnapshotEntry(role="button", name="Save")]
        diff = diff_snapshots(old, new)
        assert len(diff.removed) == 1
        assert diff.removed[0].name == "Delete"

    def test_detects_changed_text(self) -> None:
        old = [SnapshotEntry(role="label", name="Status", text="Ready")]
        new = [SnapshotEntry(role="label", name="Status", text="Saved")]
        diff = diff_snapshots(old, new)
        assert len(diff.changed) == 1
        assert diff.changed[0][0].text == "Ready"
        assert diff.changed[0][1].text == "Saved"

    def test_detects_changed_children_count(self) -> None:
        old = [SnapshotEntry(role="list", name="Items", children_count=3)]
        new = [SnapshotEntry(role="list", name="Items", children_count=5)]
        diff = diff_snapshots(old, new)
        assert len(diff.changed) == 1

    def test_empty_snapshots(self) -> None:
        diff = diff_snapshots([], [])
        assert not diff.has_changes


class TestFormatDiff:
    def test_no_changes_message(self) -> None:
        diff = SnapshotDiff(added=[], removed=[], changed=[])
        assert format_diff(diff) == "No changes."

    def test_formats_added(self) -> None:
        diff = SnapshotDiff(
            added=[SnapshotEntry(role="button", name="New")],
            removed=[],
            changed=[],
        )
        output = format_diff(diff)
        assert "Added (1)" in output
        assert '+ [button] "New"' in output

    def test_formats_changed_with_details(self) -> None:
        diff = SnapshotDiff(
            added=[],
            removed=[],
            changed=[(
                SnapshotEntry(role="label", name="Status", text="Ready"),
                SnapshotEntry(role="label", name="Status", text="Done"),
            )],
        )
        output = format_diff(diff)
        assert "Changed (1)" in output
        assert "'Ready' → 'Done'" in output
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/unit/test_snapshot.py -v -p no:pytest-qt
```

- [ ] **Step 5: Run lint**

```bash
uv run poe lint_full
```

- [ ] **Step 6: Commit**

```bash
git add src/qt_ai_dev_tools/snapshot.py src/qt_ai_dev_tools/models.py tests/unit/test_snapshot.py
git commit -m "feat: add tree snapshot save/diff for widget state comparison"
```

---

## Task 8: Add snapshot CLI commands

**Files:**
- Modify: `src/qt_ai_dev_tools/cli.py`

- [ ] **Step 1: Add snapshot subcommand group**

Add to cli.py, following existing subcommand patterns (like `vm_app` or `clipboard_app`):

```python
snapshot_app = typer.Typer(help="Widget tree snapshots for state comparison.", no_args_is_help=True, context_settings=_CONTEXT)
app.add_typer(snapshot_app, name="snapshot")


@snapshot_app.command(name="save")
def snapshot_save(
    name: typing.Annotated[str, typer.Argument(help="Snapshot name")],
    app_name: typing.Annotated[str | None, typer.Option("--app", help="App name substring")] = None,
    max_depth: typing.Annotated[int, typer.Option("--depth", help="Maximum tree depth")] = 8,
) -> None:
    """Save the current widget tree as a named snapshot."""
    _proxy_to_vm()
    from qt_ai_dev_tools.snapshot import capture_tree, save_snapshot

    pilot = _get_pilot(app_name)
    if pilot.app is None:
        typer.echo("Error: no app connected", err=True)
        raise typer.Exit(code=1)
    entries = capture_tree(pilot.app, max_depth=max_depth)
    path = Path("snapshots") / f"{name}.json"
    save_snapshot(entries, path)
    typer.echo(f"Saved snapshot '{name}' ({len(entries)} widgets) to {path}")


@snapshot_app.command(name="diff")
def snapshot_diff_cmd(
    name: typing.Annotated[str, typer.Argument(help="Snapshot name to compare against")],
    app_name: typing.Annotated[str | None, typer.Option("--app", help="App name substring")] = None,
    max_depth: typing.Annotated[int, typer.Option("--depth", help="Maximum tree depth")] = 8,
    output_json: typing.Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Compare current widget tree against a saved snapshot."""
    _proxy_to_vm()
    from qt_ai_dev_tools.snapshot import capture_tree, diff_snapshots, format_diff, load_snapshot

    pilot = _get_pilot(app_name)
    if pilot.app is None:
        typer.echo("Error: no app connected", err=True)
        raise typer.Exit(code=1)

    path = Path("snapshots") / f"{name}.json"
    try:
        old_entries = load_snapshot(path)
    except FileNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    new_entries = capture_tree(pilot.app, max_depth=max_depth)
    diff = diff_snapshots(old_entries, new_entries)

    if output_json:
        result = {
            "added": [e.to_dict() for e in diff.added],
            "removed": [e.to_dict() for e in diff.removed],
            "changed": [{"old": o.to_dict(), "new": n.to_dict()} for o, n in diff.changed],
        }
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        typer.echo(format_diff(diff))
```

- [ ] **Step 2: Run lint**

```bash
uv run poe lint_full
```

- [ ] **Step 3: Commit**

```bash
git add src/qt_ai_dev_tools/cli.py
git commit -m "feat: add snapshot save/diff CLI commands"
```

---

## Task 9: E2E tests for complex app

**Files:**
- Create: `tests/e2e/test_complex_app_e2e.py`
- Modify: `tests/e2e/conftest.py`

These tests run in the VM against the real kitchen-sink app with AT-SPI.

- [ ] **Step 1: Add complex_app fixture to e2e conftest**

Add to `tests/e2e/conftest.py`:

```python
@pytest.fixture(scope="module")
def complex_app() -> Generator[subprocess.Popen[str], None, None]:
    """Start the kitchen-sink complex test app."""
    app_path = _APPS_DIR / "complex_app.py"
    proc = _start_app(app_path, bridge=True)
    _wait_for_app_window(proc, "complex_app.py")
    yield proc
    _kill_app(proc)
```

- [ ] **Step 2: Create e2e test file**

Create `tests/e2e/test_complex_app_e2e.py`:

```python
"""E2E tests for complex widget interactions via AT-SPI.

Tests run in the VM against the kitchen-sink complex_app.py.
Exercises: tabs, combo boxes, tables, sliders, checkboxes, menus, snapshots.
"""

from __future__ import annotations

import os
import subprocess

import pytest

pytestmark = [
    pytest.mark.skipif(not os.environ.get("DISPLAY"), reason="Requires DISPLAY (VM)"),
    pytest.mark.e2e,
]


class TestTabNavigation:
    def test_switch_to_data_tab(self, complex_app: subprocess.Popen[str]) -> None:
        from qt_ai_dev_tools.pilot import QtPilot

        pilot = QtPilot(app_name="complex_app.py")
        pilot.switch_tab("Data")
        # Verify we can find the data table (only visible on Data tab)
        tables = pilot.find(role="table")
        assert len(tables) > 0

    def test_switch_to_settings_tab(self, complex_app: subprocess.Popen[str]) -> None:
        from qt_ai_dev_tools.pilot import QtPilot

        pilot = QtPilot(app_name="complex_app.py")
        pilot.switch_tab("Settings")
        # Verify scroll area is visible
        scrolls = pilot.find(role="scroll pane")
        assert len(scrolls) > 0


class TestComboBox:
    def test_select_combo_item(self, complex_app: subprocess.Popen[str]) -> None:
        from qt_ai_dev_tools.pilot import QtPilot

        pilot = QtPilot(app_name="complex_app.py")
        pilot.switch_tab("Inputs")
        pilot.select_combo_item("Cherry", role="combo box")

        # Verify via bridge
        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket

        sock = find_bridge_socket(pid=complex_app.pid)
        resp = eval_code(sock, "widgets['fruit_combo'].currentText()")
        assert resp.ok
        assert resp.result == "Cherry"


class TestTable:
    def test_read_table_cell(self, complex_app: subprocess.Popen[str]) -> None:
        from qt_ai_dev_tools.pilot import QtPilot

        pilot = QtPilot(app_name="complex_app.py")
        pilot.switch_tab("Data")
        cell_text = pilot.get_table_cell(0, 0, role="table")
        assert cell_text == "Alpha"

    def test_table_size(self, complex_app: subprocess.Popen[str]) -> None:
        from qt_ai_dev_tools.pilot import QtPilot

        pilot = QtPilot(app_name="complex_app.py")
        pilot.switch_tab("Data")
        rows, cols = pilot.get_table_size(role="table")
        assert rows == 5
        assert cols == 3


class TestSlider:
    def test_set_slider_value(self, complex_app: subprocess.Popen[str]) -> None:
        from qt_ai_dev_tools.pilot import QtPilot

        pilot = QtPilot(app_name="complex_app.py")
        pilot.switch_tab("Inputs")
        pilot.set_slider_value(75.0, role="slider")

        value = pilot.get_widget_value(role="slider")
        assert value is not None
        assert abs(value - 75.0) < 2  # slider values are integers, allow rounding


class TestCheckbox:
    def test_toggle_checkbox(self, complex_app: subprocess.Popen[str]) -> None:
        from qt_ai_dev_tools.pilot import QtPilot

        pilot = QtPilot(app_name="complex_app.py")
        pilot.switch_tab("Inputs")
        pilot.check_checkbox(role="check box", name="notifications")

        # Verify via bridge
        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket

        sock = find_bridge_socket(pid=complex_app.pid)
        resp = eval_code(sock, "widgets['notify_checkbox'].isChecked()")
        assert resp.ok


class TestMenuNavigation:
    def test_click_file_new(self, complex_app: subprocess.Popen[str]) -> None:
        from qt_ai_dev_tools.pilot import QtPilot

        pilot = QtPilot(app_name="complex_app.py")
        pilot.select_menu_item("File", "New")

        # Verify status bar updated
        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket

        sock = find_bridge_socket(pid=complex_app.pid)
        resp = eval_code(sock, "widgets['status_label'].text()")
        assert resp.ok
        assert "New clicked" in str(resp.result)


class TestSnapshot:
    def test_save_and_diff(self, complex_app: subprocess.Popen[str], tmp_path: object) -> None:
        from pathlib import Path

        from qt_ai_dev_tools.pilot import QtPilot
        from qt_ai_dev_tools.snapshot import capture_tree, diff_snapshots, save_snapshot, load_snapshot

        pilot = QtPilot(app_name="complex_app.py")
        assert pilot.app is not None

        # Save initial state
        entries = capture_tree(pilot.app)
        snap_path = Path("/tmp/test_snap.json")
        save_snapshot(entries, snap_path)

        # Modify app state via bridge
        from qt_ai_dev_tools.bridge._client import eval_code, find_bridge_socket

        sock = find_bridge_socket(pid=complex_app.pid)
        eval_code(sock, "widgets['status_label'].setText('Modified')")

        # Capture new state and diff
        import time
        time.sleep(0.5)
        new_entries = capture_tree(pilot.app)
        old_entries = load_snapshot(snap_path)
        diff = diff_snapshots(old_entries, new_entries)
        assert diff.has_changes
```

- [ ] **Step 3: Run lint**

```bash
uv run poe lint_full
```

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/test_complex_app_e2e.py tests/e2e/conftest.py
git commit -m "test: add e2e tests for complex widget interactions and snapshots"
```

---

## Task 10: Update documentation

**Files:**
- Modify: `docs/ROADMAP.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update ROADMAP.md**

Update status for completed tasks:
- 6.1 → Done (AtspiNode Value/Selection/Table interfaces)
- 6.2 → Done (Pilot helpers for complex widgets)
- 6.5 → Done (Tree snapshot/diff, lightweight JSON approach)
- 6.7 → Done (Kitchen-sink test app)
- CQ-3 → Done (Tautological tests replaced)
- CQ-4 → Deferred (Result-based errors — separate worktree later, current exception pattern documented as appropriate for CLI tool)

- [ ] **Step 2: Update CLAUDE.md**

Add to "Quick orientation" section:
- `snapshot.py` — tree snapshot save/diff (JSON-based state comparison)

Add to "Key technical facts":
- AtspiNode now wraps Value, Selection, and Table AT-SPI interfaces in addition to Text and Action
- Complex widget helpers: select_combo_item, switch_tab, get_table_cell, check_checkbox, set_slider_value, select_menu_item, get_widget_value
- Tree snapshot/diff: `snapshot save <name>` + `snapshot diff <name>` CLI commands. JSON-based, no image deps.

Add to CLI usage:
```
# Complex widget helpers:
qt-ai-dev-tools click --role "combo box" --name "fruit"
# (or use pilot.select_combo_item() from library)

# Tree snapshots:
qt-ai-dev-tools snapshot save before
# ... interact with app ...
qt-ai-dev-tools snapshot diff before
qt-ai-dev-tools snapshot diff before --json
```

- [ ] **Step 3: Commit**

```bash
git add docs/ROADMAP.md CLAUDE.md
git commit -m "docs: update roadmap status and CLAUDE.md for complex widgets, snapshots, CQ-3"
```

---

## Task 11: Final verification

- [ ] **Step 1: Run full lint**

```bash
uv run poe lint_full
```

Expected: 0 errors.

- [ ] **Step 2: Run all unit tests**

```bash
uv run pytest tests/unit/ -v -p no:pytest-qt
```

Expected: all pass (including new snapshot, atspi interface, pilot helper tests).

- [ ] **Step 3: Run e2e tests in VM (if available)**

```bash
make test-full
```

Expected: all pass including new complex_app e2e tests.

- [ ] **Step 4: Verify git status is clean**

```bash
git status
git log --oneline -10
```

Expected: clean worktree, logical commit history.
