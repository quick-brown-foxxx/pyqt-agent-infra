# Test cases: version, update check, --version flag

Features added in this session. No existing tests.

## 1. `_update_check.py` — unit tests

### `_parse_version`

| Case | Input | Expected | Priority |
|------|-------|----------|----------|
| Simple three-part | `"1.2.3"` | `(1, 2, 3)` | critical |
| Pre-release suffix | `"1.2.3rc1"` | `(1, 2)` | critical |
| Two-part | `"1.2"` | `(1, 2)` | medium |
| Single segment | `"1"` | `(1,)` | medium |
| Empty string | `""` | `()` | medium |

### `check_for_update` (with monkeypatched network/cache)

| Case | Setup | Expected | Priority |
|------|-------|----------|----------|
| Newer version available | Stub PyPI returning higher version | Returns notice string containing new version | critical |
| Up-to-date | Stub PyPI returning same version | Returns `None` | critical |
| Current is newer (dev) | Stub PyPI returning lower version | Returns `None` | medium |
| Network failure | Stub fetch raising `URLError` | Returns `None` (no crash) | critical |
| Cache hit (fresh) | Write fresh cache file, no network stub | Returns cached result without network call | critical |
| Cache expired | Write old cache file, stub PyPI | Fetches from network, returns result | critical |
| Corrupted cache file | Write garbage to cache path | Returns `None` or fetches fresh (no crash) | medium |

### `_read_cache` / `_write_cache`

| Case | Setup | Expected | Priority |
|------|-------|----------|----------|
| Round-trip | Write then read | Same data back | critical |
| Missing file | No file at path | Returns `None` | critical |
| Expired entry | Cache older than 24h | Returns `None` | critical |
| Corrupted JSON | Invalid JSON in file | Returns `None` | medium |

## 2. `__version__.py` — unit tests

| Case | Expected | Priority |
|------|----------|----------|
| `__version__` is non-empty string matching `\d+\.\d+\.\d+` pattern (or `0.0.0-dev`) | Validates importlib.metadata integration | critical |
| `__commit__` is a string (`"dev"` in dev environment) | Type check | critical |

## 3. CLI `--version` flag — integration test (subprocess)

| Case | Command | Expected | Priority |
|------|---------|----------|----------|
| Prints version and exits 0 | `qt-ai-dev-tools --version` | Exit 0, stdout matches `\d+\.\d+\.\d+ \(` | critical |
| Short flag works | `qt-ai-dev-tools -V` | Same output as `--version` | medium |

## 4. `hatch_build.py` — unit test

| Case | Expected | Priority |
|------|----------|----------|
| `_git_short_hash()` returns non-empty string | Works in git repo | medium |
| `_git_short_hash()` returns `"unknown"` when git unavailable | Fallback works | medium |

## Decisions

- **Skip**: hatch_build.py `CustomBuildHook.initialize()` — requires hatchling runtime context, tested indirectly by `uv build`
- **Skip**: CLI update notice printing in `main_callback` — tested indirectly via `check_for_update` unit tests + manual verification
- **Real over mocked**: Use `tmp_path` for cache file tests, `monkeypatch` for env vars and module-level constants. Monkeypatch `_fetch_latest_version` in integration-level tests rather than patching urllib.
