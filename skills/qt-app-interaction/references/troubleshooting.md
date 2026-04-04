# Troubleshooting

Full error recovery patterns for qt-ai-dev-tools. Each entry: problem, symptoms, and recovery steps.

## 1. Widget not found

**Symptom:** `Error: No widget found: role=push button, name=Save`

**Recovery:**
1. Re-inspect the tree: `qt-ai-dev-tools tree`
2. Check if the name changed -- labels are dynamic, the text may have updated.
3. Try partial name match: `find --role "push button" --name "Sav"` (matching is substring-based).
4. Check if a modal dialog is blocking -- look for `[dialog]` or `[alert]` in the tree.
5. The widget may not exist yet -- add `sleep 0.5` and re-inspect.

## 2. Multiple widgets found

**Symptom:** `Error: Multiple widgets found for role=push button, name=OK`

**Recovery:**
1. Use a more specific name: `--name "OK - Save Dialog"` or the full exact name from tree output.
2. If names are truly identical, use the Python API with `find()` and index into results:
   ```python
   from qt_ai_dev_tools.pilot import QtPilot
   pilot = QtPilot()
   buttons = pilot.find(role="push button", name="OK")
   pilot.click(buttons[0])  # first match
   ```
3. Use `find --json` to differentiate by extents (position/size).

## 3. Click had no effect

**Symptom:** UI did not change after a click command.

**Recovery:**
1. Take a screenshot: `screenshot -o /tmp/debug.png` -- is the widget disabled (grayed out)?
2. Check for a modal dialog blocking the main window: `tree` and look for `[dialog]` or `[alert]`.
3. The widget may be in a scroll area and not fully visible -- scroll it into view first.
4. Verify you matched the right widget: `find --role "push button" --name "Save" --json` and check the extents.
5. Try AT-SPI action as fallback: some widgets respond better to AT-SPI's action interface than coordinate clicks.

## 4. Text input lost or went to wrong widget

**Symptom:** Typed text appeared in the wrong field, or did not appear at all.

**Recovery:**
1. Use `fill` instead of manual focus+type -- it handles focus explicitly.
2. If using `type` directly, click the target text field first: `click --role "text" --name "Email"` then `type "value"`.
3. Check for modal dialogs that may have stolen focus: `tree`.
4. Verify focus is where you expect: `state --role "text" --name "Email"`.
5. Check for read-only fields -- some text widgets don't accept input.

## 5. AT-SPI stale data

**Symptom:** Widget state reads as the old value immediately after an interaction.

**Recovery:**
1. Add a short delay: `sleep 0.5` between interaction and verification.
2. Re-read the widget: AT-SPI provides live data but the tree traversal caches during a single command invocation.
3. If still stale, wait longer and try multiple reads:
   ```bash
   sleep 1
   qt-ai-dev-tools text --role "label" --name "Status"
   ```

## 6. Unnamed widgets

**Symptom:** Widget shows `[push button] ""` (empty name) in the tree.

**Recovery:**
1. Use tree position -- identify the widget relative to named siblings in the tree hierarchy.
2. Use coordinates: `find --role "push button" --json` and match by `extents` position.
3. Via Python API, use `find()` and select by index among results with the same role.
4. Take a screenshot and correlate visual position with extents from JSON output.

## 7. Dynamic content

**Symptom:** Widget names or tree structure change between inspections.

**Recovery:**
1. Always re-inspect immediately before interacting. Do not rely on tree output from earlier.
2. Use partial name matches: `--name "Item"` instead of `--name "Item (3 of 10)"`.
3. For lists that update: re-find after each add/remove operation.
4. Expect the tree to change after any interaction -- buttons may rename, labels update, new widgets appear.

## 8. Timing issues

**Symptom:** Widget not found immediately after an interaction that should create it.

**Recovery:**
1. Use `wait` for app startup: `qt-ai-dev-tools wait --app "name" --timeout 15`.
2. Add a brief delay: `sleep 0.5` then re-inspect.
3. For other waits, poll in a loop:
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

## 9. App crashed or unresponsive

**Symptom:** Commands hang or return errors. Tree shows stale data or nothing.

**Recovery:**
1. Check if the app is still running: `qt-ai-dev-tools apps`.
2. Take a screenshot to see the current display state: `screenshot -o /tmp/debug.png`.
3. If the app is gone, relaunch it and use `wait` before interacting.
4. If the app is hung, kill and restart it:
   ```bash
   qt-ai-dev-tools vm run "pkill -f app.py"
   qt-ai-dev-tools vm run "python /vagrant/app/main.py &"
   qt-ai-dev-tools wait --app "main.py" --timeout 10
   ```

## 10. Empty tree

**Symptom:** `tree` shows only `[application] "main.py"` with no children, or nothing at all.

**Recovery:**
1. App window not yet shown -- use `wait --app "name"` and add a delay for the window to render.
2. Check Xvfb is running: `qt-ai-dev-tools vm run "pgrep Xvfb"`.
3. Check openbox is running: `qt-ai-dev-tools vm run "pgrep openbox"`.
4. Check AT-SPI bus: `qt-ai-dev-tools vm run "pgrep at-spi"`.
5. Ensure the app has accessibility enabled: set `QT_ACCESSIBILITY=1` environment variable before launching the app.
