"""Screenshot capture via scrot."""

from __future__ import annotations

import logging
import os

from qt_ai_dev_tools.run import run_command

logger = logging.getLogger(__name__)


def take_screenshot(path: str = "/tmp/screenshot.png") -> str:  # noqa: S108
    """Take a screenshot of the Xvfb display using scrot.

    Returns the path to the saved screenshot.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    env = os.environ.copy()
    env.setdefault("DISPLAY", ":99")
    run_command(["scrot", path], env=env, check=True)
    size = os.path.getsize(path)
    logger.info("Screenshot saved: %s (%d bytes)", path, size)
    return path
