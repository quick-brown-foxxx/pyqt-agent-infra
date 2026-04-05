"""Tests for system tray subsystem."""

from __future__ import annotations

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

_MOCK_BUSCTL_OUTPUT = 'as 2 ":1.45/StatusNotifierItem" "org.kde.StatusNotifierHost-1234/StatusNotifierItem"'


def _make_run_tool_side_effect(
    *,
    list_output: str = _MOCK_BUSCTL_OUTPUT,
    id_value: str | None = None,
    menu_prop: str | None = None,
    menu_output: str = "",
) -> object:
    """Build a side_effect callable for run_tool mocking.

    Dispatches based on the busctl subcommand in the args list.
    """

    def _side_effect(args: list[str], **_kwargs: object) -> str:
        if "get-property" in args:
            # Distinguish watcher queries from SNI property queries
            if "RegisteredStatusNotifierItems" in args:
                return list_output
            if "Id" in args:
                if id_value is not None:
                    return f's "{id_value}"'
                msg = "Property not found"
                raise RuntimeError(msg)
            if "Menu" in args:
                if menu_prop is not None:
                    return f'o "{menu_prop}"'
                msg = "Property not found"
                raise RuntimeError(msg)
        if "call" in args:
            if "GetLayout" in args:
                return menu_output
            if "Event" in args:
                return ""
            if "Activate" in args:
                return ""
        # xdotool commands
        if args and args[0] == "xdotool":
            if "search" in args:
                return "12345678\n"
            if "getwindowgeometry" in args:
                return "Window 12345678\n  Position: 1872,0 (screen: 0)\n  Geometry: 48x24"
            if "mousemove" in args:
                return ""
            if "click" in args:
                return ""
        # xwininfo
        if args and args[0] == "xwininfo":
            return (
                '  0x3400003 (has no name): ("tray_app.py" "tray_app.py")  24x24+0+0  +1872+0\n'
                '  0x3400004 (has no name): ("other_app" "other_app")  24x24+24+0  +1896+0\n'
            )
        return ""

    return _side_effect


class TestParseRegisteredItems:
    def test_parse_two_items(self) -> None:
        """_parse_registered_items should parse bus names and object paths."""
        from qt_ai_dev_tools.subsystems.tray import _parse_registered_items

        with patch("qt_ai_dev_tools.subsystems.tray._query_sni_property", return_value=None):
            items = _parse_registered_items(_MOCK_BUSCTL_OUTPUT)

        assert len(items) == 2

        assert items[0].bus_name == ":1.45"
        assert items[0].object_path == "/StatusNotifierItem"
        assert items[0].protocol == "SNI"

        assert items[1].bus_name == "org.kde.StatusNotifierHost-1234"
        assert items[1].object_path == "/StatusNotifierItem"
        assert items[1].name == "StatusNotifierHost-1234"

    def test_parse_empty_output(self) -> None:
        """_parse_registered_items should return empty list for empty output."""
        from qt_ai_dev_tools.subsystems.tray import _parse_registered_items

        items = _parse_registered_items("as 0")
        assert items == []

    def test_connection_id_resolves_via_sni_id(self) -> None:
        """When bus_name is a connection ID, query the Id property for the real name."""
        from qt_ai_dev_tools.subsystems.tray import _parse_registered_items

        output = 'as 1 ":1.340/StatusNotifierItem"'
        with patch("qt_ai_dev_tools.subsystems.tray._query_sni_property", return_value="tray_app.py") as mock_query:
            items = _parse_registered_items(output)

        assert len(items) == 1
        assert items[0].name == "tray_app.py"
        mock_query.assert_called_once_with(":1.340", "/StatusNotifierItem", "Id")

    def test_connection_id_fallback_on_query_failure(self) -> None:
        """When Id property query fails, keep the numeric name from connection ID."""
        from qt_ai_dev_tools.subsystems.tray import _parse_registered_items

        output = 'as 1 ":1.340/StatusNotifierItem"'
        with patch("qt_ai_dev_tools.subsystems.tray._query_sni_property", return_value=None):
            items = _parse_registered_items(output)

        assert len(items) == 1
        assert items[0].name == "340"


