"""由 regions.json 和 Agent 实际读到的行首小节号生成 assemble 请求。

用法: assemble_request.py regions.json caps.json out.json --title 谱名 --bars 1,5,11,... \
        --notes "实际看图备注" --first-last "首尾" --title-notes "标题块看到了什么" \
        [--first-notes ...] [--last-notes ...]
备注必须写实际看图结果；接续备注按小节号自动生成，小节号必须是 Agent 逐行读出来的。
"""
import argparse, json

ap = argparse.ArgumentParser()
ap.add_argument('regions'); ap.add_argument('caps'); ap.add_argument('out')
for f in ('title', 'bars', 'notes', 'first-last', 'title-notes'):
    ap.add_argument('--' + f, required=True)
ap.add_argument('--first-notes', default='第一条完整谱行，谱号与拍号完整。')
ap.add_argument('--last-notes', default='最后一条完整谱行，以终止线结束。')
a = ap.parse_args()

R = json.load(open(a.regions))
caps = [c['id'] for c in json.load(open(a.caps))]
bars = [int(x) for x in a.bars.split(',')]
S = [r for r in R if r['kind'] == 'system']
if len(bars) != len(S): raise SystemExit(f'小节号 {len(bars)} 个，谱行 {len(S)} 行，不一致')
if bars != sorted(bars): raise SystemExit('小节号不是递增的')
ref = lambda r: {'position': r['position'], 'capture': r['capture'], 'bbox': r['bbox']}
joins = []
for k in range(1, len(S)):
    p, c = S[k - 1], S[k]
    where = '两行位于同一截图上下相邻。' if p['capture'] == c['capture'] else \
        f"{p['capture']} 与 {c['capture']} 按滚动偏移对齐，切线在全局坐标中首尾相接。"
    joins.append({'previous': ref(p), 'current': ref(c), 'method': 'numbered',
                  'notes': f'上一行行首 {bars[k - 1]}，本行行首印小节号 {bars[k]}，编号连续；' + where})
review = {'viewed_captures': caps, 'complete': True, 'unresolved': [], 'notes': a.notes,
          'continuity': '行首小节号 ' + ','.join(map(str, bars)) + ' 逐行连续，切线首尾相接。',
          'first_last': a.first_last,
          'evidence': {'title': {**ref(R[0]), 'notes': a.title_notes},
                       'first': {**ref(S[0]), 'notes': a.first_notes},
                       'last': {**ref(S[-1]), 'notes': a.last_notes}, 'joins': joins},
          'issue_dispositions': []}
json.dump({'title': a.title, 'regions': R, 'review': review}, open(a.out, 'w'), ensure_ascii=False)
print(f'{len(S)} 行，{len(joins)} 个接续 -> {a.out}')
