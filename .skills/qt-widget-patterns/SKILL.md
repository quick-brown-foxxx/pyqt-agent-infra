---
name: qt-widget-patterns
description: Patterns for identifying and interacting with specific Qt widget types via AT-SPI
---

# Qt Widget Patterns

## Widget identification strategies

### By role (most reliable)

Every Qt widget exposes an AT-SPI role. Use `--role` to filter:

```bash
qt-ai-dev-tools find --role "push button"
qt-ai-dev-tools find --role "text"
qt-ai-dev-tools find --role "label"
```

Roles are exact strings. Use `tree` to discover what roles exist in your app.

### By name (accessible name)

The name is the widget's accessible label -- often the visible text on the widget:

```bash
qt-ai-dev-tools find --role "push button" --name "Save"
```

Name matching is **substring-based**. `--name "Sav"` matches "Save", "Save As", "Unsaved". Use the most specific substring that uniquely identifies the widget.

### By role + name combination

Always prefer combining role and name for precision:

```bash
# BAD -- "Save" could match a label, menu item, or button
qt-ai-dev-tools find --name "Save"

# GOOD -- unambiguous
qt-ai-dev-tools find --role "push button" --name "Save"
```

### By tree position (when names are ambiguous)

When multiple widgets have the same role and name, use the Python API to select by index:

```python
from qt_ai_dev_tools.pilot import QtPilot
pilot = QtPilot()
buttons = pilot.find(role="push button", name="OK")
# buttons[0] is the first match, buttons[1] the second, etc.
pilot.click(buttons[0])
```

### Discovery workflow

When you encounter a new app:

```bash
# 1. Full tree -- understand the structure
qt-ai-dev-tools tree

# 2. List all roles present
qt-ai-dev-tools tree --role "push button"    # buttons
qt-ai-dev-tools tree --role "text"           # text inputs
qt-ai-dev-tools tree --role "label"          # labels
qt-ai-dev-tools tree --role "list"           # lists
qt-ai-dev-tools tree --role "menu"           # menus

# 3. JSON for structured analysis
qt-ai-dev-tools find --role "push button" --json
```

## Widget types and how to interact

### Push button (`[push button]`)

**Qt class:** QPushButton, QToolButton

**Identify:**
```bash
qt-ai-dev-tools find --role "push button" --name "Save"
```

**Interact:**
```bash
qt-ai-dev-tools click --role "push button" --name "Save"
```

**Verify:**
```bash
# Check if clicking had an effect on other widgets
qt-ai-dev-tools text --role "label" --name "Status"
qt-ai-dev-tools screenshot -o /tmp/after-click.png
```

**Notes:**
- Clicking uses xdotool at the widget center. This is the most reliable method.
- AT-SPI "Press" action also works for buttons but xdotool click is preferred.
- Disabled buttons can still be found but clicking them has no effect. Check the screenshot to verify button appearance.

### Text input (`[text]`)

**Qt class:** QLineEdit, QTextEdit, QPlainTextEdit

**Identify:**
```bash
qt-ai-dev-tools find --role "text"
qt-ai-dev-tools find --role "text" --name "Search"
```

**Read current value:**
```bash
qt-ai-dev-tools text --role "text" --name "Search"
```

**Type new value (append):**
```bash
qt-ai-dev-tools click --role "text" --name "Search"
qt-ai-dev-tools type "search query"
```

**Clear and replace:**
```bash
qt-ai-dev-tools focus --role "text" --name "Search"
qt-ai-dev-tools key "ctrl+a"
qt-ai-dev-tools key Delete
qt-ai-dev-tools type "new value"
```

**Notes:**
- MUST focus or click the text field before typing. `type` sends keystrokes to whatever widget currently has focus.
- AT-SPI `editable_text.insert_text()` does NOT work with Qt. Always use xdotool via `type` command.
- For multi-line text (QTextEdit), use `key Return` to insert newlines.
- QLineEdit often has a placeholder text visible in the name. Check `text` for the actual content.

### Label (`[label]`)

**Qt class:** QLabel

**Identify:**
```bash
qt-ai-dev-tools find --role "label" --name "Status"
```

