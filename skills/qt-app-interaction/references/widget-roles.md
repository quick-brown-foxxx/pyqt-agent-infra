# AT-SPI Widget Role Reference

Mapping between Qt widget classes and AT-SPI accessibility roles. Use these role strings with `--role` in qt-ai-dev-tools commands.

| Qt Widget | AT-SPI Role | Notes |
|-----------|-------------|-------|
| QPushButton | `push button` | Most reliable to click |
| QToolButton | `push button` | Same role as QPushButton |
| QLineEdit | `text` | Single-line text input |
| QTextEdit | `text` | Multi-line text input |
| QPlainTextEdit | `text` | Multi-line text input |
| QLabel | `label` | Read-only, primary verification target |
| QCheckBox | `check box` | Toggle with click |
| QRadioButton | `radio button` | Select with click |
| QComboBox | `combo box` | Click to open, then click menu item |
| QListWidget | `list` | Contains list items |
| QListWidgetItem | `list item` | Click to select |
| QTableWidget | `table` | Contains table cells |
| QTreeWidget | `tree` | Contains tree items |
| QTreeWidgetItem | `tree item` | Click to select, double-click to expand |
| QTabWidget | `page tab list` | Contains page tabs |
| QTabBar tab | `page tab` | Click to switch |
| QMenuBar | `menu bar` | Contains menus |
| QMenu | `menu` | Click to open |
| QAction | `menu item` | Click to activate |
| QDialog | `dialog` | Modal window |
| QMessageBox | `alert` | Message/question dialog |
| QFileDialog | `file chooser` | File selection dialog |
| QScrollArea | `scroll pane` | Scrollable container |
| QGroupBox | `panel` | Grouping container |
| QFrame | `filler` or `panel` | Container/separator |
| QMainWindow | `frame` | Top-level window |
| QStatusBar | `status bar` | Bottom status area |
| QProgressBar | `progress bar` | Read value via state/text |
| QSlider | `slider` | Interact via click at position |
| QSpinBox | `spin button` | Type value or use arrows |
| QToolBar | `tool bar` | Contains tool buttons |

## Key observations

- Multiple Qt widgets map to the same role (`text` covers QLineEdit, QTextEdit, QPlainTextEdit). Use `--name` to distinguish them.
- Roles are exact strings. `"push button"` works, `"pushbutton"` does not.
- Use `tree` to discover which roles exist in a given app. Not all apps use all widget types.
- Container widgets (`list`, `table`, `tree`, `page tab list`) hold child items. Inspect their children, not the container itself, to interact with individual entries.
