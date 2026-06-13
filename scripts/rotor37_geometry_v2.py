"""
Rotor 37 1-passage WATERTIGHT 3D STL generator v2.
Fixes the topology bug in v1: 6-face manifold (2 end caps + 4 spanwise walls).
"""
import math
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
import rotor37_geometry as rg

EXTRUDE_M = 0.020

sections = []
for r, chord, stagger in zip(rg.spans, rg.chords, rg.staggers):
    af = rg.airfoil_points(chord, rg.CAMBER_DEG, rg.MAX_THICKNESS_PCT, rg.N_CHORD_PTS, rg.LE_RADIUS_M, rg.TE_THICKNESS_M)
    sections.append((r, stagger, af))

n_sec = len(sections)
n_pt = len(sections[0][2])

grid = []
for r, stagger, af in sections:
    stagger_rad = stagger * math.pi / 180.0
    row = []
    for x_chord, y_thick in af:
        x_r = x_chord * math.cos(stagger_rad) - y_thick * math.sin(stagger_rad)
        y_r = x_chord * math.sin(stagger_rad) + y_thick * math.cos(stagger_rad)
        row.append((x_r, y_r + r, 0.0))
    grid.append(row)
grid_top = []
for r, stagger, af in sections:
    stagger_rad = stagger * math.pi / 180.0
    row = []
    for x_chord, y_thick in af:
        x_r = x_chord * math.cos(stagger_rad) - y_thick * math.sin(stagger_rad)
        y_r = x_chord * math.sin(stagger_rad) + y_thick * math.cos(stagger_rad)
        row.append((x_r, y_r + r, EXTRUDE_M))
    grid_top.append(row)

triangles = []
def add_tri(p0, p1, p2):
    triangles.append((p0, p1, p2))

# Face 1: Hub end cap (z=0), fan from centroid, outward -z
hub_pts = grid[0]
cx = sum(p[0] for p in hub_pts) / n_pt
cy = sum(p[1] for p in hub_pts) / n_pt
hub_c = (cx, cy, 0.0)
for i in range(n_pt):
    add_tri(hub_c, hub_pts[(i + 1) % n_pt], hub_pts[i])

# Face 2: Tip end cap (z=EXTRUDE), fan from centroid, outward +z
tip_pts = grid_top[-1]
cx = sum(p[0] for p in tip_pts) / n_pt
cy = sum(p[1] for p in tip_pts) / n_pt
tip_c = (cx, cy, EXTRUDE_M)
for i in range(n_pt):
    add_tri(tip_c, tip_pts[i], tip_pts[(i + 1) % n_pt])

# Faces 3-6: 4 spanwise walls (LE, TE, suction, pressure)
def build_strip_wall(pt_idx):
    for i in range(n_sec - 1):
        v0_bot = grid[i][pt_idx]
        v1_bot = grid[i+1][pt_idx]
        v0_top = grid_top[i][pt_idx]
        v1_top = grid_top[i+1][pt_idx]
        add_tri(v0_bot, v1_bot, v1_top)
        add_tri(v0_bot, v1_top, v0_top)

build_strip_wall(0)     # LE wall
build_strip_wall(20)    # TE wall

def build_curved_wall(pt_range):
    for i in pt_range:
        for s in range(n_sec - 1):
            v0_bot = grid[s][i]
            v1_bot = grid[s+1][i]
            v0_top = grid_top[s][i]
            v1_top = grid_top[s+1][i]
            add_tri(v0_bot, v1_bot, v1_top)
            add_tri(v0_bot, v1_top, v0_top)

build_curved_wall(range(1, 20))    # suction wall
build_curved_wall(range(21, 40))   # pressure wall

print(f'Triangles: {len(triangles)}')

# Write binary STL with proper null bytes
out = os.path.join(os.path.dirname(__file__), 'rotor37_1passage_3d_v2.stl')
null_byte = bytes([0])
with open(out, 'wb') as f:
    header = b'Rotor37 watertight 1-passage 3D solid v2, 36 blades  '
    f.write(header.ljust(80, null_byte))
    f.write(struct.pack('<I', len(triangles)))
    for p0, p1, p2 in triangles:
        v1 = (p1[0]-p0[0], p1[1]-p0[1], p1[2]-p0[2])
        v2 = (p2[0]-p0[0], p2[1]-p0[1], p2[2]-p0[2])
        nx = v1[1]*v2[2] - v1[2]*v2[1]
        ny = v1[2]*v2[0] - v1[0]*v2[2]
        nz = v1[0]*v2[1] - v1[1]*v2[0]
        mag = math.sqrt(nx*nx + ny*ny + nz*nz) or 1.0
        nx, ny, nz = nx/mag, ny/mag, nz/mag
        f.write(struct.pack('<12f', nx, ny, nz, p0[0], p0[1], p0[2], p1[0], p1[1], p1[2], p2[0], p2[1], p2[2]))
        f.write(null_byte * 2)

print(f'Wrote: {out} ({os.path.getsize(out)} bytes, expected {84 + len(triangles) * 50})')

# Verify
import trimesh
m = trimesh.load(out, file_type='stl')
print(f'is_watertight: {m.is_watertight}')
print(f'volume: {m.volume*1e6:.4f} cm^3')
print(f'triangles: {len(m.faces)}')
