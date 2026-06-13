"""Generate watertight R37 1-passage STL using trimesh.extrude_polygon.
Uses hub airfoil cross-section (constant), extruded in z = 2 cm.
This is a 2D-slice approximation: no span variation, no twist.
Watertight: YES, ready for STAR-CCM+ 2402 R8 GeometryPart import.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import warnings
warnings.filterwarnings('ignore')
import rotor37_geometry as rg
import trimesh
import trimesh.creation as trc
from shapely.geometry import Polygon

EXTRUDE_M = 0.020  # 2 cm axial thickness
af_hub = rg.airfoil_points(rg.CHORD_HUB_M, rg.CAMBER_DEG, rg.MAX_THICKNESS_PCT, rg.N_CHORD_PTS, rg.LE_RADIUS_M, rg.TE_THICKNESS_M)

# Reverse if CW (shoelace formula)
s = 0
for i in range(len(af_hub)):
    x1, y1 = af_hub[i]
    x2, y2 = af_hub[(i+1) % len(af_hub)]
    s += (x2 - x1) * (y2 + y1)
if s > 0:
    af_hub = list(reversed(af_hub))

poly = Polygon(af_hub)
print(f'Airfoil: {len(af_hub)} points, area: {poly.area*1e4:.4f} cm^2')

extruded = trc.extrude_polygon(poly, height=EXTRUDE_M)
print(f'Extruded prism: {len(extruded.vertices)} verts, {len(extruded.faces)} faces')
print(f'  watertight: {extruded.is_watertight}, volume: {extruded.volume*1e6:.4f} cm^3')
print(f'  bounds: {extruded.bounds.tolist()}')

# Translate to (hub, hub) radial position
extruded.apply_translation([0, rg.HUB_RADIUS_M, 0])
print(f'  after translation: {extruded.bounds.tolist()}')

out = 'scripts/rotor37_passage_watertight.stl'
extruded.export(out)
print(f'Saved: {out} ({os.path.getsize(out)} bytes)')
