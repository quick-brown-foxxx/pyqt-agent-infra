"""Custom hatch build hook — stamps git commit hash into __version__.py."""

from __future__ import annotations

import atexit
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

if TYPE_CHECKING:
    from typing import Final

_SENTINEL: Final = '__commit__: str = "dev"'


def _git_short_hash() -> str:
    """Return the short git commit hash, or 'unknown' if git is unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return "unknown"


class CustomBuildHook(BuildHookInterface):
    """Replace __commit__ sentinel in __version__.py with the real git hash."""

    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict[str, object]) -> None:  # type: ignore[override]  # rationale: hatchling base uses Any in signature
        """Stamp git hash into a copy of __version__.py and force-include it."""
        version_src = Path(self.root) / "src" / "qt_ai_dev_tools" / "__version__.py"
        original = version_src.read_text(encoding="utf-8")

        if _SENTINEL not in original:
            return

        commit_hash = _git_short_hash()
        stamped = original.replace(_SENTINEL, f'__commit__: str = "{commit_hash}"')

        # Write stamped file to a temp directory; force-include it in the build.
        # atexit ensures cleanup even if hatchling doesn't call finalize().
        tmp_dir = Path(tempfile.mkdtemp(prefix="hatch-commit-"))
        atexit.register(shutil.rmtree, str(tmp_dir), True)
        stamped_path = tmp_dir / "__version__.py"
        stamped_path.write_text(stamped, encoding="utf-8")

        force_include = build_data.get("force_include")
        if not isinstance(force_include, dict):
            force_include = {}
            build_data["force_include"] = force_include
        force_include[str(stamped_path)] = "qt_ai_dev_tools/__version__.py"
