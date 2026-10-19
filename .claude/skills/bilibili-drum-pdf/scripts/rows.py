"""从截图里找出所有谱行，给每行选来源截图，并在全局滚动坐标里放共用切线。

用法: rows.py <task> caps.json out_dir [--wm x0,y0,x1,y1] [--header-top Y]
输出 out_dir/regions.json（assemble 用的 regions）、rows_report.json、strip_N.png（给 Agent 看图）。
切线只放在无墨迹的空白行；某个行间隙找不到空白行时报告 contested，需要人工决定。
"""
import argparse, json
import numpy as np
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument('task'); ap.add_argument('caps'); ap.add_argument('out')
ap.add_argument('--wm', help='水印框 x0,y0,x1,y1（像素）；默认右上角 30%%宽 x 11%%高')
ap.add_argument('--header-top', type=int)
ap.add_argument('--per-strip', type=int, default=6)
a = ap.parse_args()

caps = json.load(open(a.caps))
rgb = {c['id']: np.asarray(Image.open(f"{a.task}/captures/{c['id']}.png").convert('RGB')).astype(int) for c in caps}
H, W = next(iter(rgb.values())).shape[:2]
gray = {k: v.mean(2) for k, v in rgb.items()}
ink = {k: (g < 180).sum(1) for k, g in gray.items()}          # 每行墨迹像素数（全宽）
wm = [int(v) for v in a.wm.split(',')] if a.wm else [int(W * .7), 0, W, int(H * .11)]


def staffs(cid):
    cnt = (gray[cid][:, int(W * .03):int(W * .97)] < 160).sum(1)
    ys = np.where(cnt > W * .55)[0]
    lines = []
    for y in ys:
        if lines and y - lines[-1][-1] <= 1: lines[-1].append(y)
        else: lines.append([y])
    lc = [sum(l) / len(l) for l in lines]
    out, j = [], 0
    while j < len(lc):
        g = [lc[j]]
        while j + 1 < len(lc) and lc[j + 1] - g[-1] < 25: j += 1; g.append(lc[j])
        if len(g) == 5 and g[0] > 2 and g[-1] < H - 3: out.append((g[0], g[-1]))
        j += 1
    return out


loc = {c['id']: staffs(c['id']) for c in caps}
off = {c['id']: float(c['off']) for c in caps}
for _ in range(2):   # 聚类后用各截图的实测位置修正偏移（滚动测量有 ±2px 误差）
    pts = sorted((t + off[c], c, t) for c in loc for t, _ in loc[c])
    clusters = []
    for y, c, t in pts:
        if clusters and y - clusters[-1][-1][0] < 30: clusters[-1].append((y, c, t))
        else: clusters.append([(y, c, t)])
    tops = [np.mean([p[0] for p in cl]) for cl in clusters]
    for c in loc:
        d = [tops[i] - (t + off[c]) for i, cl in enumerate(clusters) for (_, cc, t) in cl if cc == c]
        if d: off[c] += float(np.median(d))
tops = [float(np.mean([p[0] for p in cl])) for cl in clusters]
h = float(np.median([b - t for c in loc for t, b in loc[c]]))
gap = float(np.median(np.diff(tops))) - h if len(tops) > 1 else h * 2
print(f'{len(tops)} 行, 五线高 {h:.0f}px, 行间空隙 {gap:.0f}px')


def sees(c, y0, y1): return y0 - off[c] >= 0 and y1 - off[c] <= H


rows = []
for k, gy in enumerate(tops):
    best = None
    for c in rgb:
        ly = gy - off[c]
        if ly - gap * .6 < 0 or ly + h + gap * .6 > H: continue
        b = rgb[c][int(ly - gap * .6):int(ly + h + gap * .6)]
        blue = int((((b[:, :, 2] - b[:, :, 0]) > 40) & (b[:, :, 2] > 150)).sum())
        hit_wm = ly - gap * .8 < wm[3] and ly + h + gap * .6 > wm[1]
        score = hit_wm * 10 + (blue > 200) * 3 + abs(ly + h / 2 - H / 2) / H
        if best is None or score < best[0]: best = (score, c, blue, hit_wm)
    if best is None: raise SystemExit(f'第 {k + 1} 行（全局 y={gy:.0f}）没有完整截图，补采后重跑')
    rows.append({'cap': best[1], 'blue': best[2], 'watermark': bool(best[3])})


