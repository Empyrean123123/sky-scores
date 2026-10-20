"""assemble 之后的收尾：无生图工具时转矢量、排版导出、提交最终审阅。

  finish.py <cv.sh> <task> vector                 所有待生图组登记 unavailable，转轮廓矢量
  finish.py <cv.sh> <task> export [--margin 24] [--gap 6]
                                                  设布局、导出，打印每页包含哪些谱行和预览路径
  finish.py <cv.sh> <task> review --notes "..."   实际看完全部预览后提交 review-pdf
  finish.py <cv.sh> <task> deliver --name xxx-drums.pdf
                                                  补画合并块的五线（restaff.py），输出到 task 旁的 out/
"""
import argparse, json, os, re, subprocess, tempfile

ap = argparse.ArgumentParser()
ap.add_argument('cv'); ap.add_argument('task'); ap.add_argument('step', choices=['vector', 'export', 'review', 'deliver'])
ap.add_argument('--margin', type=float, default=24); ap.add_argument('--gap', type=float, default=6)
ap.add_argument('--notes'); ap.add_argument('--name')
ap.add_argument('--thick', action='store_true', help='deliver 时所有五线重画成 0.6pt（屏幕上看更清楚）')
a = ap.parse_args()


def call(op, req=None):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(req or {}, f, ensure_ascii=False)
    r = subprocess.run([a.cv, '--operation', op, '--task', a.task, '--request', f.name], capture_output=True, text=True)
    d = json.loads(r.stdout or '{}')
    if r.returncode:
        detail = ''
        if op in ('stage', 'export') and d.get('error', {}).get('code') in ('invalid_state', 'internal_error'):
            # CLI 只给通用错误码；直接调上游函数拿真正的异常信息（例如"五线边界不可确认"）
            sk = re.search(r'cd "([^"]+)"', open(a.cv).read()).group(1)
            t = subprocess.run(['uv', 'run', '--python', '3.12', '--quiet', '--isolated', '--with-requirements',
                                'scripts/requirements.txt', 'python', '-c',
                                f'import sys; sys.path.insert(0, "scripts"); import score_workflow as w; w.{op}({os.path.abspath(a.task)!r})'],
                               cwd=sk, capture_output=True, text=True)
            detail = '\n上游异常: ' + (t.stderr.strip().splitlines() or ['(无)'])[-1]
        raise SystemExit(f'{op} 失败: {d.get("error", r.stderr[-500:])}{detail}')
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
elif a.step == 'deliver':
    if not a.name: raise SystemExit('--name 必填：纯英文文件名')
    out = os.path.join(os.path.dirname(os.path.abspath(a.task)), 'out'); os.makedirs(out, exist_ok=True)
    dst = os.path.join(out, a.name)
    subprocess.run(['uv', 'run', '--quiet', '--with', 'numpy', '--with', 'pillow', '--with', 'pypdf', '--with', 'reportlab',
                    'python', os.path.join(os.path.dirname(__file__), 'restaff.py'), a.task, dst]
                   + (['--all', '--width', '0.6'] if a.thick else []), check=True)
    print('交付文件:', dst)
else:
    if not a.notes: raise SystemExit('--notes 必填：写实际看图结果')
    n = call('stage')['next']
    call('review-pdf', {'pages': n['pages'], 'output_revision': n['output_revision'], 'notes': a.notes})
    print(call('stage')['phase'])
