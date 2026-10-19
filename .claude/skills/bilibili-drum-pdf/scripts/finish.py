"""assemble 之后的收尾：无生图工具时转矢量、排版导出、提交最终审阅。

  finish.py <cv.sh> <task> vector                 所有待生图组登记 unavailable，转轮廓矢量
  finish.py <cv.sh> <task> export [--margin 24] [--gap 6]
                                                  设布局、导出，打印每页包含哪些谱行和预览路径
  finish.py <cv.sh> <task> review --notes "..."   实际看完全部预览后提交 review-pdf
"""
import argparse, json, os, subprocess, tempfile

ap = argparse.ArgumentParser()
ap.add_argument('cv'); ap.add_argument('task'); ap.add_argument('step', choices=['vector', 'export', 'review'])
ap.add_argument('--margin', type=float, default=24); ap.add_argument('--gap', type=float, default=6)
ap.add_argument('--notes')
a = ap.parse_args()


def call(op, req=None):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(req or {}, f, ensure_ascii=False)
    r = subprocess.run([a.cv, '--operation', op, '--task', a.task, '--request', f.name], capture_output=True, text=True)
    d = json.loads(r.stdout or '{}')
    if r.returncode: raise SystemExit(f'{op} 失败: {d.get("error", r.stderr[-500:])}')
    return d


if a.step == 'vector':
    for h in call('stage').get('handoffs', []):
        if h.get('status') in ('needs_input_review', 'needs_generation', 'ready_to_dispatch', 'prepared'):
            call('fail-redraw', {'identifier': h['group'], 'outcome': 'unavailable',
                                 'notes': '当前宿主没有图像生成/编辑工具，未发起任何调用，转轮廓矢量路线。'})
            print(h['group'], '-> vector')
    print(call('stage')['phase'])
elif a.step == 'export':
    call('layout', {'margin': a.margin, 'minimum_gap': a.gap})
    s = call('stage')
    out = s['artifacts']['output']
    pages = {}
    for p in out['placements']: pages.setdefault(p['page'], []).append(p['region'])
    print('PDF:', os.path.join(a.task, out['pdf']), f"共 {out['page_count']} 页")
    for k, v in sorted(pages.items()):
        print(f'  第 {k} 页: region {v[0]}–{v[-1]}', os.path.join(a.task, os.path.dirname(out['pdf']), f'preview-{k}.png'))
    print('几何检查:', s['checks']['status'], s['checks'].get('warnings'))
    print('output_revision:', s['next'].get('output_revision'))
else:
    if not a.notes: raise SystemExit('--notes 必填：写实际看图结果')
    n = call('stage')['next']
    call('review-pdf', {'pages': n['pages'], 'output_revision': n['output_revision'], 'notes': a.notes})
    print(call('stage')['phase'])