class TestQuerySniProperty:
    def test_query_string_property(self) -> None:
        """_query_sni_property should parse string property output."""
        from qt_ai_dev_tools.subsystems.tray import _query_sni_property

        with patch("qt_ai_dev_tools.subsystems.tray.run_tool", return_value='s "tray_app.py"') as mock_run:
            result = _query_sni_property(":1.340", "/StatusNotifierItem", "Id")

        assert result == "tray_app.py"
        args = mock_run.call_args[0][0]
        assert "--" in args
        assert args.index("--") < args.index(":1.340")

    def test_query_object_path_property(self) -> None:
        """_query_sni_property should parse object path property output."""
        from qt_ai_dev_tools.subsystems.tray import _query_sni_property

        with patch("qt_ai_dev_tools.subsystems.tray.run_tool", return_value='o "/MenuBar"'):
            result = _query_sni_property(":1.340", "/StatusNotifierItem", "Menu")

        assert result == "/MenuBar"

    def test_query_returns_none_on_failure(self) -> None:
        """_query_sni_property should return None when busctl fails."""
        from qt_ai_dev_tools.subsystems.tray import _query_sni_property

        with patch("qt_ai_dev_tools.subsystems.tray.run_tool", side_effect=RuntimeError("fail")):
            result = _query_sni_property(":1.340", "/StatusNotifierItem", "Id")

        assert result is None


class TestResolveMenuPath:
    def test_uses_menu_property(self) -> None:
        """_resolve_menu_path should use the Menu property when available."""
        from qt_ai_dev_tools.subsystems.models import TrayItem
        from qt_ai_dev_tools.subsystems.tray import _resolve_menu_path

        item = TrayItem(name="app", bus_name=":1.340", object_path="/StatusNotifierItem", protocol="SNI")
        with patch("qt_ai_dev_tools.subsystems.tray._query_sni_property", return_value="/MenuBar"):
            result = _resolve_menu_path(item)

        assert result == "/MenuBar"

    def test_falls_back_to_object_path_plus_menu(self) -> None:
        """_resolve_menu_path should fall back to object_path + '/Menu'."""
        from qt_ai_dev_tools.subsystems.models import TrayItem
        from qt_ai_dev_tools.subsystems.tray import _resolve_menu_path

        item = TrayItem(name="app", bus_name=":1.340", object_path="/StatusNotifierItem", protocol="SNI")
        with patch("qt_ai_dev_tools.subsystems.tray._query_sni_property", return_value=None):
            result = _resolve_menu_path(item)

        assert result == "/StatusNotifierItem/Menu"


class TestListItems:
    def test_list_items_calls_busctl(self) -> None:
        """list_items() should call busctl with correct arguments."""
        from qt_ai_dev_tools.subsystems.tray import list_items

        side_effect = _make_run_tool_side_effect(list_output=_MOCK_BUSCTL_OUTPUT)
        with (
            patch("qt_ai_dev_tools.subsystems.tray.check_tool") as mock_check,
            patch("qt_ai_dev_tools.subsystems.tray.run_tool", side_effect=side_effect) as mock_run,
        ):
            mock_check.return_value = "/usr/bin/busctl"
            items = list_items()

            mock_check.assert_called_once_with("busctl")
            assert mock_run.called
            first_call_args = mock_run.call_args_list[0][0][0]
            assert "busctl" in first_call_args
            assert "--user" in first_call_args
            assert "get-property" in first_call_args
            assert len(items) == 2


