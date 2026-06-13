"""
generate_100_stls.py -- end-to-end M3 pipeline: LHS samples -> 100 watertight STLs.

Reads `stl_samples/lhs/lhs_samples.npy` (output of `cst_lhs.py`) and produces
100 watertight STLs in `stl_samples/stl/`. Also writes a manifest CSV/JSON
with per-sample info (coefficients, mesh stats, watertightness flag).

This is the M3 acceptance deliverable: "100 watertight STL" + verified.

Usage:
  python scripts/generate_100_stls.py
  python scripts/generate_100_stls.py --n 100 --lhs stl_samples/lhs/lhs_samples.npy \\
      --out-dir stl_samples/stl
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import warnings
from typing import List, Dict, Any

import numpy as np

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

warnings.filterwarnings('ignore')

DEFAULT_LHS = os.path.join(_REPO_ROOT, 'stl_samples', 'lhs', 'lhs_samples.npy')
DEFAULT_OUT = os.path.join(_REPO_ROOT, 'stl_samples', 'stl')


def load_lhs_npy(path: str) -> np.ndarray:
    if not os.path.exists(path):
        raise FileNotFoundError(f"LHS samples not found: {path}. Run cst_lhs.py first.")
    arr = np.load(path)
    assert arr.ndim == 2 and arr.shape[1] == 12, (
        f"expected (N, 12), got {arr.shape}")
    return arr


def build_stl(coeffs: np.ndarray) -> 'trimesh.Trimesh':
    from build_r37_from_cst import build_watertight_stl
    return build_watertight_stl(coeffs)


def verify_stl(mesh) -> Dict[str, Any]:
    return {
        'n_vertices': int(len(mesh.vertices)),
        'n_faces': int(len(mesh.faces)),
        'is_watertight': bool(mesh.is_watertight),
        'is_winding_consistent': bool(mesh.is_winding_consistent),
        'volume_m3': float(mesh.volume) if mesh.is_watertight else float('nan'),
        'bounds_min': mesh.bounds[0].tolist(),
        'bounds_max': mesh.bounds[1].tolist(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--n', type=int, default=100, help='Number of STLs to generate (default 100)')
    parser.add_argument('--lhs', default=DEFAULT_LHS, help='LHS .npy file')
    parser.add_argument('--out-dir', default=DEFAULT_OUT, help='Output directory')
    parser.add_argument('--prefix', default='r37_lhs_', help='STL filename prefix')
    parser.add_argument('--quiet', action='store_true', help='Only print summary at end')
    args = parser.parse_args()

    samples = load_lhs_npy(args.lhs)
    if args.n > len(samples):
        raise ValueError(f"--n {args.n} > LHS samples available {len(samples)}. "
                         f"Re-run cst_lhs.py with --n {args.n}")
    samples = samples[:args.n]

    os.makedirs(args.out_dir, exist_ok=True)

    manifest: List[Dict[str, Any]] = []
    n_watertight = 0
    n_failed = 0
    t0 = time.time()
    for i, coeffs in enumerate(samples):
        stl_path = os.path.join(args.out_dir, f'{args.prefix}{i:04d}.stl')
        try:
            mesh = build_stl(coeffs)
            info = verify_stl(mesh)
            info['sample_index'] = int(i)
            info['cst_coefficients'] = coeffs.tolist()
            info['stl_path'] = stl_path
            info['stl_size_bytes'] = 0  # will set after export
            mesh.export(stl_path)
            info['stl_size_bytes'] = os.path.getsize(stl_path)
            if info['is_watertight']:
                n_watertight += 1
            else:
                n_failed += 1
            manifest.append(info)
        except Exception as e:
            n_failed += 1
            manifest.append({
                'sample_index': int(i),
                'cst_coefficients': coeffs.tolist(),
                'stl_path': stl_path,
                'error': str(e),
                'is_watertight': False,
            })
        if not args.quiet and (i + 1) % 10 == 0:
            elapsed = time.time() - t0
            print(f'  [{i+1:3d}/{args.n}] watertight: {n_watertight}, '
                  f'failed: {n_failed}, elapsed: {elapsed:.1f}s')

    elapsed = time.time() - t0

    # Manifest CSV
    csv_path = os.path.join(args.out_dir, 'manifest.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['sample_index', 'is_watertight', 'n_faces', 'volume_m3',
                         'stl_size_bytes', 'stl_path'])
        for m in manifest:
            writer.writerow([
                m.get('sample_index', -1),
                m.get('is_watertight', False),
                m.get('n_faces', ''),
                m.get('volume_m3', ''),
                m.get('stl_size_bytes', ''),
                m.get('stl_path', ''),
            ])

    # Manifest JSON (rich)
    json_path = os.path.join(args.out_dir, 'manifest.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'method': 'CST -> trimesh.extrude_polygon -> STL',
            'n_requested': args.n,
            'n_watertight': n_watertight,
            'n_failed': n_failed,
            'elapsed_s': round(elapsed, 2),
            'rate_stl_per_s': round(args.n / max(elapsed, 1e-9), 2),
            'lhs_source': args.lhs,
            'samples': manifest,
        }, f, indent=2)

    print(f'\n{"=" * 60}')
    print(f'M3 STL batch complete: {args.n} samples in {elapsed:.1f}s '
          f'({args.n / max(elapsed, 1e-9):.1f} STLs/s)')
    print(f'  watertight: {n_watertight}/{args.n} ({100 * n_watertight / args.n:.1f}%)')
    print(f'  failed:     {n_failed}/{args.n}')
    print(f'  manifest.csv: {csv_path}')
    print(f'  manifest.json: {json_path}')
    print(f'{"=" * 60}')

    if n_watertight < args.n:
        print(f'\nWARNING: {args.n - n_watertight} STLs failed watertightness.')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
