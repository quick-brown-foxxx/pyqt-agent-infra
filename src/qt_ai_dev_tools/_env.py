"""Centralized environment variable registry.

All env vars used by qt-ai-dev-tools are defined here as ``EnvVar`` instances.
Read them via ``get_bool`` / ``get_str`` — never use ``os.environ`` directly
in business logic.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

_TRUTHY: frozenset[str] = frozenset({"1", "true", "yes"})


@dataclass(frozen=True, slots=True)
class EnvVar:
    """A registered environment variable with name, description, and optional default."""

    name: str
    description: str
    default: str = ""


def get_bool(var: EnvVar) -> bool:
    """Read an env var as a boolean.

    Truthy values (case-insensitive): ``"1"``, ``"true"``, ``"yes"``.
    Everything else — including unset and empty — is ``False``.
    """
    return os.environ.get(var.name, "").lower() in _TRUTHY


def get_str(var: EnvVar, *, default: str | None = None) -> str:
    """Read an env var as a string.

    Returns the env value if set, otherwise *default* (falls back to
    ``var.default`` when *default* is ``None``).
    """
    fallback = var.default if default is None else default
    return os.environ.get(var.name, fallback)


# ── Registered variables ─────────────────────────────────────────────

VM = EnvVar(
    name="QT_AI_DEV_TOOLS_VM",
    description="Marks code running inside the Vagrant VM",
)

BRIDGE = EnvVar(
    name="QT_AI_DEV_TOOLS_BRIDGE",
    description="Enables the bridge server for runtime code execution",
)

ALLOW_VERSION_MISMATCH = EnvVar(
    name="QT_AI_DEV_TOOLS_ALLOW_VERSION_MISMATCH",
    description="Downgrades version mismatch errors to warnings",
)

DISPLAY = EnvVar(
    name="DISPLAY",
    description="X11 display identifier",
)