class TestClick:
    def test_click_left_calls_activate(self) -> None:
        """click(button='left') should call Activate on the matching tray item."""
        from qt_ai_dev_tools.subsystems.tray import click

        side_effect = _make_run_tool_side_effect(list_output=_MOCK_BUSCTL_OUTPUT)
        with (
            patch("qt_ai_dev_tools.subsystems.tray.check_tool"),
            patch("qt_ai_dev_tools.subsystems.tray.run_tool", side_effect=side_effect) as mock_run,
        ):
            click("StatusNotifierHost-1234", button="left")

            # Find the Activate call
            activate_calls = [c for c in mock_run.call_args_list if "Activate" in c[0][0]]
            assert len(activate_calls) == 1
            activate_args = activate_calls[0][0][0]
            assert "--" in activate_args
            assert "org.kde.StatusNotifierHost-1234" in activate_args

    def test_click_default_is_left(self) -> None:
        """click() with no button arg should default to left (Activate)."""
        from qt_ai_dev_tools.subsystems.tray import click

        side_effect = _make_run_tool_side_effect(list_output=_MOCK_BUSCTL_OUTPUT)
        with (
            patch("qt_ai_dev_tools.subsystems.tray.check_tool"),
            patch("qt_ai_dev_tools.subsystems.tray.run_tool", side_effect=side_effect) as mock_run,
        ):
            click("StatusNotifierHost-1234")

            activate_calls = [c for c in mock_run.call_args_list if "Activate" in c[0][0]]
            assert len(activate_calls) == 1

    def test_click_right_uses_xdotool(self) -> None:
        """click(button='right') should use xdotool to right-click the icon."""
        from qt_ai_dev_tools.subsystems.tray import click

        side_effect = _make_run_tool_side_effect()
        with (
            patch("qt_ai_dev_tools.subsystems.tray.check_tool"),
            patch("qt_ai_dev_tools.subsystems.tray.run_tool", side_effect=side_effect) as mock_run,
        ):
            click("tray_app", button="right")

            # Should have xdotool search, getwindowgeometry, xwininfo, mousemove, click
            all_calls = [c[0][0] for c in mock_run.call_args_list]

            # Find mousemove call
            mousemove_calls = [a for a in all_calls if "mousemove" in a]
            assert len(mousemove_calls) == 1
            assert "--screen" in mousemove_calls[0]

            # Find xdotool click call (button 3)
            xdotool_click_calls = [a for a in all_calls if a[0] == "xdotool" and "click" in a]
            assert len(xdotool_click_calls) == 1
            assert "3" in xdotool_click_calls[0]

    def test_click_raises_for_invalid_button(self) -> None:
        """click() should raise ValueError for invalid button."""
        from qt_ai_dev_tools.subsystems.tray import click

        with pytest.raises(ValueError, match="Invalid button"):
            click("app", button="middle")

    def test_click_raises_for_unknown_app(self) -> None:
        """click() should raise LookupError when no matching item exists."""
        from qt_ai_dev_tools.subsystems.tray import click

        with (
            patch("qt_ai_dev_tools.subsystems.tray.check_tool"),
            patch("qt_ai_dev_tools.subsystems.tray.run_tool", return_value="as 0"),
            pytest.raises(LookupError, match="No tray item matching"),
        ):
            click("nonexistent-app")


class TestMenu:
    def test_menu_uses_resolved_path(self) -> None:
        """menu() should resolve the menu path via the Menu property."""
        from qt_ai_dev_tools.subsystems.tray import menu

        menu_output = (
            'u(ia{sv}av) 1 0 1 "children-display" s "submenu" 2 '
            '(ia{sv}av) 4 2 "enabled" b true "label" s "Show" 0 '
            '(ia{sv}av) 1 2 "enabled" b true "label" s "Quit" 0'
        )
        side_effect = _make_run_tool_side_effect(
            list_output=_MOCK_BUSCTL_OUTPUT,
            menu_prop="/MenuBar",
            menu_output=menu_output,
        )
        with (
            patch("qt_ai_dev_tools.subsystems.tray.check_tool"),
            patch("qt_ai_dev_tools.subsystems.tray.run_tool", side_effect=side_effect) as mock_run,
        ):
            entries = menu("StatusNotifierHost-1234")

        assert len(entries) == 2
        # Verify the GetLayout call used /MenuBar, not /StatusNotifierItem/Menu
        get_layout_calls = [c for c in mock_run.call_args_list if "GetLayout" in c[0][0]]
        assert len(get_layout_calls) == 1
        gl_args = get_layout_calls[0][0][0]
        assert "/MenuBar" in gl_args
        assert "--" in gl_args

    def test_menu_busctl_has_double_dash(self) -> None:
        """menu() busctl call commands should include '--' before positional args."""
        from qt_ai_dev_tools.subsystems.tray import menu

        menu_output = '(ia{sv}av) 4 2 "enabled" b true "label" s "Show" 0'
        side_effect = _make_run_tool_side_effect(
            list_output=_MOCK_BUSCTL_OUTPUT,
            menu_output=menu_output,
        )
        with (
            patch("qt_ai_dev_tools.subsystems.tray.check_tool"),
            patch("qt_ai_dev_tools.subsystems.tray.run_tool", side_effect=side_effect) as mock_run,
        ):
            menu("StatusNotifierHost-1234")

        # All 'call' invocations should have '--'
        call_invocations = [c for c in mock_run.call_args_list if "call" in c[0][0]]
        for c in call_invocations:
            args = c[0][0]
            assert "--" in args, f"Missing '--' in busctl call: {args}"


