#!/usr/bin/env python3
import json, subprocess, sys

TIER_ORDER = ['ULV','LV','MV','HV','EV','IV','LuV','ZPM','UV','UHV','UEV','UIV','UMV','UXV']

def tier_rank(t):
    try: return TIER_ORDER.index(t)
    except: return -1

def max_tier_in_result(r):
    if r is None: return ''
    p = r.get('path', {})
    if p.get('type') == 'free': return ''
    best = p.get('voltage_tier', '') or ''
    for inp in p.get('inputs', []):
        sub = max_tier_in_result(inp.get('result'))
        if tier_rank(sub) > tier_rank(best): best = sub
    return best

def eu_cost(item_id):
    res = subprocess.run(['./gtnh', '--json', 'eu-cost', item_id],
        capture_output=True, text=True, cwd='/var/mnt/mercury/projects/gtnh')
    if res.returncode != 0: return None, None
    try:
        d = json.loads(res.stdout)
        if d is None: return None, None
        return d.get('eu_per_unit'), max_tier_in_result(d)
    except: return None, None

def fmt(eu):
    if eu is None: return 'N/A'
    if eu >= 1e12: return f'{eu/1e12:.2f}T EU'
    if eu >= 1e9:  return f'{eu/1e9:.2f}G EU'
    if eu >= 1e6:  return f'{eu/1e6:.2f}M EU'
    if eu >= 1e3:  return f'{eu/1e3:.1f}k EU'
    return f'{eu:.0f} EU'

if __name__ == '__main__':
    item_id = sys.argv[1]
    eu, tier = eu_cost(item_id)
    print(f'eu={fmt(eu)} tier={tier}')
