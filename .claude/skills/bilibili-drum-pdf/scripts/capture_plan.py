"""按 plan.json 逐个调用上游 capture，写出 caps.json: [{"id", "off", "seconds"}]。

用法: capture_plan.py <cv.sh> <task> plan.json caps.json
      capture_plan.py <cv.sh> <task> --add 秒数 caps.json    补采一张，追加到 caps.json（偏移由 rows.py 实测校正，先填附近截图的）
"""
import json, os, subprocess, sys, tempfile

cv, task, plan, out = sys.argv[1:5]
if plan == '--add':
    t = float(out); out = sys.argv[5]; caps = json.load(open(out))
    pl = json.load(open(os.path.join(os.path.dirname(os.path.abspath(out)), 'plan.json')))
    todo = [(max((o for o, s in pl if s <= t), default=0), t)]
else:
    caps = []; todo = json.load(open(plan))
for off, t in todo:
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump({'seconds': t}, f)
    r = json.loads(subprocess.check_output([cv, '--operation', 'capture', '--task', task, '--request', f.name]))
    c = r.get('capture', r)
    caps.append({'id': c['id'], 'off': off, 'seconds': t})
    print(c['id'], t, off)
json.dump(caps, open(out, 'w'))
