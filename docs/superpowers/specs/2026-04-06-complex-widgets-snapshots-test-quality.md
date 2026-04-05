# Complex Widgets, Tree Snapshots & Test Quality — Design Spec

## Goal

Extend qt-ai-dev-tools to handle complex Qt widgets (combo boxes, tables, tabs, menus, checkboxes, sliders), add tree snapshot/diff for state comparison, improve test quality by replacing tautological tests, and validate everything against a rich "kitchen sink" test app.

## Scope

| Item | Roadmap Ref | Priority |
|------|-------------|----------|
| Complex widget AT-SPI interfaces | 6.1 | High |
| Complex widget pilot helpers | 6.2 | High |
| Tree snapshot/diff | 6.5 (lightweight) | Medium |
| Kitchen-sink test app | 6.7 | MUST HAVE |
| Replace tautological tests | CQ-3 | High |
| Defer Result-based errors | CQ-4 | Deferred (documented) |

## Architecture

### Layered Widget API

Three layers, each usable independently:

1. **AtspiNode interfaces** (`_atspi.py`) — typed wrappers for AT-SPI Value, Selection, and Table interfaces. Raw-but-typed access for custom/edge-case work. Follows existing pattern: `get_*_iface()` → method calls with `# type: ignore` rationale comments.

2. **Pilot helpers** (`pilot.py`) — convenient methods on `QtPilot` for common patterns. Built on Layer 1. Methods like `select_combo_item()`, `switch_tab()`, `get_table_cell()`.

3. **CLI commands** (`cli.py`) — expose new helpers via existing CLI patterns. No new subcommand groups needed — extend existing `click`/`find` or add new top-level commands.

### Tree Snapshot/Diff

New `snapshot` subcommand group in CLI. Saves `tree --json` output to files, diffs against current tree state. Pure JSON text comparison — no image dependencies.

- `snapshot save <name>` — serialize current widget tree to `<workspace>/snapshots/<name>.json`
- `snapshot diff <name>` — compare saved snapshot against current tree, show added/removed/changed widgets
- Library API: `QtPilot.snapshot()` returns tree as list of `WidgetInfo` dicts, `diff_snapshots()` compares two

### Kitchen-Sink Test App

`tests/apps/complex_app.py` — a single PySide6 app exercising all complex widget types:
- QTabWidget (3 tabs: "Inputs", "Data", "Settings")
- Tab 1 "Inputs": QComboBox, QCheckBox, QRadioButton (in QButtonGroup), QSlider, QSpinBox, QLineEdit
- Tab 2 "Data": QTableWidget (5 rows × 3 columns), QListWidget with selection
- Tab 3 "Settings": QMenuBar with File/Edit/Help menus, QScrollArea with many widgets
- Status bar showing last action
- Modal dialog triggered by menu action

Follows project standards: basedpyright strict, ruff, typed. PySide6 added to dev dependency group so type checking works on host.

### CQ-3: Test Quality

Replace tautological mock tests in `test_atspi.py` and `test_vm.py`:

**test_atspi.py** — Delete "mock returns configured value" tests. Keep and expand tests for real logic:
- `do_action()` action name lookup + error paths
- `get_text()` fallback from Text interface to name
- `children` property filtering out None values
- `get_action_names()` with empty/missing interface
- New: tests for Value/Selection/Table interfaces (from 6.1 work)

**test_vm.py** — Delete "subprocess called with these args" tests. Keep tests for real logic:
- `find_workspace()` directory walking (real filesystem logic — already good)
- `vm_run()` environment variable construction (actual string building logic)
- Error paths: missing Vagrantfile, failed commands

### CQ-4: Deferred

Result-based error handling is a codebase-wide breaking change. Deferred to a dedicated worktree/branch. The current exception pattern (RuntimeError/LookupError in core, caught at CLI boundary) is clean and appropriate for a CLI tool. Document this decision in ROADMAP.md.

## AT-SPI Interface Details

### Value Interface (sliders, spinners, progress bars)

