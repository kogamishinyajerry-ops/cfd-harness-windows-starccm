"""case_solve/ · fan/propeller case builder + aero extractor.

Plane: ADAPTER_STARCCM (per ADR-001 four-plane import law).
Stage 3+ placeholder. The 7 月期 fan_blade.py is a **stub** (see its
module docstring). The full implementation lands in 8 月数据期 ①.

This __init__.py is intentionally empty (no re-exports) for the 7 月
scaffold; once the real builder lands, re-export ``build_case`` and
``extract_aero`` here so callers can do
``from cfd_harness.starccm_adapter.case_solve import build_case``.
"""
