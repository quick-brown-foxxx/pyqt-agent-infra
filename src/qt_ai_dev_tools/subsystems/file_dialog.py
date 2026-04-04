"""File dialog automation via AT-SPI (QtPilot)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qt_ai_dev_tools.subsystems.models import FileDialogInfo, FileDialogResult

if TYPE_CHECKING:
    from qt_ai_dev_tools._atspi import AtspiNode
    from qt_ai_dev_tools.pilot import QtPilot


# AT-SPI role names used by QFileDialog widgets
_DIALOG_ROLES = ("file chooser", "dialog")
_TEXT_ROLES = ("text", "combo box")
_BUTTON_ROLE = "push button"

# Buttons that accept the dialog
_ACCEPT_NAMES = ("Open", "Save", "OK", "Choose")

# Common filename input names in QFileDialog
_FILENAME_NAMES = ("fileNameEdit", "file name", "File name:")


def detect(pilot: QtPilot) -> FileDialogInfo:
    """Detect an open file dialog in the application.

    Searches the AT-SPI tree for a QFileDialog by looking for
    'file chooser' role or dialog widgets with file-dialog structure.

    Args:
        pilot: Connected QtPilot instance.

    Returns:
        FileDialogInfo with dialog type and current path.

    Raises:
        LookupError: If no file dialog is found.
    """
    # Try file chooser role first (standard AT-SPI role)
    widgets = pilot.find(role="file chooser")
    if widgets:
        dialog = widgets[0]
        dialog_type = "file chooser"
        # Try to read current path from any text field in the dialog
        current_path = _read_current_path(pilot, dialog)
        return FileDialogInfo(dialog_type=dialog_type, current_path=current_path)

    # Fall back to looking for dialogs with QFileDialog structure
    dialogs = pilot.find(role="dialog")
    for dialog in dialogs:
        name = pilot.get_name(dialog)
        if any(keyword in name.lower() for keyword in ("open", "save", "file", "choose")):
            current_path = _read_current_path(pilot, dialog)
            return FileDialogInfo(dialog_type="dialog", current_path=current_path)

    msg = "No file dialog found in the application"
    raise LookupError(msg)


def _read_current_path(pilot: QtPilot, root: AtspiNode) -> str | None:
    """Try to read the current filename/path from a dialog's text field."""
    for role in _TEXT_ROLES:
        fields = pilot.find(role=role, root=root)
        for field in fields:
            text = pilot.get_text(field)
            if text:
                return text
    return None


def fill(pilot: QtPilot, path: str) -> None:
    """Type a file path into the file dialog's filename field.

    Finds the filename text field in the open dialog, clears it,
    and types the provided path.

    Args:
        pilot: Connected QtPilot instance.
        path: File path to enter.

    Raises:
        LookupError: If no filename text field is found.
    """
    # Find filename text field by common names
    for name in _FILENAME_NAMES:
        results = pilot.find(role="text", name=name)
        if results:
            field = results[0]
            pilot.focus(field)
            pilot.press_key("ctrl+a")
            pilot.press_key("Delete")
            pilot.type_text(path)
            return

    # Fallback: find any text field in a file chooser/dialog
    choosers = pilot.find(role="file chooser")
    if not choosers:
        choosers = pilot.find(role="dialog")

    for chooser in choosers:
        fields = pilot.find(role="text", root=chooser)
        if fields:
            field = fields[0]
            pilot.focus(field)
            pilot.press_key("ctrl+a")
            pilot.press_key("Delete")
            pilot.type_text(path)
            return

    msg = "No filename text field found in file dialog"
    raise LookupError(msg)


def accept(pilot: QtPilot) -> FileDialogResult:
    """Click the accept button (Open/Save/OK) in the file dialog.

    Args:
        pilot: Connected QtPilot instance.

    Returns:
        FileDialogResult indicating acceptance.

    Raises:
        LookupError: If no accept button is found.
    """
    for name in _ACCEPT_NAMES:
        results = pilot.find(role=_BUTTON_ROLE, name=name)
        if results:
            pilot.click(results[0])
            return FileDialogResult(accepted=True)

    msg = f"No accept button found (tried: {', '.join(_ACCEPT_NAMES)})"
    raise LookupError(msg)


def cancel(pilot: QtPilot) -> None:
    """Click the Cancel button in the file dialog.

    Args:
        pilot: Connected QtPilot instance.

    Raises:
        LookupError: If no Cancel button is found.
    """
    results = pilot.find(role=_BUTTON_ROLE, name="Cancel")
    if not results:
        msg = "No Cancel button found in file dialog"
        raise LookupError(msg)
    pilot.click(results[0])