def cut_in(c, y0, y1):
    """截图 c 中 [y0,y1) 全局区间内最长空白段的中点；没有空白时返回 (最少墨迹行, False)。"""
    l0, l1 = int(round(y0 - off[c])), int(round(y1 - off[c]))
    seg = ink[c][l0:l1]
    best, run = None, None
    for i, v in enumerate(list(seg) + [1]):
        if v == 0 and run is None: run = i
        if v != 0 and run is not None:
            if best is None or i - run > best[1] - best[0]: best = (run, i)
            run = None
    if best: return l0 + (best[0] + best[1]) // 2 + off[c], True
    return l0 + int(np.argmin(seg)) + off[c], False


cuts, contested = [], []
first = rows[0]['cap']
for k in range(len(tops) + 1):
    if k == 0:
        lo, hi = tops[0] - gap, tops[0] - 3
        cands = [first]
    elif k == len(tops):
        lo, hi = tops[-1] + h + 3, min(tops[-1] + h + gap, off[rows[-1]['cap']] + H - 1)
        cands = [rows[-1]['cap']]
    else:
        lo, hi = tops[k - 1] + h + 3, tops[k] - 3
        cands = [rows[k - 1]['cap'], rows[k]['cap']] + list(rgb)
    c = next(c for c in cands if sees(c, lo, hi))
    y, clean = cut_in(c, max(lo, off[c]), hi)
    cuts.append(y)
    if not clean: contested.append(k)


def clean_line(c, y):
    """在本截图里确认切线无墨迹；偏移误差导致压线时在 ±4px 内挪到空白行。"""
    ly = int(round(y - off[c]))
    for d in [0, -1, 1, -2, 2, -3, 3, -4, 4]:
        if 0 <= ly + d < H and ink[c][ly + d] == 0: return ly + d
    return ly


regions = []
hc = first
top0 = a.header_top
if top0 is None:
    g = gray[hc].copy(); g[wm[1]:wm[3], wm[0]:wm[2]] = 255
    rows_ink = np.where((g < 180).sum(1)[:clean_line(hc, cuts[0])] > 0)[0]
    top0 = max(0, int(rows_ink[0]) - 20) if len(rows_ink) else 0
regions.append({'position': 'header', 'capture': hc, 'bbox': [0, top0, W, clean_line(hc, cuts[0])], 'kind': 'header'})
for k, r in enumerate(rows):
    c = r['cap']; t = clean_line(c, cuts[k]); b = clean_line(c, cuts[k + 1])
    # 矢量转描在 staff_top + i*staff_spacing ±2px 处找五线，用本截图实测的首末线位置（保留小数）
    s0, s4 = min(loc[c], key=lambda s: abs(s[0] - (tops[k] - off[c])))
    regions.append({'position': f'row-{k + 1:02d}', 'capture': c, 'bbox': [0, t, W, b], 'kind': 'system',
                    'staff_top': round(s0 - t, 2), 'staff_spacing': round((s4 - s0) / 4, 2)})

json.dump(regions, open(f'{a.out}/regions.json', 'w'), ensure_ascii=False, indent=0)
rep = {'rows': len(rows), 'offsets': off, 'contested_gaps': contested,
       'with_blue': [k + 1 for k, r in enumerate(rows) if r['blue'] > 200],
       'with_watermark': [k + 1 for k, r in enumerate(rows) if r['watermark']],
       'sources': [r['cap'] for r in rows]}
json.dump(rep, open(f'{a.out}/rows_report.json', 'w'), ensure_ascii=False, indent=1)
print('来源:', rep['sources'])
print('含播放高亮的行:', rep['with_blue'], ' 可能被水印遮挡的行:', rep['with_watermark'])
if contested: print('找不到空白切线的行间隙（k 表示第 k 行与第 k+1 行之间，0=标题之下）:', contested)

n = a.per_strip
for p in range(0, len(regions), n):
    ims = []
    for r in regions[p:p + n]:
        im = Image.fromarray(rgb[r['capture']].astype(np.uint8)).crop(r['bbox'])
        d = ImageDraw.Draw(im); d.rectangle([0, 0, im.width - 1, im.height - 1], outline=(255, 0, 0))
        d.text((W - 90, 4), r['position'], fill=(255, 0, 0)); ims.append(im)
    S = Image.new('RGB', (W, sum(i.height for i in ims)), 'white'); y = 0
    for i in ims: S.paste(i, (0, y)); y += i.height
    S.save(f'{a.out}/strip_{p // n + 1}.png')
print(f'看图: {a.out}/strip_*.png')
