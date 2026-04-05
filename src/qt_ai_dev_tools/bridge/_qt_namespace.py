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
    from PySide6.QtCore import (
        QModelIndex,
        QObject,
        Qt,
        QTimer,
    )
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QDialog,
        QDockWidget,
        QDoubleSpinBox,
        QGroupBox,
        QLabel,
        QLineEdit,
        QListView,
        QMainWindow,
        QMenuBar,
        QPlainTextEdit,
        QProgressBar,
        QPushButton,
        QRadioButton,
        QScrollArea,
        QSlider,
        QSpinBox,
        QStackedWidget,
        QStatusBar,
        QTableView,
        QTabWidget,
        QTextEdit,
        QToolBar,
        QTreeView,
        QWidget,
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
    qapp_core = QApplication.instance()
    if qapp_core is not None and isinstance(qapp_core, QApplication):
        qapp = qapp_core
        entries["app"] = qapp

        # Build widgets dict from named widgets
        widgets: dict[str, object] = {}
        for w in qapp.allWidgets():
            obj_name: str = w.objectName()
            if obj_name:
                widgets[obj_name] = w
        entries["widgets"] = widgets

        # Convenience functions — search all widgets, not just QApplication children
        def find(widget_type: type, name: str) -> object:
            """Find a single widget by type and objectName."""
            for w in qapp.allWidgets():
                if isinstance(w, widget_type) and w.objectName() == name:
                    return w
            return None

        def findall(widget_type: type) -> list[object]:
            """Find all widgets of given type."""
            result: list[object] = [w for w in qapp.allWidgets() if isinstance(w, widget_type)]
            return result

        entries["find"] = find
        entries["findall"] = findall

    return entries
