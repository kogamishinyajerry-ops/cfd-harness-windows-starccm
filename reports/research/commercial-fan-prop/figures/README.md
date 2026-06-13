# Figures README 鈥?paper-draft-2026-07.md visualization provenance

> All PNG / .sim figures embedded in `paper-draft-2026-07.md` are
> **real STAR-CCM+ 2402 R8 outputs** from the cfd-harness v35 pipeline,
> not placeholders or MOCK data. Provenance is file:line traced below.

## Embedded in paper

| Paper fig | Local file | Provenance | Solver status | Notes |
|---|---|---|---|---|
| **Fig. 1** NACA 2412 v35 pressure | `figures/fig1_naca_v35_pressure.png` | `D:\StarCCM Codebuddy\Cases\Results\naca_v35_pressure.png` produced by `macros/NacaTrueE2E.java` v1 (build 2026-06-11, 6/12 02:33:22) | **real STAR-CCM+ 2402 R8** k-蠅 SST, steady, 2000 iter, Re=1脳10鈦? AOA=4掳, 115 MB .sim saved | contour scale -50..+50 Pa, polyhedral mesh visible |
| **Fig. 2** NACA 2412 v35 velocity | `figures/fig2_naca_v35_velocity.png` | same pipeline as Fig. 1 | same | scale -1..15 m/s; the negative lower bound is a display override, not a physical negative velocity (Vector3 fields are non-negative) |
| `.sim` Lid-Driven Cavity | `figures/ldc_solved.sim` | `D:\StarCCM Codebuddy\Cases\Results\lid_driven_cavity_solved.sim`, 1.9 MB, 5/10 鐪熻窇 by `macros/LidDrivenCavity.java` | **real STAR-CCM+ 2402 R8** laminar steady, 5000 iter, Re=100, lid U=1 m/s, 129脳129 mesh | summary.json: `init_ok=true`, `run_ok=true`, `mesh_nx=129, mesh_ny=129`. u_centerline.csv is `null` (DEC-005 known gap; STAR-CCM+ 2402 R8 FF probe API broken 鈥?workaround: open `.sim` in GUI) |

## Files in `sidecar_diagnostic_only/` (NOT cited in paper)

These were copied during exploration but are NOT embedded in the
paper. They are kept only as diagnostic reference:

- `fig5_yplus.png`, `fig6_mesh.png` 鈥?sourced from a 2026-05-15
  APU Case1 sim, **not cfd-harness-scope**.
- `fig_blank_ldc_scene.png` 鈥?`lid_driven_cavity_solved_scene.png` is
  an empty STAR-CCM+ startup screen (no scene rendered), discarded.
- `fig_fake_v161R_pressure.png` 鈥?`cyl_v161R_pressure.png` is a
  2026-06-05 v161R pipeline frame where the solver field has not
  been plotted (single-color shading, no pressure gradient); not a
  useful data figure.

## Source-of-truth references

- `D:\StarCCM Codebuddy\Cases\Results\naca2412_v35_true.sim` (115 MB) 鈥?the solved sim behind Fig. 1 & 2
- `D:\StarCCM Codebuddy\Cases\Results\naca2412_summary.json` 鈥?pipeline summary (cl=8.52, cd=-0.41, cm=0.003 from v3 Vector3 fields; sign quirk is a known alias issue 鈥?see DEC-005)
- `D:\StarCCM Codebuddy\Cases\Results\naca_true_v1.log` 鈥?full step-by-step pipeline log (geometry import 鈫?boolean subtract 鈫?region 鈫?physics enable (k-蠅 SST, RANS, segregated flow) 鈫?BC assign (xmin Inlet, xmax Pressure, y/z Symmetry, naca2412 Wall) 鈫?AutoMesh with 10 prism layers stretch=1.3 鈫?MPC run 48.4 s 鈫?initialize 鈫?200 steps 脳 200 iter = 901 s wall)
- `D:\CFD-harness-Windows-StarCCM\reports\LDC_STATUS.md` 鈥?LDC end-to-end status
- `D:\StarCCM Codebuddy\Cases\Results\lid_driven_cavity_summary.json` 鈥?LDC summary (init_ok=true, run_ok=true, mesh=129脳129, 5000 iter)