**Read value:**
```bash
qt-ai-dev-tools text --role "label" --name "Status"
```

**Notes:**
- Labels are read-only. They are your primary verification targets after interactions.
- Label names update in real-time as the app changes state.
- A label's `name` property IS its text. `text` command also returns the same value.

### List (`[list]`) and list items (`[list item]`)

**Qt class:** QListWidget, QListView

**Identify the list:**
```bash
qt-ai-dev-tools find --role "list"
```

**Read list items:**
```bash
qt-ai-dev-tools tree --role "list item"
```

Or via JSON:
```bash
qt-ai-dev-tools find --role "list item" --json
```

**Select an item by clicking:**
```bash
qt-ai-dev-tools click --role "list item" --name "Item text"
```

**Notes:**
- List items appear as children of the `[list]` widget in the tree.
- Items may be dynamically created -- re-inspect after adding items.
- For long lists, items outside the visible area may not be in the AT-SPI tree until scrolled into view.

### Combo box / dropdown (`[combo box]`)

**Qt class:** QComboBox

**Identify:**
```bash
qt-ai-dev-tools find --role "combo box"
```

**Read current selection:**
```bash
qt-ai-dev-tools text --role "combo box" --name "Country"
```

**Open the dropdown:**
```bash
qt-ai-dev-tools click --role "combo box" --name "Country"
```

**Select an option:**
```bash
# After opening, menu items appear in the tree
qt-ai-dev-tools tree --role "menu item"
qt-ai-dev-tools click --role "menu item" --name "France"
```

**Alternative: keyboard navigation:**
```bash
qt-ai-dev-tools click --role "combo box" --name "Country"
qt-ai-dev-tools key Down
qt-ai-dev-tools key Down
qt-ai-dev-tools key Return
```

**Notes:**
- The dropdown items only appear in the AT-SPI tree AFTER the combo box is clicked/opened.
- Re-inspect the tree after clicking the combo box to see the options.
- Keyboard navigation (Up/Down arrows + Return) is often more reliable than clicking menu items.

### Tab widget (`[page tab list]`, `[page tab]`)

**Qt class:** QTabWidget

**Identify tabs:**
```bash
qt-ai-dev-tools find --role "page tab"
```

**Switch tab:**
```bash
qt-ai-dev-tools click --role "page tab" --name "Settings"
```

**Verify tab switch:**
```bash
# The tree under the tab changes when you switch
qt-ai-dev-tools tree
```

