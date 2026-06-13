"""
conftest.py for tests/test_surrogate/.

Auto-applies the ``@pytest.mark.surrogate`` marker to every test collected
under this directory. The marker is registered in pyproject.toml.

Note: a bare ``pytestmark = pytest.mark.surrogate`` at module level in a
conftest.py is *not* applied to collected items (unlike the same line at
the top of a test module). We have to register the marker manually in
``pytest_collection_modifyitems``.

This avoids editing 5 test files individually and keeps the
``pytest -m surrogate`` / ``pytest -m "not surrogate"`` selection clean
for the M3 surrogate track (DEC-008).
"""
from __future__ import annotations

import pytest


def pytest_collection_modifyitems(config, items):
    """Attach @pytest.mark.surrogate to every test in this directory."""
    for item in items:
        item.add_marker(pytest.mark.surrogate)
