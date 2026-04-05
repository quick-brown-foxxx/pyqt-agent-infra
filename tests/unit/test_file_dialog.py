"""Tests for file dialog subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    pass

pytestmark = pytest.mark.unit


@dataclass
class MockNode:
    """Minimal mock for AtspiNode."""

    name: str
    role_name: str
    _text: str = ""

    def get_text(self) -> str:
        return self._text


class MockPilot:
    """Minimal mock for QtPilot that returns pre-configured widgets."""

    def __init__(self, widgets: dict[str, list[MockNode]] | None = None) -> None:
        self._widgets: dict[str, list[MockNode]] = widgets or {}
        self.clicked: list[MockNode] = []
        self.focused: list[MockNode] = []
        self.typed: list[str] = []
        self.keys_pressed: list[str] = []

    def find(
        self,
        role: str | None = None,
        name: str | None = None,
        root: object | None = None,
    ) -> list[MockNode]:
        """Return matching mock nodes based on role and name."""
        results: list[MockNode] = []
        for nodes in self._widgets.values():
            for node in nodes:
                match = True
                if role and node.role_name != role:
                    match = False
                if name and name not in node.name:
                    match = False
                if match:
                    results.append(node)
        return results

    def click(self, widget: object) -> None:
        if isinstance(widget, MockNode):
            self.clicked.append(widget)

    def focus(self, widget: object) -> None:
        if isinstance(widget, MockNode):
            self.focused.append(widget)

    def type_text(self, text: str) -> None:
        self.typed.append(text)

    def press_key(self, key: str) -> None:
        self.keys_pressed.append(key)

    def get_name(self, widget: object) -> str:
        if isinstance(widget, MockNode):
            return widget.name
        return ""

    def get_text(self, widget: object) -> str:
        if isinstance(widget, MockNode):
            return widget._text
        return ""


class TestDetect:
    def test_detect_file_chooser_role(self) -> None:
        """detect() should find a file dialog with 'file chooser' role."""
        from qt_ai_dev_tools.subsystems.file_dialog import detect

        chooser = MockNode(name="Open File", role_name="file chooser")
        pilot = MockPilot({"choosers": [chooser]})

        # We need to cast to satisfy the type checker in tests
        result = detect(pilot)  # type: ignore[reportArgumentType]  # rationale: MockPilot for testing
        assert result.dialog_type == "file chooser"

    def test_detect_dialog_with_file_keyword(self) -> None:
        """detect() should find a dialog with file-related name."""
        from qt_ai_dev_tools.subsystems.file_dialog import detect

        dialog = MockNode(name="Save File As", role_name="dialog")
        pilot = MockPilot({"dialogs": [dialog]})

        result = detect(pilot)  # type: ignore[reportArgumentType]  # rationale: MockPilot for testing
        assert result.dialog_type == "dialog"

    def test_detect_raises_when_no_dialog(self) -> None:
        """detect() should raise LookupError when no file dialog exists."""
        from qt_ai_dev_tools.subsystems.file_dialog import detect

        pilot = MockPilot()

        with pytest.raises(LookupError, match="No file dialog found"):
            detect(pilot)  # type: ignore[reportArgumentType]  # rationale: MockPilot for testing


class TestFill:
    def test_fill_types_path_into_filename_field(self) -> None:
        """fill() should find the filename field and type the path."""
        from qt_ai_dev_tools.subsystems.file_dialog import fill

        dialog = MockNode(name="Open File", role_name="file chooser")
        field = MockNode(name="fileNameEdit", role_name="text")
        pilot = MockPilot({"dialogs": [dialog], "fields": [field]})

        fill(pilot, "/tmp/test.txt")  # type: ignore[reportArgumentType]  # rationale: MockPilot for testing

        assert len(pilot.focused) == 1
        assert pilot.focused[0] is field
        assert "ctrl+a" in pilot.keys_pressed
        assert "Delete" in pilot.keys_pressed
        assert "/tmp/test.txt" in pilot.typed

    def test_fill_raises_when_no_dialog(self) -> None:
        """fill() should raise LookupError when no file dialog is found."""
        from qt_ai_dev_tools.subsystems.file_dialog import fill

        pilot = MockPilot()

        with pytest.raises(LookupError, match="No file dialog found"):
            fill(pilot, "/tmp/test.txt")  # type: ignore[reportArgumentType]  # rationale: MockPilot for testing

    def test_fill_raises_when_no_field(self) -> None:
        """fill() should raise LookupError when dialog exists but no text field."""
        from qt_ai_dev_tools.subsystems.file_dialog import fill

        dialog = MockNode(name="Open File", role_name="file chooser")
        pilot = MockPilot({"dialogs": [dialog]})

        with pytest.raises(LookupError, match="No filename text field"):
            fill(pilot, "/tmp/test.txt")  # type: ignore[reportArgumentType]  # rationale: MockPilot for testing


class TestAccept:
    def test_accept_presses_return(self) -> None:
        """accept() should press Return to confirm the dialog."""
        from qt_ai_dev_tools.subsystems.file_dialog import accept

        pilot = MockPilot()

        result = accept(pilot)  # type: ignore[reportArgumentType]  # rationale: MockPilot for testing

        assert result.accepted is True
        assert "Return" in pilot.keys_pressed


class TestCancel:
    def test_cancel_presses_escape(self) -> None:
        """cancel() should press Escape to dismiss the dialog."""
        from qt_ai_dev_tools.subsystems.file_dialog import cancel

        pilot = MockPilot()

        cancel(pilot)  # type: ignore[reportArgumentType]  # rationale: MockPilot for testing

        assert "Escape" in pilot.keys_pressed
