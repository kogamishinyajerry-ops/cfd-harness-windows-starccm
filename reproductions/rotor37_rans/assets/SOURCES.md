# Rotor 37 RANS reproduction — acquired assets (provenance)

Acquired 2026-06-15. Each file verified on disk (size + magic bytes / parser).

## Blade geometry (USABLE — needs meshing)
- `deeplabs_rotor37_geometries_1.npy` (64,512,128 B) — NumPy float64 array, shape (1000, 2, 9, 112, 4)
  = (samples, surfaces[0=suction,1=pressure], 9 spanwise sections, 112 points/side, [x,y,z,label]).
  Coordinates in METERS. Sample 0 is the baseline Rotor 37 blade; the other 999 are LCVT
  parametric variations. Radii ~0.171–0.255 m, blade height ~0.04 m (physically consistent w/ R37).
  Verified: all finite, correct shape.
- `deeplabs_rotor37_geometries_2.npy` — second 1000 samples (same schema). May be partial; the
  robust resumable downloader keeps appending until 64,512,128 B (re-run if smaller).
- `deeplabs_rotor37_edp.csv` (1,710,414 B) — 2000 rows x 53 cols = 36 Engineering Design
  Parameters (chord, metal angles, wedge angles, stagger, Bezier thickness/stacking ctrl pts) +
  17 CFD aerodynamic performances per sample.
- `deeplabs_rotor37_README.md`, `deeplabs_rotor37_CITATION.cff`, `deeplabs_rotor37_load_data.ipynb`,
  `deeplabs_rotor37_original_blade.png` — dataset docs / loader / reference render.
  Source: GitHub `Deeplabs-ai/rotor37` (Sanguineti, Ratto, Perrone, Ricci, Beqiraj 2022).
  Raw URLs: https://raw.githubusercontent.com/Deeplabs-ai/rotor37/main/data/<file>

## Design / validation reports (PDF)
- `nasa_tp1337_reid_moore_1978.pdf` (3,813,337 B, 132 pp, %%EOF OK) — NASA TP-1337, Reid & Moore
  1978, "Design and Overall Performance of Four Highly Loaded, High-Speed Inlet Stages..." — the
  design report with the spanwise blade geometry tables (Rotor 37 = stage 36/37 family).
  Source: https://ntrs.nasa.gov/api/citations/19780025165/downloads/19780025165.pdf
- `suder_TP-3623_1996.pdf` (11.8 MB, 268 pp) — NASA TM-107310, Suder 1996, experimental flow
  investigation in the transonic axial compressor (Rotor 37) — blockage/loss measurements.
- `ameri_CR-2010-216235.pdf` (2.1 MB, 7 pp) — NASA/CR-2010-216235 (AIAA 2009-1060), Ameri,
  "NASA Rotor 37 CFD Code Validation, Glenn-HT" — contains grid topology/size details.
- `vanzante_blindtest.pdf` (1.45 MB) — ASME/IGTI Rotor 37 blind-test material (scanned PDF).
  (suder/ameri/vanzante were already present in the assets dir before this run.)

## NOT acquired
- A ready computational GRID/MESH (Plot3D/.cgns/.msh/.ccm): the canonical NASA turbmodels page
  (turbmodels.larc.nasa.gov/Other_exp_Data/rotor37_exp.html) now 301-redirects entirely to
  www.nasa.gov and no longer hosts any grid or even the exp tar.gz. Rotor 37 is a validation case
  where users build their own mesh; no official ready grid is publicly hosted.
- PLAID CGNS dataset (real RANS meshes of R37-in-duct, CGNS standard): exists and is reachable —
  HF `PLAID-datasets/Rotor37` (11 parquet shards, ~397 MB each) and Zenodo record 10149830
  (`Rotor37.tar.gz`, 3.1 GB, md5 638ee66c3fd6c2040c44e328c2bb02c1). NOT downloaded: the 397 MB
  shard repeatedly truncated over this throttled link, and the meshes are morphed parametric
  variants requiring `pyplaid` to decode to CGNS. Fetch on a faster link with:
    huggingface_hub.hf_hub_download(repo_id="PLAID-datasets/Rotor37", repo_type="dataset",
       filename="data/all_samples-00000-of-00011.parquet")
  then decode via plaid.bridges.huggingface_bridge.huggingface_dataset_to_plaid -> sample.get_nodes().
