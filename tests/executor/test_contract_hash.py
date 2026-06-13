"""Pin the contract_hash / spec-binding behavior (recon 'unverified claim').

contract_hash = sha256(spec_file_sha256 | MODE | VERSION). The spec hash is
lru_cached and falls back to a documented sentinel when the spec file is
unreadable. These tests lock in: mode-sensitivity, stability, and the
sentinel fallback — with cache isolation so the sentinel never leaks to
other tests in the session.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cfd_harness.executor import base


@pytest.fixture
def spec_cache_isolation():
    """Clear the lru_cache before AND after so a sentinel value computed
    here cannot poison contract_hash for any other test."""
    base._executor_spec_sha256.cache_clear()
    yield
    base._executor_spec_sha256.cache_clear()


def test_contract_hash_stable_and_mode_sensitive():
    from cfd_harness.executor.mock import MockExecutor
    from cfd_harness.executor.win_starccm import WinStarCCMExecutor

    h1 = MockExecutor().contract_hash
    h2 = MockExecutor().contract_hash
    assert h1 == h2  # same mode/spec/version -> stable
    assert WinStarCCMExecutor().contract_hash != h1  # different MODE -> differs
    assert len(h1) == 64  # SHA-256 hex


def test_spec_available_true_in_repo(spec_cache_isolation):
    """In a source checkout the spec file is present."""
    assert base.spec_is_available() is True
    assert base._executor_spec_sha256() != base.SPEC_FILE_UNAVAILABLE_SENTINEL


def test_missing_spec_falls_back_to_sentinel(monkeypatch, spec_cache_isolation):
    """A missing/unreadable spec file yields the sentinel (no crash), so
    contract_hash is deterministic but spec-unbound."""
    monkeypatch.setattr(base, "_SPEC_FILE", Path("this-spec-does-not-exist.md"))
    base._executor_spec_sha256.cache_clear()
    assert base._executor_spec_sha256() == base.SPEC_FILE_UNAVAILABLE_SENTINEL
    assert base.spec_is_available() is False

    # contract_hash still computes (over the sentinel) and stays mode-sensitive.
    from cfd_harness.executor.mock import MockExecutor
    from cfd_harness.executor.win_starccm import WinStarCCMExecutor
    assert MockExecutor().contract_hash != WinStarCCMExecutor().contract_hash
