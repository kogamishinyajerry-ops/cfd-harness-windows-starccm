import os
os.environ['STARCCM_BRIDGE_TEST_SPAWN'] = '1'
os.environ['LDC_ITERS'] = '100'
os.environ['PYTHONPATH'] = r'D:\\CFD-harness-Windows-StarCCM;D:\\CFD-harness-Windows-StarCCM\\packages\\starccm-bridge'

import sys
sys.path.insert(0, r'D:\CFD-harness-Windows-StarCCM\src')
sys.path.insert(0, r'D:\CFD-harness-Windows-StarCCM\packages\starccm-bridge\src')

from cfd_harness.starccm_adapter.executor import StarCCMExecutor
from cfd_harness.models import TaskSpec, FlowType, GeometryType

ts = TaskSpec(
    case_id='lid_driven_cavity',
    flow_type=FlowType.INTERNAL,
    geometry_type=GeometryType.SIMPLE_GRID,
    parameters={'Re': 100, 'boundary_conditions': {'top_wall_u': 1.0, 'other_walls_u': 0.0}},
    gold_anchor='',
    solver_profile='',
    mesh_density='mesh_160',  # maps to 200 iters via iters_map
)
ex = StarCCMExecutor(timeout_s=900)
report = ex.execute(ts)
print('status:', report.status.value)
print('notes:', list(report.notes))
if report.execution_result:
    print('execution_result.success:', report.execution_result.success)
    print('key_quantities keys:', list(report.execution_result.key_quantities.keys()))
