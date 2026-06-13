"""fan_blade.py · 7 月期 stub · fan/propeller case builder + aero extractor.

Plane: ADAPTER_STARCCM (per ADR-001 four-plane import law).
Lives under ``cfd_harness.starccm_adapter.case_solve`` — does NOT
import from cfd_harness.executor (the EXECUTION plane). Only consumes
``cfd_harness.starccm_adapter.executor.StarCCMExecutor``'s read-only
``_CASE_TO_COMMAND`` / ``_MACRO_NAME_FOR_CASE`` mappings; the
executor itself is not subclassed here.

==============================================================================
                       !!  STUB  —  NOT A REAL IMPLEMENTATION  !!
==============================================================================

This module is a **deliberate stub** scaffolded in 7 月期 to fill the
``case_solve/fan_blade.py`` slot that verdict-2026-07 §5.2 D-4 / D-9
flagged as HIGH-severity debt blocking M1 acceptance. It exists to:

1. Make the 4 import statements below importable on a fresh venv (so
   CI / docs build / plain `import cfd_harness.starccm_adapter.case_solve`
   does not blow up).
2. Give the chief-engineer a visible "stub surface" to read in the
   7 月底 M1 review — they can SEE the API shape, but they should NOT
   trust the implementation.

The full implementation lands in **8 月数据期** with the August
GREEN-light call (per DEC-008 §2.3 L0 grant + CHARTER §2 数据期 ①).
8-10 月路线图:
  - 8 月: 数据期 ① (2D LHS 100-200 样本, MOCK 端 + 真机 30-50 混合)
          *This stub is replaced with the 2D-slice real builder.*
  - 9 月: 数据期 ② (3D 单通道 30-50 首批)
          *`rotor37_single_channel` is wired to Rotor37SingleChannel.java.*
  - 10 月: 建模期 ① (surrogate baseline 验证)

Already-deployed facts (D-1 / D-6 / D-7 — all DONE 2026-06-12):
  - D-1: PLAID-datasets/Rotor37 is a Safran RANS surrogate, not a
    NASA experimental gold; rotor37 gold 来源转 NASA-TP-1338 +
    Suder 1995, 详见 ``planning/d1-plaid-probe.md``.
  - D-6: Codebuddy ``analyze`` CLI is a real command (NOT dead code)
    and ``_invoke`` is missing one ``encoding="utf-8"`` line that
    will be patched before 7 月数据期, 详见
    ``planning/d6-analyze-probe.md``.
  - D-7: ``star.motion.RotatingReferenceFrame`` exists in 2402 R8
    (1/4 candidates hit). 3D 旋转域 GREEN; full 90s spawn 留 7/20-7/25,
    详见 ``planning/d7-probe-result.md`` + ``macros/EnableModelProbe.java``.

What this stub DOES:
  - ``build_case(rotor_yaml, output_dir)``: read the gold-standard yaml
    (if present), and write a placeholder .sim path + a minimal Java
    macro template string into ``output_dir``. **Returns the .sim
    path; does NOT execute the macro.** Suitable for unit-testing the
    surface; not suitable for a real solve.
  - ``extract_aero(sim_path)``: parse a hypothetical ``_summary.json``
    file at the .sim's parent dir. If absent (the case for any real
    solve today, since no real .sim is solved), returns a dict of all
    ``None`` for the 4 expected quantities. This is a SHAPE contract;
    the real reader lands in 8 月.

What this stub does NOT do (and you SHOULD NOT call):
  - Spawn STAR-CCM+ (``subprocess`` of ``starccm+.bat`` is forbidden
    here; that path is owned by ``StarCCMExecutor``).
  - Import ``star.*`` Java classes (no classpath, no JVM).
  - Reuse ``executor._extract_key_quantities`` (which is executor
    internal; reusing would couple case_solve to EXECUTION plane
    internals).
  - Sign or attest anything (no V&V claims, no manifest, no audit).

References (the up-stack contract this stub conforms to):
  - verdict-2026-07 §5.2 D-4 (this stub = the deliverable)
  - track-d-deliverable.md §3 ★ 3 (the ROI entry that created this slot)
  - CHARTER.md §2 数据期 ① (the 8 月 plan that uses this entry point)
  - DEC-008 §2.3 L0 grant (the autonomy envelope that allows the stub)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

# 4 quantities the rotor family is expected to report.
# Per verdict-2026-07 §5.2 C1: total_temperature_ratio is the one
# FlowType.ROTOR_COMPRESSOR sub-enum tracks that the 7 月 V&V engine
# does NOT yet support. Until that lands, we keep these names as plain
# strings and the dict-of-None is the canonical "not measured yet" shape.
_AERO_KEYS = ("cl", "cd", "PR", "eta_is")  # noqa: N806 (PR is conventional)

# A minimal STAR-CCM+ Java macro template. The string is intentionally
# incomplete — it has placeholders that the August real builder will
# fill with the user's `Rotor37Slice.java` / `Rotor37SingleChannel.java`
# content. Today this template is only used to PROVE that
# ``build_case`` returns a usable path, not to actually run a solve.
_MACRO_TEMPLATE = """// AUTO-GENERATED STUB MACRO — DO NOT RUN.
// 7 月期 fan_blade.py scaffold; replaced in 8 月数据期 ①.
public class StubRotor37Case {{
    public static void main(String[] args) {{
        // TODO(8月): wire rotor yaml path + Re/Ma/alpha to StarCCM+.
    }}
}}
"""


def build_case(rotor_yaml: str, output_dir: str) -> Path:
    """Build a placeholder .sim + macro template for a rotor case.

    Parameters
    ----------
    rotor_yaml : str
        Path to the gold-standard rotor yaml (e.g.
        ``knowledge/gold_standards/rotor37.yaml``). **May not exist
        yet** — the 7 月期 track-c草稿 uses ``__TO_FILL_FROM_LIT__``
        placeholders and is itself HIGH-severity debt (D-2). This
        stub is tolerant of a missing file: it logs the absence and
        still returns a valid .sim path.
    output_dir : str
        Directory to write the .sim placeholder + macro template into.
        Created if missing.

    Returns
    -------
    Path
        The .sim path that *would* be opened by STAR-CCM+. The file
        itself is not created; only ``<output_dir>/stub_rotor_macro.java``
        is written (a marker that the stub ran).

    Notes
    -----
    Stub-only: does not parse yaml, does not run STAR-CCM+. The 8 月
    real builder will: (a) parse the yaml to get design-point Re/Ma/alpha;
    (b) emit a real Java macro via the Codebuddy macro template engine;
    (c) hand the macro path to ``StarCCMExecutor._MACRO_NAME_FOR_CASE``
    routing.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Write the marker macro so smoke tests can detect "stub ran".
    macro_path = out / "stub_rotor_macro.java"
    macro_path.write_text(_MACRO_TEMPLATE, encoding="utf-8")

    # The .sim path we hand back. The file is intentionally NOT created;
    # STAR-CCM+ is the only thing allowed to write .sim files, and
    # the stub does not invoke STAR-CCM+.
    case_id = Path(rotor_yaml).stem if rotor_yaml else "rotor37_slice"
    sim_path = out / f"{case_id}_PLACEHOLDER.sim"
    return sim_path


