---
name: qt-inspect-interact-verify
description: Core workflow for AI agents interacting with Qt apps -- inspect widget tree, interact, verify results
---

# Qt Inspect -> Interact -> Verify Loop

## The pattern

Every UI interaction follows three phases:

1. **Inspect** -- understand the current UI state before acting
2. **Interact** -- perform the action (click, type, select)
3. **Verify** -- confirm the action had the intended effect

Never skip phases. Blind interaction without inspection leads to clicking wrong widgets. Interaction without verification means you don't know if it worked.

All commands below run inside the VM via `qt-ai-dev-tools vm run "..."` unless you are already in a VM SSH session.

## Phase 1: Inspect

### Get the full widget tree

```bash
qt-ai-dev-tools tree
```

Output:

```
[application] "main.py"
  [frame] "My App" @(720,387 480x320)
    [filler] ""
      [label] "Status: Ready" @(736,403 448x14)
      [text] "" @(736,429 356x22)
      [push button] "Add" @(1104,429 80x22)
      [list] "" @(736,463 448x194)
      [push button] "Clear" @(736,669 80x22)
      [label] "Items: 0" @(1099,669 85x22)
```

This is your primary orientation tool. Read the tree before every interaction sequence. The tree shows:
- **Role** in brackets: `[push button]`, `[text]`, `[label]`, `[list]`
- **Name** in quotes: the accessible name (often the visible label text)
- **Position** after @: screen coordinates and size

### Filter the tree by role

When the tree is large, filter to specific widget types:

```bash
qt-ai-dev-tools tree --role "push button"
```

### Find specific widgets

```bash
# Find by role
qt-ai-dev-tools find --role "push button"

# Find by role AND name
qt-ai-dev-tools find --role "label" --name "Status"

# Get structured output for programmatic use
qt-ai-dev-tools find --role "push button" --json
```

JSON output returns:

```json
[
  {
    "role": "push button",
    "name": "Add",
    "text": "",
    "extents": {"x": 1104, "y": 429, "width": 80, "height": 22}
  }
]
```

### Read widget state

Get detailed info about a specific widget:

```bash
qt-ai-dev-tools state --role "label" --name "Items"
```

Output:

```
[label] "Items: 0"
  text: Items: 0
  extents: (1099,669 85x22)
```

### Get text content

For text fields and labels, read the text directly:

```bash
qt-ai-dev-tools text --role "text"
```

### List running apps

See what AT-SPI can see:

```bash
qt-ai-dev-tools apps
```

### Take a screenshot

Visual confirmation of what the display looks like:

```bash
qt-ai-dev-tools screenshot -o /tmp/before.png
```

### When to use which inspection command

| Goal | Command |
|------|---------|
| First look at the UI | `tree` |
| Find a button/widget to click | `find --role "push button" --name "Save"` |
| Check a label value | `text --role "label" --name "Status"` |
| Full widget details | `state --role "text" --json` |
| Visual check | `screenshot` |
| Is the app running? | `apps` or `wait --app "name"` |

## Phase 2: Interact

### Click a widget

Click by role and name:

```bash
qt-ai-dev-tools click --role "push button" --name "Add"
```

Output: `Clicked [push button] "Add" @(1104,429 80x22)`

The click uses xdotool to send a real X11 click at the widget's center coordinates. This is the most reliable interaction method.

### Type text

Type into the currently focused widget:

```bash
qt-ai-dev-tools type "Hello, world"
```

**Important:** The target widget must already be focused. Always focus or click a text field before typing.

### Press keys

Send individual keystrokes:

```bash
qt-ai-dev-tools key Return
qt-ai-dev-tools key Tab
qt-ai-dev-tools key Escape
qt-ai-dev-tools key "ctrl+a"
qt-ai-dev-tools key "ctrl+c"
qt-ai-dev-tools key BackSpace
qt-ai-dev-tools key Delete
```

### Focus a widget

Set focus to a widget via AT-SPI (falls back to click if SetFocus is not supported):

```bash
qt-ai-dev-tools focus --role "text" --name "Email"
```

### Fill a text field (focus + clear + type)

The `fill` command is a compound operation available via the Python API:

```python
from qt_ai_dev_tools.pilot import QtPilot
pilot = QtPilot()
pilot.fill(role="text", name="Email", value="user@example.com")
```

Via CLI, the equivalent sequence is:

```bash
qt-ai-dev-tools focus --role "text" --name "Email"
qt-ai-dev-tools key "ctrl+a"
qt-ai-dev-tools key Delete
qt-ai-dev-tools type "user@example.com"
```

### Focus management rules

1. **Always focus before typing.** `type` sends keystrokes to whatever is focused. If you don't focus the right widget, text goes to the wrong place.
2. **Click focuses.** After `click`, the clicked widget has focus. You can type immediately after clicking a text field.
3. **Tab navigates.** `key Tab` moves focus to the next widget in tab order.
4. **Read the tree after focus changes.** Focus can change widget state (e.g., a combo box may expand).

### When to use which interaction command

| Goal | Command |
|------|---------|
| Press a button | `click --role "push button" --name "Save"` |
| Enter text in a field | `focus --role "text"` then `type "value"` |
| Clear and replace text | `focus` then `key "ctrl+a"` then `type "new value"` |
| Submit a form | `key Return` |
| Navigate between fields | `key Tab` |
| Close a dialog | `key Escape` |
| Select all text | `key "ctrl+a"` |

