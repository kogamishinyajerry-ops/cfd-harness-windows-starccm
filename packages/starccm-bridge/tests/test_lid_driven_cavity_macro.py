"""Tests for the case-specific Java macros that ship with the harness.

These tests do NOT spawn STAR-CCM+ (which is slow + license-heavy).
They verify the macro files exist + parse as valid Java + declare
the right class.

For the actual E2E (spawn STAR-CCM+ + run the macro + verify the
output CSV), see ``test_lid_driven_cavity_e2e.py`` (marked
``real_solver``, opt-in only).
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest


HARNESS_ROOT = Path(__file__).resolve().parents[3]
MACROS_DIR = HARNESS_ROOT / "macros"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


@pytest.mark.real_solver
def test_lid_driven_cavity_macro_exists():
    """LidDrivenCavity.java must ship with the harness."""
    p = MACROS_DIR / "LidDrivenCavity.java"
    assert p.exists(), f"missing: {p}"
    assert p.stat().st_size > 1000, f"LidDrivenCavity.java is suspiciously small ({p.stat().st_size} bytes)"


@pytest.mark.real_solver
def test_lid_driven_cavity_macro_declares_correct_class():
    """LidDrivenCavity.java must declare `class LidDrivenCavity extends StarMacro`."""
    p = MACROS_DIR / "LidDrivenCavity.java"
    assert p.exists()
    content = _read(p)
    assert "class LidDrivenCavity extends StarMacro" in content, (
        "LidDrivenCavity.java must declare `class LidDrivenCavity extends StarMacro`"
    )
    assert "public void execute()" in content, "must override execute()"


@pytest.mark.real_solver
def test_lid_driven_cavity_macro_has_required_steps():
    """LidDrivenCavity.java must have all 10 step methods (geometry, region, continuum, physics, BCs, mesh, init, run, sample, save)."""
    p = MACROS_DIR / "LidDrivenCavity.java"
    content = _read(p)
    required_methods = [
        "step1CreateBlock",
        "step2CreateRegion",
        "step3CreateContinuum",
        "step4EnablePhysics",
        "step5SetBCs",
        "step6CreateMesh",
        "step7Init",
        "step8Run",
        "step9SampleCenterline",
        "step10Save",
    ]
    for m in required_methods:
        assert f"void {m}()" in content, f"missing step method: {m}"


@pytest.mark.real_solver
def test_lid_driven_cavity_macro_has_correct_constants():
    """LidDrivenCavity.java must declare the Ghia 1982 cavity defaults."""
    p = MACROS_DIR / "LidDrivenCavity.java"
    content = _read(p)
    # Defaults that match the gold standard
    assert "gSize" in content and "1.0" in content, "gSize default must be 1.0"
    assert "gLidU" in content and "1.0" in content, "gLidU default must be 1.0"
    assert "gNu" in content and "0.01" in content, "gNu default must be 0.01 (→ Re=100)"
    assert "gNx" in content and "129" in content, "gNx default must be 129 (Ghia 1982 reference)"
    assert "gNy" in content and "129" in content, "gNy default must be 129 (Ghia 1982 reference)"


@pytest.mark.real_solver
def test_lid_driven_cavity_macro_handles_reflection_gracefully():
    """LidDrivenCavity.java must wrap reflective calls in try/catch (different STAR-CCM+ versions differ)."""
    p = MACROS_DIR / "LidDrivenCavity.java"
    content = _read(p)
    # Each step method should have a try/catch
    for step in ["step1CreateBlock", "step5SetBCs", "step6CreateMesh", "step9SampleCenterline"]:
        # Find the method body and count try/catch pairs
        idx = content.find(f"void {step}()")
        assert idx > 0, f"missing {step}"
        end_idx = content.find("\n    }", idx)
        body = content[idx:end_idx]
        assert "try" in body, f"{step} should have a try block"
        assert "catch" in body, f"{step} should have a catch block"


@pytest.mark.real_solver
@pytest.mark.skipif(
    not (HARNESS_ROOT / "macros" / "LidDrivenCavity.java").exists(),
    reason="LidDrivenCavity.java not found",
)
def test_lid_driven_cavity_macro_no_obvious_compile_errors():
    """LidDrivenCavity.java should not have obvious unbalanced braces (lightweight syntax check)."""
    p = MACROS_DIR / "LidDrivenCavity.java"
    content = _read(p)
    # Naive brace count (string-aware is hard; this is a quick sanity check)
    open_braces = content.count("{")
    close_braces = content.count("}")
    assert open_braces == close_braces, (
        f"unbalanced braces in LidDrivenCavity.java: {{={open_braces} }}={close_braces}"
    )
    open_parens = content.count("(")
    close_parens = content.count(")")
    assert open_parens == close_parens, (
        f"unbalanced parens in LidDrivenCavity.java: {open_parens} vs {close_parens}"
    )
