"""Tests for system tray subsystem."""

from __future__ import annotations

from unittest.mock import patch

import pytest

_MOCK_BUSCTL_OUTPUT = 'as 2 ":1.45/StatusNotifierItem" "org.kde.StatusNotifierHost-1234/StatusNotifierItem"'


class TestParseRegisteredItems:
    def test_parse_two_items(self) -> None:
        """_parse_registered_items should parse bus names and object paths."""
        from qt_ai_dev_tools.subsystems.tray import _parse_registered_items

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


class TestListItems:
    def test_list_items_calls_busctl(self) -> None:
        """list_items() should call busctl with correct arguments."""
        from qt_ai_dev_tools.subsystems.tray import list_items

        with (
            patch("qt_ai_dev_tools.subsystems.tray.check_tool") as mock_check,
            patch("qt_ai_dev_tools.subsystems.tray.run_tool", return_value=_MOCK_BUSCTL_OUTPUT) as mock_run,
        ):
            mock_check.return_value = "/usr/bin/busctl"
            items = list_items()

            mock_check.assert_called_once_with("busctl")
            assert mock_run.called
            args = mock_run.call_args[0][0]
            assert "busctl" in args
            assert "--user" in args
            assert "get-property" in args
            assert len(items) == 2


class TestClick:
    def test_click_calls_activate(self) -> None:
        """click() should call Activate on the matching tray item."""
        from qt_ai_dev_tools.subsystems.tray import click

        with (
            patch("qt_ai_dev_tools.subsystems.tray.check_tool"),
            patch("qt_ai_dev_tools.subsystems.tray.run_tool", return_value=_MOCK_BUSCTL_OUTPUT) as mock_run,
        ):
            click("StatusNotifierHost-1234")

            # Second call should be the Activate call
            assert mock_run.call_count == 2
            activate_args = mock_run.call_args_list[1][0][0]
            assert "Activate" in activate_args
            assert "org.kde.StatusNotifierHost-1234" in activate_args

    def test_click_raises_for_unknown_app(self) -> None:
        """click() should raise LookupError when no matching item exists."""
        from qt_ai_dev_tools.subsystems.tray import click

        with (
            patch("qt_ai_dev_tools.subsystems.tray.check_tool"),
            patch("qt_ai_dev_tools.subsystems.tray.run_tool", return_value='as 0'),
            pytest.raises(LookupError, match="No tray item matching"),
        ):
            click("nonexistent-app")


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
