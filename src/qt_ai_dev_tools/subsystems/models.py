"""Shared data types for Linux subsystem helpers."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ClipboardError:
    """Error from clipboard operations."""

    message: str
    tool_missing: bool = False


@dataclass(slots=True)
class FileDialogInfo:
    """Current state of a file dialog."""

    dialog_type: str
    current_path: str | None = None


@dataclass(slots=True)
class FileDialogResult:
    """Outcome of a file dialog interaction."""

    accepted: bool
    selected_path: str | None = None


@dataclass(slots=True)
class TrayItem:
    """A system tray icon entry."""

    name: str
    bus_name: str
    object_path: str
    protocol: str


@dataclass(slots=True)
class TrayMenuEntry:
    """A single entry in a tray icon's context menu."""

    label: str
    enabled: bool
    index: int


@dataclass(slots=True)
class NotificationAction:
    """An action button on a notification."""

    key: str
    label: str


@dataclass(slots=True)
class Notification:
    """A desktop notification."""

    id: int
    app_name: str
    summary: str
    body: str
    actions: list[NotificationAction] = field(default_factory=list)


@dataclass(slots=True)
class VirtualMicInfo:
    """Info about a virtual microphone PipeWire node."""

    pid: int
    node_name: str


@dataclass(slots=True)
class AudioSource:
    """A PipeWire/PulseAudio audio source."""

    id: int
    name: str
    description: str


@dataclass(slots=True)
class AudioStream:
    """An active audio stream."""

    id: int
    node_name: str
    state: str


@dataclass(slots=True)
class AudioVerification:
    """Result of verifying audio output."""

    is_silent: bool
    max_amplitude: float
    rms_amplitude: float
    duration_seconds: float