Methods on AtspiNode:
- `get_value() -> float | None` — current value, None if no Value interface
- `set_value(value: float) -> None` — set value, raises RuntimeError if no interface or read-only
- `get_minimum_value() -> float | None`
- `get_maximum_value() -> float | None`
- `has_value_iface -> bool` — property

### Selection Interface (combo boxes, list widgets, tabs)

Methods on AtspiNode:
- `get_selected_child(index: int = 0) -> AtspiNode | None` — get nth selected child
- `select_child(index: int) -> bool` — select child by index
- `deselect_child(index: int) -> bool` — deselect child by index
- `get_n_selected_children() -> int`
- `is_child_selected(index: int) -> bool`
- `has_selection_iface -> bool` — property

### Table Interface (tables, trees)

Methods on AtspiNode:
- `get_n_rows() -> int`
- `get_n_columns() -> int`
- `get_cell_at(row: int, col: int) -> AtspiNode | None`
- `has_table_iface -> bool` — property

## Pilot Helper Methods

Built on AtspiNode interfaces:

- `select_combo_item(role, name, item_text)` — find combo, expand, select item by text
- `switch_tab(role, name, tab_text)` — find tab widget, select tab by label
- `get_table_cell(role, name, row, col)` — find table, get cell content
- `check_checkbox(role, name, checked=True)` — find checkbox, set checked state
- `set_slider_value(role, name, value)` — find slider/spinner, set value
- `select_menu_item(*path)` — navigate menu hierarchy (e.g. "File", "Save As")
- `get_value(role, name)` — get current value from slider/spinner

## Snapshot Data Model

```python
@dataclass(slots=True)
class SnapshotEntry:
    """Single widget in a snapshot."""
    role: str
    name: str
    text: str | None = None
    value: float | None = None
    children_count: int = 0

@dataclass(slots=True)
class SnapshotDiff:
    """Diff between two snapshots."""
    added: list[SnapshotEntry]
    removed: list[SnapshotEntry]
    changed: list[tuple[SnapshotEntry, SnapshotEntry]]  # (old, new)
```

## File Map

### New files
- `tests/apps/complex_app.py` — kitchen-sink test app
- `src/qt_ai_dev_tools/snapshot.py` — snapshot save/diff logic
- `tests/unit/test_snapshot.py` — snapshot unit tests
- `tests/e2e/test_complex_app_e2e.py` — e2e tests against kitchen-sink app

### Modified files
- `src/qt_ai_dev_tools/_atspi.py` — add Value, Selection, Table interface wrappers
- `src/qt_ai_dev_tools/pilot.py` — add complex widget helper methods
- `src/qt_ai_dev_tools/cli.py` — add snapshot subcommand group, extend existing commands
- `src/qt_ai_dev_tools/models.py` — add SnapshotEntry, SnapshotDiff
- `tests/unit/test_atspi.py` — replace tautological tests, add interface tests
- `tests/unit/test_vm.py` — replace tautological tests
- `tests/unit/test_pilot.py` — add tests for new pilot methods
- `pyproject.toml` — add PySide6 to dev deps (for host type checking)
- `docs/ROADMAP.md` — update status, document CQ-4 deferral

## Testing Strategy

### Unit tests (host-runnable, mocked AT-SPI)
- AtspiNode Value/Selection/Table interfaces — mock native objects
- Pilot complex widget methods — mock AtspiNode
- Snapshot save/diff logic — pure data manipulation
- Replacement tests for CQ-3 items

### E2E tests (VM, real AT-SPI)
- Kitchen-sink app: exercise each widget type through CLI and pilot
- Snapshot: save, modify app state, diff, verify changes detected
- Complex interactions: fill form across tabs, navigate menus, read table data

## Dependencies

Implementation order matters:
1. **Kitchen-sink test app** (6.7) — needed as test target for everything else
2. **AtspiNode interfaces** (6.1) — foundation for pilot helpers
3. **CQ-3 test replacement** — can be done in parallel with 6.1
4. **Pilot helpers** (6.2) — depends on 6.1
5. **Tree snapshot/diff** (6.5) — independent, can parallel with 6.2
6. **E2E tests** — depends on all above
7. **CQ-4 deferral doc** — trivial, do last
