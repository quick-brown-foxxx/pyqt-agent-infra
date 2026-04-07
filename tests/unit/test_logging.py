"""Tests for logging setup utilities."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clean_root_logger() -> object:
    """Remove any handlers added during tests from root logger.

    Yields control to the test, then cleans up handlers to prevent
    cross-test pollution of the logging hierarchy.
    """
    root = logging.getLogger()
    handlers_before = list(root.handlers)
    level_before = root.level
    yield
    # Remove only handlers that were added during the test
    for handler in root.handlers[:]:
        if handler not in handlers_before:
            root.removeHandler(handler)
            handler.close()
    root.setLevel(level_before)


class TestSetupFileLogging:
    """Test setup_file_logging() rotating file handler creation."""

    def test_creates_log_directory(self, tmp_path: Path) -> None:
        """Log directory should be created if it doesn't exist."""
        from qt_ai_dev_tools.logging.logger_setup import setup_file_logging

        log_dir = tmp_path / "nested" / "logs"
        setup_file_logging(log_dir=log_dir, app_name="test")

        assert log_dir.is_dir()

    def test_creates_log_file(self, tmp_path: Path) -> None:
        """A log file named <app_name>.log should be created."""
        from qt_ai_dev_tools.logging.logger_setup import setup_file_logging

        setup_file_logging(log_dir=tmp_path, app_name="myapp")

        log_file = tmp_path / "myapp.log"
        assert log_file.exists()

    def test_adds_rotating_handler_to_root(self, tmp_path: Path) -> None:
        """A RotatingFileHandler should be added to the root logger."""
        from qt_ai_dev_tools.logging.logger_setup import setup_file_logging

        setup_file_logging(log_dir=tmp_path, app_name="test")

        root = logging.getLogger()
        rotating_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
        assert len(rotating_handlers) >= 1

    def test_handler_level_matches_requested(self, tmp_path: Path) -> None:
        """The file handler level should match the level argument."""
        from qt_ai_dev_tools.logging.logger_setup import setup_file_logging

        setup_file_logging(log_dir=tmp_path, app_name="test", level=logging.WARNING)

        root = logging.getLogger()
        rotating_handlers = [h for h in root.handlers if isinstance(h, RotatingFileHandler)]
        assert rotating_handlers[-1].level == logging.WARNING

    def test_messages_are_written_to_file(self, tmp_path: Path) -> None:
        """Log messages should appear in the log file."""
        from qt_ai_dev_tools.logging.logger_setup import setup_file_logging

        setup_file_logging(log_dir=tmp_path, app_name="test", level=logging.DEBUG)

        test_logger = logging.getLogger("test_file_write")
        test_logger.debug("file_write_marker_12345")

        # Flush handlers to ensure write
        for handler in logging.getLogger().handlers:
            handler.flush()

        log_file = tmp_path / "test.log"
        content = log_file.read_text()
        assert "file_write_marker_12345" in content

    def test_sets_root_level_to_requested(self, tmp_path: Path) -> None:
        """Root logger level should be set to the requested level."""
        from qt_ai_dev_tools.logging.logger_setup import setup_file_logging

        setup_file_logging(log_dir=tmp_path, app_name="test", level=logging.DEBUG)

        root = logging.getLogger()
        assert root.level <= logging.DEBUG


class TestSetupStderrLogging:
    """Test setup_stderr_logging() colored stream handler creation."""

    def test_adds_handler_to_root(self) -> None:
        """A StreamHandler should be added to the root logger."""
        from qt_ai_dev_tools.logging.logger_setup import setup_stderr_logging

        root = logging.getLogger()
        count_before = len(root.handlers)

        setup_stderr_logging(level=logging.INFO)

        assert len(root.handlers) == count_before + 1

    def test_sets_root_level(self) -> None:
        """Root logger level should be set to the requested level."""
        from qt_ai_dev_tools.logging.logger_setup import setup_stderr_logging

        setup_stderr_logging(level=logging.DEBUG)

        root = logging.getLogger()
        assert root.level <= logging.DEBUG

    def test_handler_writes_to_stderr(self) -> None:
        """The added handler should be a StreamHandler writing to stderr."""
        import sys

        from qt_ai_dev_tools.logging.logger_setup import setup_stderr_logging

        root = logging.getLogger()
        count_before = len(root.handlers)

        setup_stderr_logging(level=logging.INFO)

        new_handler = root.handlers[count_before]
        assert isinstance(new_handler, logging.StreamHandler)
        assert new_handler.stream is sys.stderr  # pyright: ignore[reportAttributeAccessIssue]  # rationale: StreamHandler.stream exists at runtime


class TestConfigureLoggerLevel:
    """Test configure_logger_level() helper."""

    def test_sets_level(self) -> None:
        """Named logger should have its level set."""
        from qt_ai_dev_tools.logging.logger_setup import configure_logger_level

        configure_logger_level("test.noisy.lib", logging.WARNING)

        logger = logging.getLogger("test.noisy.lib")
        assert logger.level == logging.WARNING

    def test_sets_propagate(self) -> None:
        """Propagation should match the propagate argument."""
        from qt_ai_dev_tools.logging.logger_setup import configure_logger_level

        configure_logger_level("test.no.propagate", logging.INFO, propagate=False)

        logger = logging.getLogger("test.no.propagate")
        assert logger.propagate is False
