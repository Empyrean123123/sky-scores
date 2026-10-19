"""按 plan.json 逐个调用上游 capture，写出 caps.json: [{"id", "off", "seconds"}]。

用法: capture_plan.py <cv.sh> <task> plan.json caps.json
"""
import json, subprocess, sys, tempfile

cv, task, plan, out = sys.argv[1:5]
caps = []
for off, t in json.load(open(plan)):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump({'seconds': t}, f)
    r = json.loads(subprocess.check_output([cv, '--operation', 'capture', '--task', task, '--request', f.name]))
    c = r.get('capture', r)
    caps.append({'id': c['id'], 'off': off, 'seconds': t})
    print(c['id'], t, off)
json.dump(caps, open(out, 'w'))
