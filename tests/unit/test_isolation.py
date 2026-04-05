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
    def test_real_gi_not_replaced_by_mock(self) -> None:
        """In VM (real gi available), _atspi.Atspi must NOT be a MagicMock.

        The actual bug: test_atspi.py's sys.modules.setdefault("gi", mock)
        runs before real gi is imported, permanently installing a mock.
        Later, _atspi.py imports from the mock gi instead of the real one.

        This test detects that scenario: if real gi exists in sys.modules,
        then _atspi.Atspi must be the real module, not a MagicMock.
        On host (no real gi), the mock IS expected — we skip.
        """
        import sys

        gi_mod = sys.modules.get("gi")
        if gi_mod is None:
            pytest.skip("gi not in sys.modules — cannot test mock leak")
        if isinstance(gi_mod, MagicMock):
            pytest.skip("No real gi available (host environment) — mock is expected")

        from qt_ai_dev_tools import _atspi as mod

        atspi = mod.Atspi  # type: ignore[reportUnknownMemberType]  # gi.repository.Atspi has no stubs
        assert not isinstance(atspi, MagicMock), (
            "_atspi.Atspi is a MagicMock despite real gi being available — "
            "test_atspi.py mock leaked into sys.modules"
        )

    def test_gi_modules_are_coherent(self) -> None:
        """sys.modules gi entries must all be real or all be mock — not mixed."""
        import sys

        gi_mod = sys.modules.get("gi")
        gi_repo = sys.modules.get("gi.repository")

        if gi_mod is None:
            pytest.skip("gi not in sys.modules — nothing to check")

        gi_is_mock = isinstance(gi_mod, MagicMock)
        repo_is_mock = isinstance(gi_repo, MagicMock)

        # Both real or both mock — never mixed
        assert gi_is_mock == repo_is_mock, (
            f"Incoherent gi modules: gi={'mock' if gi_is_mock else 'real'}, "
            f"gi.repository={'mock' if repo_is_mock else 'real'}"
        )
