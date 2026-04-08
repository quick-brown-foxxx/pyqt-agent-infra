"""Package version — reads from installed metadata (pyproject.toml is the single source).

During development, __commit__ is "dev". At build time, the custom hatch build
hook (hatch_build.py) replaces it with the actual git short hash.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__: str = version("qt-ai-dev-tools")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"

__commit__: str = "dev"
