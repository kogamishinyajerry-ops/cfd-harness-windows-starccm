import os
os.environ['STARCCM_BRIDGE_TEST_SPAWN'] = '1'
os.environ['PYTHONPATH'] = r'D:\\CFD-harness-Windows-StarCCM;D:\\CFD-harness-Windows-StarCCM\packages\starccm-bridge\src'

import sys
sys.path.insert(0, r'D:\CFD-harness-Windows-StarCCM\src')
sys.path.insert(0, r'D:\CFD-harness-Windows-StarCCM\packages\starccm-bridge\src')

from cfd_harness.starccm_adapter.executor import StarCCMExecutor
from cfd_harness.models import TaskSpec, FlowType, GeometryType

ts = TaskSpec(
    case_id='lid_driven_cavity',
    flow_type=FlowType.INTERNAL,
    geometry_type=GeometryType.SIMPLE_GRID,
    parameters={'Re': 100},
    gold_anchor='',
    solver_profile='',
    mesh_density='mesh_160',
)
print('Starting executor.execute() ...', flush=True)
ex = StarCCMExecutor(timeout_s=900)
report = ex.execute(ts)
print('status:', report.status.value, flush=True)
print('notes:', list(report.notes), flush=True)
if report.execution_result:
    print('exec.success:', report.execution_result.success, flush=True)
    print('exec.residuals:', report.execution_result.residuals, flush=True)
    print('exec.key_quantities keys:', list(report.execution_result.key_quantities.keys()), flush=True)
    kq = report.execution_result.key_quantities
    if 'u_centerline' in kq:
        print('u_centerline (first 5):', kq['u_centerline'][:5], flush=True)
    if '_macro_summary' in kq:
        print('_macro_summary:', kq['_macro_summary'], flush=True)
