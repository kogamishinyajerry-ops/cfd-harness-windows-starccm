"""End-to-end MOCK smoke test for the CLI.

This test exercises the full V&V loop on a MOCK executor:
  1. CLI parses args
  2. MockExecutor runs the case
  3. AutoVerifier compares against the gold standard
  4. ManifestBuilder builds a Manifest
  5. Signer signs the manifest
  6. DataCollector writes data.json
  7. ReportGenerator renders the markdown report
  8. MetricsAccumulator records the verdict
"""
from __future__ import annotations

from pathlib import Path

from cfd_harness.cli.run import main


def test_cli_lid_driven_cavity_mock_passes(ldc_task_spec, tmp_path, repo_root):
    """The CLI runs end-to-end on MOCK executor and exits 0."""
    import sys
    argv = [
        "--case", "lid_driven_cavity",
        "--executor", "mock",
        "--output", str(tmp_path / "reports"),
        "--sign-key", "test-only-key-padded-to-at-least-32-bytes",
    ]
    rc = main(argv)
    assert rc == 0
    # Check the report was written
    case_dir = tmp_path / "reports" / "lid_driven_cavity"
    assert case_dir.exists()
    data_files = list(case_dir.glob("*/data.json"))
    md_files = list(case_dir.glob("*/data.md"))
    assert len(data_files) == 1
    assert len(md_files) == 1


def test_cli_naca0012_mock(cylinder_task_spec, tmp_path):
    """NACA on MOCK — exit 0, report written."""
    argv = [
        "--case", "naca0012_airfoil",
        "--executor", "mock",
        "--output", str(tmp_path / "reports"),
        "--sign-key", "test-only-key-padded-to-at-least-32-bytes",
    ]
    rc = main(argv)
    assert rc == 0
    assert (tmp_path / "reports" / "naca0012_airfoil").exists()


def test_cli_circular_cylinder_wake_mock(tmp_path):
    """Cylinder wake on MOCK — exit 0."""
    argv = [
        "--case", "circular_cylinder_wake",
        "--executor", "mock",
        "--output", str(tmp_path / "reports"),
        "--sign-key", "test-only-key-padded-to-at-least-32-bytes",
    ]
    rc = main(argv)
    assert rc == 0


def test_cli_unknown_case(tmp_path):
    """An unknown case_id returns exit code 2."""
    argv = [
        "--case", "no_such_case",
        "--executor", "mock",
        "--output", str(tmp_path / "reports"),
    ]
    rc = main(argv)
    assert rc == 2


def test_cli_win_starccm_stub(tmp_path):
    """Stage 1+2: --executor win_starccm returns MODE_NOT_YET_IMPLEMENTED;
    the verdict is FAIL (real-solver refused), so exit code is 1."""
    argv = [
        "--case", "lid_driven_cavity",
        "--executor", "win_starccm",
        "--output", str(tmp_path / "reports"),
        "--sign-key", "test-only-key-padded-to-at-least-32-bytes",
    ]
    rc = main(argv)
    # Refusal → not validated → exit 1
    assert rc == 1
