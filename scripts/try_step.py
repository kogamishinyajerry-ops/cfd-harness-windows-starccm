"""Try direct STEP generation via CadQuery from airfoil outline."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import warnings
warnings.filterwarnings('ignore')
import rotor37_geometry as rg
import cadquery as cq
from cadquery import exporters

# Use CadQuery's Workplane to build the airfoil as a closed polygon + extrude
af_hub = rg.airfoil_points(rg.CHORD_HUB_M, rg.CAMBER_DEG, rg.MAX_THICKNESS_PCT, rg.N_CHORD_PTS, rg.LE_RADIUS_M, rg.TE_THICKNESS_M)

# Reverse if CW
s = 0
for i in range(len(af_hub)):
    x1, y1 = af_hub[i]
    x2, y2 = af_hub[(i+1) % len(af_hub)]
    s += (x2 - x1) * (y2 + y1)
if s > 0:
    af_hub = list(reversed(af_hub))

# Build a closed polygon via Workplane
wp = cq.Workplane("XY")
# Add all the points as a polyline
pts = [(p[0], p[1]) for p in af_hub]
# Use polyline to connect them, then close
wp = wp.polyline(pts).close()
# Extrude
EXTRUDE_M = 0.020
result = wp.extrude(EXTRUDE_M)
print(f'CadQuery shape: type={type(result.val()).__name__}')
print(f'  bounding box: {result.val().BoundingBox()}')
# Translate to (0, hub_radius, 0)
result = result.translate((0, rg.HUB_RADIUS_M, 0))
# Export as STEP
out_step = 'scripts/rotor37_extruded.step'
exporters.export(result, out_step)
print(f'STEP: {os.path.getsize(out_step)} bytes')
