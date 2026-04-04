---
name: qt-app-interaction
description: >
  Interact with Qt/PySide apps via AT-SPI accessibility. Use when asked
  to "test the UI", "click a button", "fill a form", "inspect widgets",
  "take a screenshot", "read widget state", or any task requiring
  programmatic Qt app interaction. Covers the full
  inspect-interact-verify workflow loop.
---

# Qt App Interaction

Every UI interaction follows three phases. Never skip phases. Blind interaction without inspection leads to clicking wrong widgets. Interaction without verification means you don't know if it worked.

All UI commands auto-detect host vs VM and proxy transparently through SSH. Run them directly -- no `vm run` wrapping needed. Use `vm run` only for arbitrary non-qt-ai-dev-tools commands (launching apps, pytest, systemctl, etc.).

## Phase 1: Inspect

Understand the current UI state before acting.

**`tree`** -- full widget tree. Shows `[role] "name" @(x,y WxH)`.

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

Read this before every interaction sequence. Roles are in brackets, names in quotes, coordinates after @.

**`tree --role "push button"`** -- filter by role when the tree is large.

**`find --role "label" --name "Status"`** -- find a specific widget. Add `--json` for structured output with extents.

**`text --role "label" --name "Status"`** -- read text content of a widget.

**`state --role "text" --json`** -- full widget details (role, name, text, extents).

**`screenshot -o /tmp/before.png`** -- visual check (~14-22 KB PNG).

**`apps`** -- list AT-SPI-visible applications. **`wait --app "name" --timeout 10`** -- block until app appears.

### When to use which

| Goal | Command |
|------|---------|
| First look at the UI | `tree` |
| Find a specific widget | `find --role "push button" --name "Save"` |
| Read a label's value | `text --role "label" --name "Status"` |
| Full widget details | `state --role "text" --json` |
| Visual check | `screenshot -o /tmp/check.png` |
| Is the app running? | `apps` or `wait --app "name"` |
| Filter tree to one type | `tree --role "push button"` |
| Structured output | `find --role "text" --json` |

## Phase 2: Interact

Perform the action.

**`click --role "push button" --name "Save"`** -- click by role+name. Uses xdotool at the widget's center coordinates.

**`type "hello"`** -- type into the currently focused widget. The target widget MUST already be focused.

**`key Return`** -- send a keystroke. Common keys: `Return`, `Tab`, `Escape`, `BackSpace`, `Delete`, `Down`, `Up`, `Page_Down`, `Page_Up`. Modifiers: `"ctrl+a"`, `"ctrl+c"`, `"ctrl+v"`.

**`focus --role "text" --name "Email"`** -- set focus via AT-SPI (falls back to click).

**`fill "user@example.com" --role "text" --name "Email"`** -- focus + clear + type in one command. Preferred over manual focus+clear+type.

**`do click "Save" --role "push button" --verify "label:Status contains Saved"`** -- click + verify in one command. Add `--screenshot` to also capture after clicking.

### When to use which

| Goal | Command |
|------|---------|
| Press a button | `click --role "push button" --name "Save"` |
| Enter text in a field | `fill "value" --role "text" --name "Field"` |
| Clear and replace text | `fill "new value" --role "text" --name "Field"` |
| Append text (no clear) | `click --role "text"` then `type "value"` |
| Submit a form | `key Return` |
| Navigate between fields | `key Tab` |
| Close a dialog | `key Escape` |
| Select all text | `key "ctrl+a"` |
| Click and verify result | `do click "Save" --verify "label:Status contains Saved"` |

## Phase 3: Verify

Confirm the action worked. After every interaction sequence:

1. **Read the target widget state** -- did the label update? Did the text field accept input?

   ```bash
   qt-ai-dev-tools text --role "label" --name "Status"
   ```

2. **Read related widgets** -- did the item count increase? Did a new list item appear?

   ```bash
   qt-ai-dev-tools tree --role "list item"
   ```

3. **Take a screenshot if uncertain** -- visual confirmation catches things text inspection misses (layout issues, overlapping widgets, unexpected dialogs).

   ```bash
   qt-ai-dev-tools screenshot -o /tmp/after.png
   ```

Re-inspect the tree after interactions. The widget tree changes -- new items appear, labels update, dialogs open. Do not rely on stale tree output.

## Focus and Input Rules

These are critical. Violating them is the most common source of bugs.

- **Always focus or click a text field before typing.** `type` sends keystrokes to whatever widget currently has focus. If you skip this, text goes to the wrong place.
- **Use `fill` instead of manual focus+clear+type.** `fill` handles all three steps and is more reliable.
- **AT-SPI `editable_text.insert_text()` does NOT work with Qt.** It updates the accessibility layer but not Qt's internal model. Always use xdotool via `type`.
- **Clicking a widget gives it focus.** After `click --role "text"`, you can `type` immediately.
- **`key Tab` navigates fields** in tab order. Useful for forms.
- **Re-inspect the tree after focus changes.** Focus can change widget state (e.g., a combo box may expand its dropdown).

## Error Recovery Essentials

The three most common problems and their fixes. See [references/troubleshooting.md](references/troubleshooting.md) for the full list.

**Widget not found** -- `tree` to re-inspect. The name may have changed (labels are dynamic), or a modal dialog may be blocking interaction with the main window. Try partial name match: `find --role "push button" --name "Sav"`.

**Click had no effect** -- take a `screenshot` to see what happened. Look for a modal dialog in the tree (`[dialog]` or `[alert]`). The widget may be disabled (grayed out) or outside the visible scroll area. Use `find --json` to verify you matched the right widget.

**Text went to wrong widget** -- use `fill` instead of manual focus+type. If a modal dialog appeared and stole focus, dismiss it first (`key Escape`). Always click the target text field before typing if not using `fill`.
