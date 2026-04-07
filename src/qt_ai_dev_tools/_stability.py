"""Command stability classification.

Every CLI command is classified as 'beta' or 'alpha'.
Alpha commands print a one-line warning on stderr before executing.
The main CLI help shows the tool's overall stability level.
"""

from __future__ import annotations

import enum
import sys
from typing import Final


class Stability(enum.Enum):
    """Stability level for a CLI command."""

    ALPHA = "alpha"
    BETA = "beta"


# Commands that are alpha. Everything else is beta.
_ALPHA_COMMANDS: Final[frozenset[str]] = frozenset(
    {
        "clipboard read",
        "clipboard write",
        "file-dialog detect",
        "file-dialog fill",
        "file-dialog accept",
        "file-dialog cancel",
        "tray list",
        "tray click",
        "tray menu",
        "tray select",
        "notify listen",
        "notify dismiss",
        "notify action",
        "audio virtual-mic start",
        "audio virtual-mic stop",
        "audio virtual-mic play",
        "audio record",
        "audio verify",
        "audio sources",
        "audio status",
    }
)


def get_stability(command: str) -> Stability:
    """Get stability level for a command."""
    if command in _ALPHA_COMMANDS:
        return Stability.ALPHA
    return Stability.BETA


def warn_if_alpha(command: str) -> None:
    """Print a one-line warning to stderr if the command is alpha."""
    if get_stability(command) == Stability.ALPHA:
        print(
            f"\u26a0 '{command}' is alpha \u2014 API may change, report issues.",
            file=sys.stderr,
        )