def extract_aero(sim_path: str) -> Dict[str, Optional[float]]:
    """Extract the 4 aerodynamic quantities from a solved .sim's
    sibling ``_summary.json`` file.

    Parameters
    ----------
    sim_path : str
        Path to a (hypothetically) solved .sim file. The summary is
        expected at ``<sim_path parent>/<sim_path stem>_summary.json``.

    Returns
    -------
    dict
        Mapping ``{cl, cd, PR, eta_is} -> float | None``. Returns
        ``{k: None for k in _AERO_KEYS}`` when the summary file is
        absent (the case for any real .sim today, since no rotor
        case has been solved in 7 月期).

    Notes
    -----
    Stub-only: returns all-None when no summary file exists. The 8 月
    real reader will: (a) parse the summary.json shape that the
    user's Rotor37Slice.java macro writes; (b) use the ForceCoefficientReport
    reader that track-d §1.3 (★ 4) calls out as the missing piece for
    Cl/Cd; (c) populate the dict with measured floats.
    """
    result: Dict[str, Optional[float]] = {k: None for k in _AERO_KEYS}
    sim = Path(sim_path)
    summary = sim.parent / f"{sim.stem}_summary.json"
    if not summary.exists():
        return result
    # Future real reader: json.loads + traverse to the 4 quantity keys.
    # Stub keeps the surface but does not implement the parse.
    return result


__all__ = ["build_case", "extract_aero", "_AERO_KEYS"]
