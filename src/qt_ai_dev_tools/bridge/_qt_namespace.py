"""Build pre-populated Qt namespace for bridge eval.

This module is the PySide6 boundary for the bridge — all PySide6 imports
are confined here (same pattern as _atspi.py for AT-SPI). The rest of the
bridge works with plain dict[str, object].
"""

from __future__ import annotations

import contextlib


def build_qt_namespace() -> dict[str, object]:
    """Build the pre-populated namespace with Qt imports and helpers.

    Lazily imports PySide6 -- only call this inside a Qt app process.
    """
    ns: dict[str, object] = {"_": None}

    with contextlib.suppress(ImportError):
        ns.update(_import_qt_entries())

    return ns


def _import_qt_entries() -> dict[str, object]:
    """Import PySide6 and build namespace entries."""
    from PySide6.QtCore import (  # type: ignore[import-not-found]  # rationale: PySide6 is a system dep
        QModelIndex,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QObject,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        Qt,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QTimer,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
    )
    from PySide6.QtWidgets import (  # type: ignore[import-not-found]  # rationale: PySide6 is a system dep
        QApplication,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QCheckBox,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QComboBox,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QDialog,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QDockWidget,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QDoubleSpinBox,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QGroupBox,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QLabel,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QLineEdit,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QListView,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QMainWindow,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QMenuBar,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QPlainTextEdit,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QProgressBar,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QPushButton,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QRadioButton,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QScrollArea,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QSlider,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QSpinBox,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QStackedWidget,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QStatusBar,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QTableView,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QTabWidget,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QTextEdit,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QToolBar,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QTreeView,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
        QWidget,  # type: ignore[reportUnknownVariableType]  # rationale: PySide6 not in venv
    )

    entries: dict[str, object] = {
        "QApplication": QApplication,
        "QWidget": QWidget,
        "QPushButton": QPushButton,
        "QLineEdit": QLineEdit,
        "QComboBox": QComboBox,
        "QCheckBox": QCheckBox,
        "QRadioButton": QRadioButton,
        "QLabel": QLabel,
        "QTextEdit": QTextEdit,
        "QPlainTextEdit": QPlainTextEdit,
        "QSpinBox": QSpinBox,
        "QDoubleSpinBox": QDoubleSpinBox,
        "QSlider": QSlider,
        "QProgressBar": QProgressBar,
        "QTabWidget": QTabWidget,
        "QTableView": QTableView,
        "QTreeView": QTreeView,
        "QListView": QListView,
        "QGroupBox": QGroupBox,
        "QMenuBar": QMenuBar,
        "QToolBar": QToolBar,
        "QStatusBar": QStatusBar,
        "QDialog": QDialog,
        "QMainWindow": QMainWindow,
        "QDockWidget": QDockWidget,
        "QScrollArea": QScrollArea,
        "QStackedWidget": QStackedWidget,
        "Qt": Qt,
        "QObject": QObject,
        "QTimer": QTimer,
        "QModelIndex": QModelIndex,
    }

    # Add app instance and convenience functions
    qapp = QApplication.instance()  # type: ignore[reportUnknownVariableType,reportUnknownMemberType]  # rationale: PySide6 not in venv
    if qapp is not None:
        entries["app"] = qapp

        # Build widgets dict from named widgets
        widgets: dict[str, object] = {}
        for w in qapp.allWidgets():  # type: ignore[reportUnknownVariableType,reportUnknownMemberType]  # rationale: PySide6 not in venv
            obj_name: str = w.objectName()  # type: ignore[reportUnknownMemberType]  # rationale: PySide6 not in venv
            if obj_name:
                widgets[obj_name] = w
        entries["widgets"] = widgets

        # Convenience functions
        def find(widget_type: type, name: str) -> object:
            """Find a single child widget by type and objectName."""
            return qapp.findChild(widget_type, name)  # type: ignore[reportUnknownMemberType,reportUnknownVariableType]  # rationale: PySide6 not in venv

        def findall(widget_type: type) -> list[object]:
            """Find all child widgets by type."""
            result: list[object] = list(qapp.findChildren(widget_type))  # type: ignore[reportUnknownMemberType,reportUnknownArgumentType]  # rationale: PySide6 not in venv
            return result

        entries["find"] = find
        entries["findall"] = findall

    return entries
