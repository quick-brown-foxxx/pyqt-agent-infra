"""Typed bridge to gi.repository.Atspi.

All raw AT-SPI access is confined to this module. The rest of the codebase
works with AtspiNode — fully typed, IDE-friendly, zero type ignores needed.
"""

from __future__ import annotations

import time

import gi  # type: ignore[import-untyped]  # rationale: system GObject introspection has no stubs

gi.require_version("Atspi", "2.0")  # type: ignore[reportUnknownMemberType]  # rationale: gi has no stubs
from gi.repository import Atspi  # type: ignore[import-untyped]  # rationale: system AT-SPI bindings have no stubs  # noqa: E402, I001
from qt_ai_dev_tools.models import Extents  # noqa: E402


class AtspiNode:
    """Typed wrapper around a raw AT-SPI Accessible object.

    Confines all untyped AT-SPI access to this class so the rest of the
    codebase can work with fully typed, IDE-friendly objects.
    """

    __slots__ = ("_native",)

    def __init__(self, native: object) -> None:
        self._native = native

    @property
    def name(self) -> str:
        """Accessible name of the widget."""
        result = self._native.get_name()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
        return result or ""  # type: ignore[no-any-return]  # rationale: AT-SPI get_name() returns untyped str|None

    @property
    def role_name(self) -> str:
        """Role name (e.g. 'push button', 'text', 'label')."""
        return self._native.get_role_name()  # type: ignore[union-attr,no-any-return]  # rationale: AT-SPI Accessible has no stubs

    @property
    def child_count(self) -> int:
        """Number of child widgets."""
        return self._native.get_child_count()  # type: ignore[union-attr,no-any-return]  # rationale: AT-SPI Accessible has no stubs

    def child_at(self, index: int) -> AtspiNode | None:
        """Return child at index, or None if the child is None."""
        child = self._native.get_child_at_index(index)  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
        if child is None:
            return None
        return AtspiNode(child)  # type: ignore[reportUnknownArgumentType]  # rationale: AT-SPI child is untyped

    @property
    def children(self) -> list[AtspiNode]:
        """All non-None children."""
        result: list[AtspiNode] = []
        for i in range(self.child_count):
            node = self.child_at(i)
            if node is not None:
                result.append(node)
        return result

    def get_extents(self) -> Extents:
        """Screen position and size of the widget."""
        ext = self._native.get_extents(Atspi.CoordType.SCREEN)  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
        return Extents(ext.x, ext.y, ext.width, ext.height)  # type: ignore[arg-type]  # rationale: AT-SPI extents fields are untyped

    def get_text(self) -> str:
        """Text content. Falls back to accessible name if no text iface."""
        iface = self._native.get_text_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
        if iface:
            count: int = Atspi.Text.get_character_count(iface)  # type: ignore[reportUnknownMemberType]  # rationale: AT-SPI has no stubs
            return Atspi.Text.get_text(iface, 0, count)  # type: ignore[reportUnknownMemberType,no-any-return]  # rationale: AT-SPI Text.get_text returns untyped str; call via class to bypass Accessible.get_text shadow
        return self.name

    def get_action_names(self) -> list[str]:
        """List available action names on this widget."""
        iface = self._native.get_action_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
        if not iface:
            return []
        n_actions: int = iface.get_n_actions()  # type: ignore[union-attr]  # rationale: AT-SPI action iface has no stubs
        return [iface.get_action_name(i) for i in range(n_actions)]  # type: ignore[union-attr]  # rationale: AT-SPI action iface has no stubs

    def do_action(self, name: str, pause: float = 0.3) -> None:
        """Execute an action by name.

        Args:
            name: Action name (e.g. 'click', 'press').
            pause: Seconds to sleep after action for UI to settle.

        Raises:
            RuntimeError: If the widget has no action interface.
            LookupError: If the named action is not available.
        """
        iface = self._native.get_action_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
        if not iface:
            msg = f"Widget {self!r} has no action interface"
            raise RuntimeError(msg)
        n_actions: int = iface.get_n_actions()  # type: ignore[union-attr]  # rationale: AT-SPI action iface has no stubs
        for i in range(n_actions):  # type: ignore[reportUnknownArgumentType]  # rationale: AT-SPI n_actions is untyped
            action_name: str = iface.get_action_name(i)  # type: ignore[union-attr]  # rationale: AT-SPI action iface has no stubs
            if action_name == name:
                iface.do_action(i)  # type: ignore[union-attr]  # rationale: AT-SPI action iface has no stubs
                time.sleep(pause)
                return
        available = [iface.get_action_name(i) for i in range(n_actions)]  # type: ignore[union-attr,reportUnknownArgumentType]  # rationale: AT-SPI action iface has no stubs
        msg = f"Action {name!r} not found. Available: {available}"
        raise LookupError(msg)

    @property
    def has_action_iface(self) -> bool:
        """Whether the widget has an action interface."""
        return self._native.get_action_iface() is not None  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs

    # ------------------------------------------------------------------
    # Value interface (sliders, spinners, progress bars)
    # ------------------------------------------------------------------

    @property
    def has_value_iface(self) -> bool:
        """Whether the widget has a value interface."""
        return self._native.get_value_iface() is not None  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs

    def get_value(self) -> float | None:
        """Current value, or None if no Value interface."""
        iface = self._native.get_value_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
        if not iface:
            return None
        return iface.get_current_value()  # type: ignore[union-attr,no-any-return]  # rationale: AT-SPI Value iface has no stubs

    def set_value(self, value: float) -> None:
        """Set the current value.

        Raises:
            RuntimeError: If the widget has no value interface.
        """
        iface = self._native.get_value_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
        if not iface:
            msg = f"Widget {self!r} has no value interface"
            raise RuntimeError(msg)
        iface.set_current_value(value)  # type: ignore[union-attr]  # rationale: AT-SPI Value iface has no stubs

    def get_minimum_value(self) -> float | None:
        """Minimum value, or None if no Value interface."""
        iface = self._native.get_value_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
        if not iface:
            return None
        return iface.get_minimum_value()  # type: ignore[union-attr,no-any-return]  # rationale: AT-SPI Value iface has no stubs

    def get_maximum_value(self) -> float | None:
        """Maximum value, or None if no Value interface."""
        iface = self._native.get_value_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
        if not iface:
            return None
        return iface.get_maximum_value()  # type: ignore[union-attr,no-any-return]  # rationale: AT-SPI Value iface has no stubs

    # ------------------------------------------------------------------
    # Selection interface (combo boxes, list widgets, tabs)
    # ------------------------------------------------------------------

    @property
    def has_selection_iface(self) -> bool:
        """Whether the widget has a selection interface."""
        return self._native.get_selection_iface() is not None  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs

    def get_n_selected_children(self) -> int:
        """Number of selected children, or 0 if no Selection interface."""
        iface = self._native.get_selection_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
        if not iface:
            return 0
        return iface.get_n_selected_children()  # type: ignore[union-attr,no-any-return]  # rationale: AT-SPI Selection iface has no stubs

    def get_selected_child(self, index: int = 0) -> AtspiNode | None:
        """Return the selected child at the given selection index."""
        iface = self._native.get_selection_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
        if not iface:
            return None
        child = iface.get_selected_child(index)  # type: ignore[union-attr]  # rationale: AT-SPI Selection iface has no stubs
        if child is None:
            return None
        return AtspiNode(child)  # type: ignore[reportUnknownArgumentType]  # rationale: AT-SPI selected child is untyped

    def select_child(self, index: int) -> bool:
        """Select a child by index. Returns False if no Selection interface."""
        iface = self._native.get_selection_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
        if not iface:
            return False
        return iface.select_child(index)  # type: ignore[union-attr,no-any-return]  # rationale: AT-SPI Selection iface has no stubs

    def deselect_child(self, index: int) -> bool:
        """Deselect a child by index. Returns False if no Selection interface."""
        iface = self._native.get_selection_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
        if not iface:
            return False
        return iface.deselect_child(index)  # type: ignore[union-attr,no-any-return]  # rationale: AT-SPI Selection iface has no stubs

    def is_child_selected(self, index: int) -> bool:
        """Check if a child is selected. Returns False if no Selection interface."""
        iface = self._native.get_selection_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
        if not iface:
            return False
        return iface.is_child_selected(index)  # type: ignore[union-attr,no-any-return]  # rationale: AT-SPI Selection iface has no stubs

    # ------------------------------------------------------------------
    # Table interface (tables, trees)
    # ------------------------------------------------------------------

    @property
    def has_table_iface(self) -> bool:
        """Whether the widget has a table interface."""
        return self._native.get_table_iface() is not None  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs

    def get_n_rows(self) -> int:
        """Number of rows, or 0 if no Table interface."""
        iface = self._native.get_table_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
        if not iface:
            return 0
        return iface.get_n_rows()  # type: ignore[union-attr,no-any-return]  # rationale: AT-SPI Table iface has no stubs

    def get_n_columns(self) -> int:
        """Number of columns, or 0 if no Table interface."""
        iface = self._native.get_table_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
        if not iface:
            return 0
        return iface.get_n_columns()  # type: ignore[union-attr,no-any-return]  # rationale: AT-SPI Table iface has no stubs

    def get_cell_at(self, row: int, col: int) -> AtspiNode | None:
        """Return the accessible at the given row and column."""
        iface = self._native.get_table_iface()  # type: ignore[union-attr]  # rationale: AT-SPI Accessible has no stubs
        if not iface:
            return None
        cell = iface.get_accessible_at(row, col)  # type: ignore[union-attr]  # rationale: AT-SPI Table iface has no stubs
        if cell is None:
            return None
        return AtspiNode(cell)  # type: ignore[reportUnknownArgumentType]  # rationale: AT-SPI table cell is untyped

    @staticmethod
    def desktop(screen: int = 0) -> AtspiNode:
        """Get the AT-SPI desktop node."""
        return AtspiNode(Atspi.get_desktop(screen))  # type: ignore[reportUnknownMemberType,reportUnknownArgumentType]  # rationale: AT-SPI has no stubs

    def __repr__(self) -> str:
        return f'AtspiNode([{self.role_name}] "{self.name}")'
