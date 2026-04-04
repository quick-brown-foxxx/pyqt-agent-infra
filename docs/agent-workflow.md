# Agent workflow

Recommended workflow for AI agents using qt-ai-dev-tools to interact with Qt/PySide applications.

## Workflow overview

1. **Setup** -- initialize workspace and start the VM.
2. **Launch** -- start the target app inside the VM.
3. **Inspect** -- get the widget tree to understand the UI layout.
4. **Interact** -- click, type, fill forms.
5. **Verify** -- check state and take screenshots to confirm results.
6. **Iterate** -- repeat inspect/interact/verify as needed.

UI commands (tree, click, type, screenshot, etc.) auto-detect host vs VM and proxy transparently through SSH. Run them directly from the host -- no `vm run` wrapping needed. Use `vm run` only for arbitrary non-qt-ai-dev-tools commands (launching apps, pytest, systemctl, etc.).

## Setup

```bash
qt-ai-dev-tools workspace init --path .
qt-ai-dev-tools vm up
qt-ai-dev-tools vm status          # confirm Xvfb, openbox, AT-SPI running
```

## Common command sequences

### Start an app and inspect it

```bash
qt-ai-dev-tools vm run "python /vagrant/app/main.py &"   # vm run for launching apps
qt-ai-dev-tools wait --app "main.py" --timeout 10         # auto-proxies to VM
qt-ai-dev-tools tree                                       # auto-proxies to VM
```

Always use `wait` before interacting with a newly launched app. AT-SPI needs time to register the application. Note that `vm run` is used here only to launch the Python process -- the `wait` and `tree` commands auto-proxy to the VM.

### Inspect the widget tree

```bash
qt-ai-dev-tools tree                          # full tree, human-readable
qt-ai-dev-tools tree --role "push button"     # filter by role
qt-ai-dev-tools find --role "label" --json    # structured output for parsing
```

Start with `tree` to get the full picture. Use `find` with `--json` when you need machine-parseable output for decision-making.

### Fill a form

```bash
qt-ai-dev-tools fill --role "text" --name "email" --value "user@example.com"
qt-ai-dev-tools fill --role "text" --name "password" --value "secret123"
qt-ai-dev-tools click --role "push button" --name "Submit"
qt-ai-dev-tools find --role "label" --name "status" --json
```

Use `fill` instead of separate focus + type steps. `fill` handles focusing, clearing existing text, and typing in one command.

### Navigate UI and verify

```bash
qt-ai-dev-tools tree                          # find navigation targets
qt-ai-dev-tools click --role "push button" --name "Settings"
qt-ai-dev-tools tree                          # re-inspect after navigation
qt-ai-dev-tools screenshot -o /tmp/after.png  # visual confirmation
```

### Click with verification

```bash
qt-ai-dev-tools do click "Save" --verify "status contains 'Saved'"
```

The `do` command combines interaction with a state assertion, returning both the action result and verification outcome.

## Tips for agents

**Always tree first.** Before any interaction, run `tree` to understand the current UI layout. Widget names and positions change as the app state changes.

**Use --json for parsing.** Human-readable output is good for understanding; `--json` is better when you need to extract specific values or make decisions based on widget state.

**Screenshot after complex interactions.** When a sequence of actions modifies the UI significantly, take a screenshot to visually confirm the result. Screenshots are small (~14-22 KB PNG).

**Use wait before interacting.** After launching an app or triggering a dialog, always `wait` for the target to appear in the AT-SPI tree. Race conditions are the most common source of "widget not found" errors.

**Use fill for form fields.** `fill` is more reliable than manually focusing and typing. It handles clearing existing content and ensures focus is on the correct widget.

**Re-inspect after actions.** The widget tree is a snapshot. After clicking a button that opens a dialog or changes the view, run `tree` again to see the updated state.

**Filter by role and name.** The widget tree can be large. Use `--role` and `--name` filters to narrow results: `find --role "push button" --name "Save"`.

## Error recovery

### Widget not found

The widget may not exist yet, or the tree may have changed. Recovery:
1. Run `tree` to see the current state.
2. Check if the app is still running: `apps`.
3. The widget may have a different name or role than expected -- inspect the tree output carefully.

### Click did not produce expected result

Coordinate-based clicks can miss if the window moved or resized. Recovery:
1. Try AT-SPI action instead: `click --role "push button" --name "Save"` uses AT-SPI's action interface (more reliable than coordinates for buttons).
2. Take a screenshot to see what actually happened.
3. Re-inspect the tree -- the widget state may have changed.

### Text input was lost or went to wrong widget

Focus may not be where you expect. Recovery:
1. Use `fill` which handles focus explicitly.
2. If using `type` directly, first click the target widget to ensure focus.
3. Check for modal dialogs that may have stolen focus -- run `tree` to see if a dialog appeared.

### Stale tree data

AT-SPI provides live data, but the tree you inspected may no longer reflect reality after an interaction. Recovery:
1. Always re-run `tree` or `find` after actions that change the UI.
2. Do not cache widget references across multiple command invocations -- each CLI call discovers widgets fresh.

### App crashed or became unresponsive

1. Check if the app is still listed: `apps`.
2. Take a screenshot to see the current display state.
3. If the app is gone, relaunch it and start over.
4. If the app is hung, you may need to kill and restart it: `qt-ai-dev-tools vm run "pkill -f main.py"`.
