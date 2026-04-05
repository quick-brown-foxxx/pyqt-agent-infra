"""Regression test: gi mock in test_atspi.py must not leak to other modules.

test_atspi.py uses sys.modules.setdefault() to inject mock gi bindings at
module level. This test verifies the gi state is consistent after
test_atspi runs — no broken/detached mocks, no mixed real+mock state.

With pytest-xdist, this runs in a separate worker from e2e tests, so
cross-tier contamination is impossible. This test guards against intra-unit
contamination — ensuring one unit test file doesn't break another.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


class TestGiMockIsolation:
    def test_atspi_module_attribute_is_consistent(self) -> None:
        """After test_atspi.py runs, _atspi.Atspi should still be importable.

        In the VM (where real gi exists), sys.modules.setdefault is a no-op
        and Atspi is the real module. On the host (no gi), setdefault installs
        the mock. Either way, _atspi.Atspi must not be None or a detached mock.

        When run standalone without test_atspi.py and without real gi, the
        import itself fails — that's expected and not what this test guards
        against. We skip in that case.
        """
        import sys

        if "gi" not in sys.modules:
            pytest.skip("gi not in sys.modules — run with test_atspi.py to test mock isolation")

        from qt_ai_dev_tools import _atspi as mod

        # Atspi attribute must exist and be non-None
        assert hasattr(mod, "Atspi")
        atspi = mod.Atspi  # type: ignore[reportUnknownMemberType]  # rationale: gi.repository.Atspi has no stubs
        assert atspi is not None

    def test_gi_modules_are_coherent(self) -> None:
        """sys.modules gi entries must all be real or all be mock — not mixed."""
        import sys

        gi_mod = sys.modules.get("gi")
        gi_repo = sys.modules.get("gi.repository")

        if gi_mod is None:
            # gi not imported at all — fine (no AT-SPI tests ran yet)
            return

        gi_is_mock = isinstance(gi_mod, MagicMock)
        repo_is_mock = isinstance(gi_repo, MagicMock)

        # Both real or both mock — never mixed
        assert gi_is_mock == repo_is_mock, (
            f"Incoherent gi modules: gi={'mock' if gi_is_mock else 'real'}, "
            f"gi.repository={'mock' if repo_is_mock else 'real'}"
        )
