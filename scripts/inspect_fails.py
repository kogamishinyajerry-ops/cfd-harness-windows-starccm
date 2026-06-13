import json
with open(r'stl_samples\stl\manifest.json', encoding='utf-8') as f:
    d = json.load(f)
print('n_watertight:', d['n_watertight'], '/', d['n_requested'])
print('failed samples:')
for s in d['samples']:
    if not s.get('is_watertight', False):
        idx = s['sample_index']
        coeffs = s['cst_coefficients']
        print(f'  idx={idx} coeffs={coeffs}')
        if 'error' in s:
            print(f'    error: {s["error"]}')