class TestParseMenuOutput:
    def test_parse_menu_labels_and_dbus_ids(self) -> None:
        """_parse_menu_output should extract labels and D-Bus IDs."""
        from qt_ai_dev_tools.subsystems.tray import _parse_menu_output

        # Realistic busctl GetLayout output
        output = (
            'u(ia{sv}av) 1 0 1 "children-display" s "submenu" 3 '
            '(ia{sv}av) 4 3 "enabled" b true "label" s "Show" "visible" b true 0 '
            '(ia{sv}av) 3 3 "enabled" b true "label" s "Settings" "visible" b true 0 '
            '(ia{sv}av) 1 3 "enabled" b true "label" s "Quit" "visible" b true 0'
        )
        entries = _parse_menu_output(output)
        assert len(entries) == 3
        assert entries[0].label == "Show"
        assert entries[0].dbus_id == 4
        assert entries[0].enabled is True
        assert entries[1].label == "Settings"
        assert entries[1].dbus_id == 3
        assert entries[2].label == "Quit"
        assert entries[2].dbus_id == 1

    def test_parse_menu_empty(self) -> None:
        """_parse_menu_output should return empty list for no labels."""
        from qt_ai_dev_tools.subsystems.tray import _parse_menu_output

        entries = _parse_menu_output("")
        assert entries == []

    def test_parse_menu_disabled_item(self) -> None:
        """_parse_menu_output should detect disabled entries."""
        from qt_ai_dev_tools.subsystems.tray import _parse_menu_output

        output = '(ia{sv}av) 5 2 "label" s "Disabled Item" "enabled" b false 0'
        entries = _parse_menu_output(output)
        assert len(entries) == 1
        assert entries[0].enabled is False
        assert entries[0].dbus_id == 5


class TestFindStalonetrayWid:
    def test_finds_window(self) -> None:
        """_find_stalonetray_wid should return the first window ID."""
        from qt_ai_dev_tools.subsystems.tray import _find_stalonetray_wid

        with (
            patch("qt_ai_dev_tools.subsystems.tray.check_tool"),
            patch("qt_ai_dev_tools.subsystems.tray.run_tool", return_value="12345678\n87654321\n"),
        ):
            wid = _find_stalonetray_wid()

        assert wid == "12345678"

    def test_raises_when_not_running(self) -> None:
        """_find_stalonetray_wid should raise when stalonetray is not found."""
        from qt_ai_dev_tools.subsystems.tray import _find_stalonetray_wid

        with (
            patch("qt_ai_dev_tools.subsystems.tray.check_tool"),
            patch("qt_ai_dev_tools.subsystems.tray.run_tool", return_value=""),
            pytest.raises(RuntimeError, match="stalonetray window not found"),
        ):
            _find_stalonetray_wid()