## Phase 3: Verify

### Read state after interaction

After clicking a button, check the result:

```bash
# Check if a status label updated
qt-ai-dev-tools text --role "label" --name "Status"

# Check item count
qt-ai-dev-tools text --role "label" --name "Items"

# Check what's in a text field
qt-ai-dev-tools text --role "text"
```

### Re-inspect the tree

The widget tree changes after interactions (new items appear, labels update, dialogs open):

```bash
qt-ai-dev-tools tree
```

### Take a screenshot

Visual confirmation is the most reliable verification:

```bash
qt-ai-dev-tools screenshot -o /tmp/after.png
```

### Verify specific conditions

Check that a value matches your expectation:

```bash
# Read the label and check its content
RESULT=$(qt-ai-dev-tools text --role "label" --name "Items")
echo "$RESULT"  # Should show "Items: 1" after adding an item
```

### Verification strategy

After every interaction sequence:

1. **Read the target widget state** -- did the clicked button's label change? Did the text field accept input?
2. **Read related widgets** -- did the status label update? Did the item count increase?
3. **Take a screenshot if uncertain** -- visual confirmation catches things text inspection misses (layout issues, overlapping widgets, unexpected dialogs).

## Error recovery

### Click missed (widget not found)

```
Error: No widget found: role=push button, name=Save
```

**Recovery:**
1. Re-inspect the tree: `qt-ai-dev-tools tree`
2. Check if the name changed (labels can be dynamic)
3. Try partial name match: `find --role "push button" --name "Sav"`
4. Check if a dialog or overlay is blocking

### Multiple widgets found

```
Error: Multiple widgets found for role=push button, name=OK: [...]
```

**Recovery:**
1. Add more specificity to the name: `--name "OK - Save Dialog"`
2. Use the full exact name from the tree output
3. If names are truly identical, use the Python API with `find()` and index into the results

### App not responding after click

**Recovery:**
1. Take a screenshot: `screenshot -o /tmp/debug.png`
2. Check the tree: `tree` -- look for unexpected dialogs or error popups
3. The click may have opened a modal dialog. Look for `[dialog]` or `[alert]` roles
4. Try pressing Escape to dismiss unexpected dialogs: `key Escape`

### AT-SPI returns stale data

After an interaction, the tree or widget state may not update immediately.

**Recovery:**
1. Add a short delay: `sleep 0.5` between interaction and verification
2. Re-read the tree to force a fresh traversal
3. Multiple reads -- if the first read shows old data, read again after 1 second

### Text field didn't accept input

**Recovery:**
1. Confirm focus is on the right widget: `state --role "text"`
2. Clear existing content first: `key "ctrl+a"` then `key Delete`
3. Try clicking the text field before typing: `click --role "text"` then `type "value"`
4. Check for read-only fields -- some text widgets don't accept input

## Common sequences

### Add an item to a list

```bash
# 1. Inspect
qt-ai-dev-tools tree

# 2. Type the item name
qt-ai-dev-tools click --role "text"
qt-ai-dev-tools type "New item"

# 3. Click Add
qt-ai-dev-tools click --role "push button" --name "Add"

# 4. Verify
qt-ai-dev-tools text --role "label" --name "Items"
qt-ai-dev-tools tree --role "list item"
```

### Fill a form with multiple fields

```bash
# 1. Inspect -- identify all text fields
qt-ai-dev-tools find --role "text" --json

# 2. Fill each field
qt-ai-dev-tools focus --role "text" --name "Name"
qt-ai-dev-tools key "ctrl+a"
qt-ai-dev-tools type "John Doe"

qt-ai-dev-tools focus --role "text" --name "Email"
qt-ai-dev-tools key "ctrl+a"
qt-ai-dev-tools type "john@example.com"

# 3. Submit
qt-ai-dev-tools click --role "push button" --name "Submit"

# 4. Verify
qt-ai-dev-tools screenshot -o /tmp/form-result.png
qt-ai-dev-tools text --role "label" --name "Status"
```

### Navigate a menu

```bash
# 1. Inspect menu bar
qt-ai-dev-tools tree --role "menu"

# 2. Click top-level menu
qt-ai-dev-tools click --role "menu" --name "File"

# 3. Re-inspect to see menu items (they appear after click)
qt-ai-dev-tools tree --role "menu item"

# 4. Click the menu item
qt-ai-dev-tools click --role "menu item" --name "Save As"

# 5. Handle the resulting dialog
qt-ai-dev-tools tree  # look for the dialog
```

### Handle a dialog

```bash
# 1. A dialog appeared -- inspect it
qt-ai-dev-tools tree

# 2. Look for dialog-specific widgets
qt-ai-dev-tools find --role "push button"

# 3. Click the appropriate button
qt-ai-dev-tools click --role "push button" --name "OK"

# 4. Verify dialog closed
qt-ai-dev-tools tree  # dialog should be gone
```

### Iterative debugging

When something isn't working, use the screenshot-inspect-retry loop:

```bash
# See what's on screen
qt-ai-dev-tools screenshot -o /tmp/debug1.png

# Get the full tree
qt-ai-dev-tools tree

# Try the interaction
qt-ai-dev-tools click --role "push button" --name "Save"

# Check result
qt-ai-dev-tools screenshot -o /tmp/debug2.png
qt-ai-dev-tools tree
```

Compare screenshots and tree output to understand what changed and what went wrong.
