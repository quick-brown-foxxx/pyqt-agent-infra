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

    def _side_effect(args: list[str]) -> str:
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
    def test_click_calls_activate(self) -> None:
        """click() should call Activate on the matching tray item."""
        from qt_ai_dev_tools.subsystems.tray import click

        side_effect = _make_run_tool_side_effect(list_output=_MOCK_BUSCTL_OUTPUT)
        with (
            patch("qt_ai_dev_tools.subsystems.tray.check_tool"),
            patch("qt_ai_dev_tools.subsystems.tray.run_tool", side_effect=side_effect) as mock_run,
        ):
            click("StatusNotifierHost-1234")

            # Find the Activate call
            activate_calls = [c for c in mock_run.call_args_list if "Activate" in c[0][0]]
            assert len(activate_calls) == 1
            activate_args = activate_calls[0][0][0]
            assert "--" in activate_args
            assert "org.kde.StatusNotifierHost-1234" in activate_args

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

        menu_output = '"label" s "Show"\n"enabled" s "true"\n"label" s "Quit"\n"enabled" s "true"'
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

        menu_output = '"label" s "Show"\n"enabled" s "true"'
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
    def test_parse_menu_labels(self) -> None:
        """_parse_menu_output should extract labeled entries."""
        from qt_ai_dev_tools.subsystems.tray import _parse_menu_output

        output = '"label" s "Show"\n"enabled" s "true"\n"label" s "Quit"\n"enabled" s "true"'
        entries = _parse_menu_output(output)
        assert len(entries) == 2
        assert entries[0].label == "Show"
        assert entries[0].enabled is True
        assert entries[1].label == "Quit"

    def test_parse_menu_empty(self) -> None:
        """_parse_menu_output should return empty list for no labels."""
        from qt_ai_dev_tools.subsystems.tray import _parse_menu_output

        entries = _parse_menu_output("")
        assert entries == []

    def test_parse_menu_disabled_item(self) -> None:
        """_parse_menu_output should detect disabled entries."""
        from qt_ai_dev_tools.subsystems.tray import _parse_menu_output

        output = '"label" s "Disabled Item"\n"enabled" s "false"'
        entries = _parse_menu_output(output)
        assert len(entries) == 1
        assert entries[0].enabled is False


class TestSelect:
    def test_select_calls_event_with_double_dash(self) -> None:
        """select() should include '--' in busctl call and use resolved menu path."""
        from qt_ai_dev_tools.subsystems.tray import select

        menu_output = '"label" s "Settings"\n"enabled" s "true"'
        side_effect = _make_run_tool_side_effect(
            list_output=_MOCK_BUSCTL_OUTPUT,
            menu_prop="/MenuBar",
            menu_output=menu_output,
        )
        with (
            patch("qt_ai_dev_tools.subsystems.tray.check_tool"),
            patch("qt_ai_dev_tools.subsystems.tray.run_tool", side_effect=side_effect) as mock_run,
        ):
            select("StatusNotifierHost-1234", "Settings")

        # Find the Event call
        event_calls = [c for c in mock_run.call_args_list if "Event" in c[0][0]]
        assert len(event_calls) == 1
        event_args = event_calls[0][0][0]
        assert "--" in event_args
        assert "/MenuBar" in event_args