class TestFindIconCenter:
    def test_finds_icon_by_absolute_coords(self) -> None:
        """_find_icon_center should parse xwininfo and return absolute center."""
        from qt_ai_dev_tools.subsystems.tray import _find_icon_center

        xwininfo_output = (
            "  Root window id: 0x123\n"
            "  Parent window id: 0x456\n"
            '     0x3400003 (has no name): ("tray_app.py" "tray_app.py")  24x24+0+0  +1872+0\n'
            '     0x3400004 (has no name): ("other_app" "other_app")  24x24+24+0  +1896+0\n'
        )

        def _side_effect(args: list[str], **_kwargs: object) -> str:
            if args[0] == "xdotool" and "getwindowgeometry" in args:
                return "Window 12345678\n  Position: 1872,0 (screen: 0)\n  Geometry: 48x24"
            if args[0] == "xwininfo":
                return xwininfo_output
            return ""

        with (
            patch("qt_ai_dev_tools.subsystems.tray.check_tool"),
            patch("qt_ai_dev_tools.subsystems.tray.run_tool", side_effect=_side_effect),
        ):
            cx, cy = _find_icon_center("12345678", "tray_app")

        # Absolute: +1872+0, icon 24x24, center = 1872+12, 0+12
        assert cx == 1884
        assert cy == 12

    def test_raises_when_icon_not_found(self) -> None:
        """_find_icon_center should raise LookupError when no match."""
        from qt_ai_dev_tools.subsystems.tray import _find_icon_center

        def _side_effect(args: list[str], **_kwargs: object) -> str:
            if args[0] == "xdotool" and "getwindowgeometry" in args:
                return "Window 12345678\n  Position: 1872,0 (screen: 0)\n  Geometry: 48x24"
            if args[0] == "xwininfo":
                return "  Root window id: 0x123\n  No children.\n"
            return ""

        with (
            patch("qt_ai_dev_tools.subsystems.tray.check_tool"),
            patch("qt_ai_dev_tools.subsystems.tray.run_tool", side_effect=_side_effect),
            pytest.raises(LookupError, match="Tray icon for 'nonexistent' not found"),
        ):
            _find_icon_center("12345678", "nonexistent")


class TestSelect:
    def test_select_triggers_dbus_event(self) -> None:
        """select() should find menu entry by label and trigger D-Bus Event."""
        from qt_ai_dev_tools.subsystems import tray as tray_mod
        from qt_ai_dev_tools.subsystems.models import TrayItem, TrayMenuEntry

        mock_item = TrayItem(name="tray_app.py", bus_name=":1.100", object_path="/StatusNotifierItem", protocol="SNI")
        mock_entries = [
            TrayMenuEntry(label="Show", enabled=True, index=0, dbus_id=4),
            TrayMenuEntry(label="Settings", enabled=True, index=1, dbus_id=3),
            TrayMenuEntry(label="Quit", enabled=True, index=2, dbus_id=1),
        ]

        with (
            patch.object(tray_mod, "_find_item", return_value=mock_item),
            patch.object(tray_mod, "menu", return_value=mock_entries),
            patch.object(tray_mod, "_resolve_menu_path", return_value="/MenuBar"),
            patch.object(tray_mod, "check_tool"),
            patch.object(tray_mod, "run_tool", return_value="") as mock_run,
        ):
            tray_mod.select("tray_app", "Settings")

            # Verify the Event call uses the correct D-Bus ID (3 for Settings)
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert "Event" in call_args
            assert "3" in call_args  # D-Bus ID for Settings

    def test_select_raises_when_menu_item_not_found(self) -> None:
        """select() should raise LookupError when no matching menu entry exists."""
        from qt_ai_dev_tools.subsystems import tray as tray_mod
        from qt_ai_dev_tools.subsystems.models import TrayItem, TrayMenuEntry

        mock_item = TrayItem(name="tray_app.py", bus_name=":1.100", object_path="/StatusNotifierItem", protocol="SNI")
        mock_entries = [
            TrayMenuEntry(label="Show", enabled=True, index=0, dbus_id=4),
        ]

        with (
            patch.object(tray_mod, "_find_item", return_value=mock_item),
            patch.object(tray_mod, "menu", return_value=mock_entries),
            pytest.raises(LookupError, match="Menu item 'NonExistent' not found"),
        ):
            tray_mod.select("tray_app", "NonExistent")
