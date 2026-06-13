#!/usr/bin/env python3
"""Project quality gate for cfd-harness-windows-starccm.

A single command that enforces the project's load-bearing guarantees so the
green test suite + the honesty/trust invariants stay durable rather than
incidental. Intended for a pre-release / pre-commit / CI check.

Checks
------
  [1] Mock/unit test suite passes AND coverage(cfd_harness) >= --min-cov
      (default 85%; current baseline ~87%). Runs:
        pytest -m "not real_solver" --cov=cfd_harness --cov-fail-under=<N>
  [2] Honesty / trust invariants (library-level, fast — defence in depth on
      the guarantees the audit/V&V code exists to provide):
        a. a MOCK verdict can NEVER be validated; a clean MOCK PASS is
           clamped to WARN (the EXECUTOR_ABSTRACTION §6.1 ceiling).
        b. a dev-unsigned audit is REJECTED by the default verifier trust
           policy, but is integrity-verifiable with --allow-untrusted (DEC-010).
        c. a tampered manifest fails verification.

Exit code 0 iff ALL checks pass.

Usage
-----
  python scripts/quality_gate.py                 # full gate (tests + coverage + invariants)
  python scripts/quality_gate.py --fast          # invariants only (skip pytest + coverage)
  python scripts/quality_gate.py --min-cov 80    # custom coverage floor
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"


def _pass(name: str) -> None:
    print(f"  [PASS] {name}")


def _fail(name: str, detail: str = "") -> None:
    print(f"  [FAIL] {name}" + (f" — {detail}" if detail else ""))


def check_tests_and_coverage(min_cov: int) -> bool:
    print(f"[1] mock suite + coverage (>= {min_cov}%)")
    cmd = [
        sys.executable, "-m", "pytest", "-q", "-m", "not real_solver",
        "-p", "pytest_cov", "--cov=cfd_harness",
        "--cov-report=term-missing:skip-covered",
        f"--cov-fail-under={min_cov}",
    ]
    rc = subprocess.run(cmd, cwd=str(REPO)).returncode
    if rc == 0:
        _pass("pytest -m 'not real_solver' + coverage gate")
    else:
        _fail("pytest/coverage", f"pytest exited {rc} (tests failed or coverage < {min_cov}%)")
    return rc == 0


def _dummy_spec():
    from cfd_harness.models import FlowType, GeometryType, TaskSpec
    return TaskSpec(
        case_id="_gate_probe",
        flow_type=FlowType.INTERNAL,
        geometry_type=GeometryType.SIMPLE_GRID,
    )


def check_honesty_invariants() -> bool:
    print("[2] honesty / trust invariants")
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))  # safety net if not pip-installed
    try:
        from cfd_harness.auto_verifier.verifier import Verdict
        from cfd_harness.auto_verifier.gold_standard_comparator import ComparisonResult
        from cfd_harness.auto_verifier.convergence_checker import ConvergenceChecker
        from cfd_harness.auto_verifier.physics_checker import PhysicsChecker
        from cfd_harness.audit_package.manifest import Manifest, SCHEMA_VERSION
        from cfd_harness.audit_package.sign import Signer, DEV_UNSIGNED_KEY
        from cfd_harness.audit_package.verify import verify_audit
    except ImportError as e:  # pragma: no cover
        _fail("import cfd_harness", str(e))
        return False

    ok = True

    # (a) MOCK ceiling: a clean MOCK PASS clamps to WARN and never validates.
    conv = ConvergenceChecker(1e-3).check({"p": 1e-9})
    phys = PhysicsChecker().check(_dummy_spec())
    mock_v = Verdict(
        level="PASS",
        comparison=ComparisonResult(all_pass=True),
        convergence=conv, physics=phys, suggestions=[], is_mock=True,
    )
    if mock_v.level == "WARN" and mock_v.is_validated is False and mock_v.mock_ceiling_applied:
        _pass("MOCK verdict clamped to WARN, never validated (§6.1 ceiling)")
    else:
        _fail("MOCK ceiling", f"level={mock_v.level} is_validated={mock_v.is_validated}")
        ok = False

    # Build a "validated"-looking manifest signed with the (public) dev key.
    m = Manifest(
        schema_version=SCHEMA_VERSION, case_id="_gate_probe",
        executor_mode="win_starccm", contract_hash="probe", spec_version="0.3",
        verdict_level="PASS", is_validated=True, is_mock=False,
        comparison_all_pass=True,
    )
    sig = Signer(DEV_UNSIGNED_KEY).sign(m)
    audit = {
        "manifest": m.to_dict(),
        "signature": {
            "digest": sig.digest, "hmac": sig.hmac, "key_id": sig.key_id,
            "algorithm": sig.algorithm, "signed_at": sig.signed_at,
        },
        "signing": {"key_source": "dev-unsigned", "trusted": False},
    }

    # (b) dev-unsigned is rejected by default, but integrity-verifiable.
    rejected = verify_audit(audit, DEV_UNSIGNED_KEY)
    integrity = verify_audit(audit, DEV_UNSIGNED_KEY, require_trusted=False)
    if (not rejected.accepted) and integrity.accepted:
        _pass("dev-unsigned audit rejected by default; integrity-only accepts (DEC-010)")
    else:
        _fail("dev-unsigned trust policy",
              f"default.accepted={rejected.accepted} integrity.accepted={integrity.accepted}")
        ok = False

    # (c) tampering breaks verification.
    tampered = dict(audit)
    tampered["manifest"] = {**audit["manifest"], "verdict_level": "FAIL"}
    if not verify_audit(tampered, DEV_UNSIGNED_KEY, require_trusted=False).accepted:
        _pass("tampered manifest fails verification")
    else:
        _fail("tamper detection", "a modified manifest still verified")
        ok = False

    return ok


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="cfd-harness quality gate")
    p.add_argument("--min-cov", type=int, default=85, help="coverage floor %% (default 85)")
    p.add_argument("--fast", action="store_true", help="skip the pytest+coverage run")
    args = p.parse_args(argv)

    print("=" * 64)
    print("cfd-harness-windows-starccm · quality gate")
    print("=" * 64)

    results = []
    if not args.fast:
        results.append(check_tests_and_coverage(args.min_cov))
    else:
        print("[1] mock suite + coverage — SKIPPED (--fast)")
    results.append(check_honesty_invariants())

    passed = all(results)
    print("-" * 64)
    print(f"QUALITY GATE: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
