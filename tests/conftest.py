"""Shared pytest configuration and hooks."""

from __future__ import annotations

import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Auto-group e2e and integration tests for serial execution under xdist.

    When running with pytest-xdist (-n auto), unit tests distribute freely
    across workers for maximum parallelism. E2E and integration tests share
    a single worker (serial) because they depend on shared resources:
    DISPLAY :99, AT-SPI bus, D-Bus session, app subprocesses.

    Without xdist (serial mode), this hook is a no-op — the marker has no
    effect when there's only one worker.

    NOTE: tryfirst=True is required so the marker is applied before xdist's
    WorkerInteractor.pytest_collection_modifyitems reads it to append the
    @group suffix to nodeids.
    """
    for item in items:
        fspath = str(item.fspath)
        if "/tests/e2e/" in fspath or "/tests/integration/" in fspath:
            item.add_marker(pytest.mark.xdist_group("serial_vm"))
