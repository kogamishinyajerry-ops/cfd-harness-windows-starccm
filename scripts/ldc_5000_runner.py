import os
os.environ['STARCCM_BRIDGE_TEST_SPAWN'] = '1'
os.environ['PYTHONPATH'] = r'D:\\CFD-harness-Windows-StarCCM;D:\\CFD-harness-Windows-StarCCM\packages\starccm-bridge\src'
# NO LDC_ITERS env var -> macro uses default 5000

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
    mesh_density='default',  # No iters_map hit -> use macro default (5000)
)
print('Starting LDC FULL 5000-iter executor.execute() ...', flush=True)
import time
t0 = time.time()
ex = StarCCMExecutor(timeout_s=1800)  # 30 min wall
report = ex.execute(ts)
t1 = time.time()
print('DONE in {:.1f}s wall'.format(t1-t0), flush=True)
print('status:', report.status.value, flush=True)
print('notes:', list(report.notes), flush=True)
if report.execution_result:
    print('exec.success:', report.execution_result.success, flush=True)
    kq = report.execution_result.key_quantities
    if '_macro_summary' in kq:
        print('summary:', kq['_macro_summary'], flush=True)
    if 'u_centerline' in kq:
        print('u_centerline[0:3]:', kq['u_centerline'][:3], flush=True)
    if 'csv_parse_error' in kq:
        print('csv_parse_error:', kq['csv_parse_error'], flush=True)