**Notes:**
- The tab bar has role `[page tab list]`. Individual tabs have role `[page tab]`.
- Clicking a tab changes which widgets are visible in the tree (the tab's content panel updates).
- Always re-inspect the tree after switching tabs.

### Menu bar and menus (`[menu bar]`, `[menu]`, `[menu item]`)

**Qt class:** QMenuBar, QMenu, QAction

**Inspect menu bar:**
```bash
qt-ai-dev-tools find --role "menu bar"
qt-ai-dev-tools find --role "menu"
```

**Open a menu:**
```bash
qt-ai-dev-tools click --role "menu" --name "File"
```

**Select a menu item (after opening):**
```bash
qt-ai-dev-tools tree --role "menu item"
qt-ai-dev-tools click --role "menu item" --name "Save"
```

**Navigate submenus:**
```bash
# Open top menu
qt-ai-dev-tools click --role "menu" --name "Edit"
# Re-inspect to see items
qt-ai-dev-tools tree --role "menu item"
# Click submenu
qt-ai-dev-tools click --role "menu item" --name "Preferences"
# Re-inspect for submenu items
qt-ai-dev-tools tree --role "menu item"
```

**Notes:**
- Menu items only appear in the AT-SPI tree AFTER their parent menu is opened.
- You must re-inspect (`tree`) between opening a menu and clicking an item.
- Clicking outside an open menu closes it. If you need to abort, use `key Escape`.

### Check box (`[check box]`)

**Qt class:** QCheckBox

**Identify:**
```bash
qt-ai-dev-tools find --role "check box"
```

**Toggle:**
```bash
qt-ai-dev-tools click --role "check box" --name "Remember me"
```

**Read state:**
```bash
qt-ai-dev-tools state --role "check box" --name "Remember me" --json
```

### Radio button (`[radio button]`)

**Qt class:** QRadioButton

**Identify and select:**
```bash
qt-ai-dev-tools find --role "radio button"
qt-ai-dev-tools click --role "radio button" --name "Option B"
```

### Dialog (`[dialog]`, `[file chooser]`, `[alert]`)

**Qt class:** QDialog, QMessageBox, QFileDialog

**Detect dialog:**
```bash
qt-ai-dev-tools tree  # look for [dialog] or [alert] in the tree
```

**Handle message box:**
```bash
qt-ai-dev-tools find --role "push button"  # Find OK/Cancel/Yes/No buttons
qt-ai-dev-tools click --role "push button" --name "OK"
```

**Dismiss with keyboard:**
```bash
qt-ai-dev-tools key Escape   # Cancel/close
qt-ai-dev-tools key Return   # Accept/OK (if focused)
```

**Notes:**
- Dialogs are modal -- they block interaction with the main window until dismissed.
- If interactions with the main window suddenly stop working, check for an unexpected dialog.
- File dialogs (`[file chooser]`) are complex. Keyboard navigation is often easier than clicking through the file browser.

### Scroll area (`[scroll pane]`)

**Qt class:** QScrollArea

**Notes:**
- Widgets inside a scroll area may not appear in the AT-SPI tree if they are scrolled out of view.
- To reach hidden widgets, scroll using keyboard: click inside the scroll area, then use `key Down` / `key Up` / `key Page_Down` / `key Page_Up`.
- After scrolling, re-inspect the tree to see newly visible widgets.

## AT-SPI role reference

| Qt widget | AT-SPI role | Notes |
|-----------|-------------|-------|
| QPushButton | `push button` | Most reliable to click |
| QToolButton | `push button` | Same role as QPushButton |
| QLineEdit | `text` | Single-line text input |
| QTextEdit | `text` | Multi-line text input |
| QPlainTextEdit | `text` | Multi-line text input |
| QLabel | `label` | Read-only text, primary verification target |
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

## Troubleshooting widget issues

### Unnamed widgets

**Symptom:** Widget shows `[push button] ""` (empty name).

**Strategies:**
- Use tree position: the widget's location in the tree relative to named siblings helps identify it.
- Use coordinates: `find --role "push button" --json` and match by `extents` position.
- Via Python API, use `find()` and select by index among results with the same role.
- Take a screenshot and correlate visual position with the extents from JSON output.

### Dynamic content

**Symptom:** Widget names or tree structure change between inspections.

**Strategies:**
- Always re-inspect immediately before interacting. Don't cache widget references from minutes ago.
- Use partial name matches: `--name "Item"` instead of `--name "Item (3 of 10)"`.
- For lists that update: re-find after each add/remove operation.

### Timing issues

**Symptom:** Widget not found immediately after an interaction that should create it.

**Strategies:**
- Add a brief delay: `sleep 0.5` then re-inspect.
- Use the `wait` command for app startup: `qt-ai-dev-tools wait --app "name" --timeout 15`
- For other waits, poll in a loop:

```bash
for i in $(seq 1 10); do
  RESULT=$(qt-ai-dev-tools find --role "label" --name "Done" 2>/dev/null)
  if [ -n "$RESULT" ]; then
    echo "Found: $RESULT"
    break
  fi
  sleep 0.5
done
```

### Widget exists but click has no effect

**Causes:**
- Widget is disabled (grayed out). Take a screenshot to verify.
- Widget is behind another widget (overlap). Check extents -- do any widgets overlap?
- Widget is in a non-visible scroll area. Scroll it into view first.
- Wrong widget matched. Use `--json` to verify you have the right one.

### Tree is empty or shows only the application node

**Causes:**
- App window not yet shown. Wait for the app to fully start.
- Xvfb or openbox not running. Check `pgrep Xvfb` and `pgrep openbox`.
- AT-SPI bus not connected. Check `pgrep at-spi`.
- App not using Qt's accessibility. Most Qt apps have it enabled by default, but some explicitly disable it. Set `QT_ACCESSIBILITY=1` environment variable.
