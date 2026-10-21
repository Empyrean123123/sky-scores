"""从截图里找出所有谱行，给每行选来源截图，并在全局滚动坐标里放共用切线。

用法: rows.py <task> caps.json out_dir [--wm x0,y0,x1,y1] [--header-top Y] [--merge 3-4,10-12]
输出 out_dir/regions.json（assemble 用的 regions）、rows_report.json、strip_N.png（给 Agent 看图）。

- 切线只放在无墨迹的空白行（墨迹判定是上游 crop-checks 的超集，预检通过则门禁通过）。
- 两行记号在高度上交错、行间没有空白行时（contested），自动把这几行合并成一个 region，
  从一张能完整看到它们的截图里裁；导出后用 restaff.py 补画合并块里其余各组五线。
- --merge 手动合并（行号从 1 起），用于有空白行但记号被分到错的一行时。
"""
import argparse, json
import numpy as np
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument('task'); ap.add_argument('caps'); ap.add_argument('out')
ap.add_argument('--wm', help='水印框 x0,y0,x1,y1（像素）；默认右上角 30%%宽 x 11%%高')
ap.add_argument('--header-top', type=int)
ap.add_argument('--merge', default='', help='强制合并的行号区间，如 3-4,10-12')
ap.add_argument('--per-strip', type=int, default=6)
a = ap.parse_args()

caps = json.load(open(a.caps))
rgb = {c['id']: np.asarray(Image.open(f"{a.task}/captures/{c['id']}.png").convert('RGB')) for c in caps}   # uint8 省内存
H, W = next(iter(rgb.values())).shape[:2]
gray = {k: (v[:, :, 0] * .299 + v[:, :, 1] * .587 + v[:, :, 2] * .114).astype(np.float32) for k, v in rgb.items()}


def ink_mask(c):  # noqa
    """上游 ink_mask 是 gray<165 或高饱和深色；这里放宽到 gray<180，保证预检比门禁严。"""
    v = rgb[c]; mx, mn = v.max(2).astype(int), v.min(2).astype(int)
    return (gray[c] < 180) | (((mx - mn) > 45) & (mn < 150))


wm = [int(v) for v in a.wm.split(',')] if a.wm else [int(W * .7), 0, W, int(H * .11)]
# 谱面左右范围：五线长横线的最左/最右再放宽 40px，去掉软件界面的滚动条等常驻竖条
_m = {c: ink_mask(c) for c in rgb}
_always = np.mean([m[wm[3]:].mean(0) for m in _m.values()], 0) > .8


def _run(row):
    """一行里最长的连续墨迹段（允许 3px 断口）——五线本身，不含旁边的滚动条。"""
    xs = np.where(row)[0]
    if not len(xs): return None
    cuts_ = np.where(np.diff(xs) > 3)[0]
    st = np.r_[0, cuts_ + 1]; en = np.r_[cuts_, len(xs) - 1]
    i = int(np.argmax(xs[en] - xs[st]))
    return xs[st[i]], xs[en[i]]


_ext = [_run((gray[c] < 160)[y]) for c in rgb
        for y in np.where((gray[c][:, int(W * .03):int(W * .97)] < 160).sum(1) > W * .55)[0] if y >= wm[3]]
_ext = [e for e in _ext if e]
XL = max(0, int(min(e[0] for e in _ext)) - 40) if _ext else 0
XR = min(W, int(max(e[1] for e in _ext)) + 4) if _ext else W   # 终止线在五线末端，右侧常有滚动条，不多留
while XR > XL and _always[XR - 1]: XR -= 1
while XL < XR and _always[XL]: XL += 1
# 左边缘贴着软件的当前行标记等界面元素时，右移到第一列全空白处（不越过五线起点）
_colink = np.sum([m[wm[3]:, :].sum(0) for m in _m.values()], 0)
_x0 = int(min(e[0] for e in _ext)) if _ext else W
while XL < _x0 - 3 and _colink[XL] > 0: XL += 1
ink = {c: m[:, XL:XR].sum(1) for c, m in _m.items()}           # 每个像素行在谱面范围内的墨迹数
lines_cnt = {c: (g[:, int(W * .03):int(W * .97)] < 160).sum(1) for c, g in gray.items()}


def full_staffs(c):
    """第一遍：只认几乎通栏的五线，用来量线距。"""
    ys = np.where(lines_cnt[c] > W * .55)[0]
    ls = []
    for y in ys:
        if ls and y - ls[-1][-1] <= 1: ls[-1].append(y)
        else: ls.append([y])
    lc = [sum(l) / len(l) for l in ls]
    out, j = [], 0
    while j < len(lc):
        g = [lc[j]]
        while j + 1 < len(lc) and lc[j + 1] - g[-1] < 25: j += 1; g.append(lc[j])
        if len(g) == 5: out.append((g[-1] - g[0]) / 4)
        j += 1
    return out


sps = [s for c in rgb for s in full_staffs(c)]
if not sps: raise SystemExit('没找到任何五线；不是白底五线谱或画面太小')
SP = float(np.median(sps))


def staffs(c):
    """第二遍：按线距做五线模板匹配，半行（短行、末行）也能找到；密集符梁不会五处同时成线。"""
    cnt = lines_cnt[c]
    near = lambda y: cnt[max(0, y - 1):min(H, y + 2)].max()
    score = np.array([min(near(int(round(y + i * SP))) for i in range(5)) if y + 4 * SP < H - 2 else 0
                      for y in range(H)])
    found = []
    for y in np.argsort(-score):
        if score[y] < W * .3: break
        if all(abs(y - f) > 4 * SP for f in found): found.append(int(y))
    out = []
    for y0 in sorted(found):
        g = [max(range(max(0, r - 1), min(H, r + 2)), key=lambda y: cnt[y]) for r in
             (int(round(y0 + i * SP)) for i in range(5))]
        if g[0] > 2 and g[-1] < H - 3: out.append((g[0], g[-1]))
    return out


loc = {c['id']: staffs(c['id']) for c in caps}
order = list(dict.fromkeys(c['id'] for c in sorted(caps, key=lambda c: c['seconds'])))   # 按时间（补采的可能追加在末尾）
masks = {}
for c in order:   # 对齐时不看水印框（半透明水印压在共有行上会让差异变大）
    _mm = _m[c].copy(); _mm[wm[1]:wm[3], wm[0]:wm[2]] = False; masks[c] = _mm[:, XL:XR]


def band(c, t):
    y0 = int(round(t - 2 * SP)); y1 = y0 + int(8 * SP)
    return masks[c][max(0, y0):min(H, y1)] if y0 >= 0 and y1 <= H else None


def match(p, c):
    """按共有谱行的内容对齐相邻两张截图：返回 (c 相对 p 的滚动量, 差异率, 重叠行数)。
    五线位置有 ±1px 的取整误差，细线一错位差异就很大，所以每个候选再在 ±2px 内细调。
    重复段落的谱行像素级相同，错开整行也能匹配上；在差异达标的候选里优先选重叠行最多的。"""
    cands = []
    for a0, _ in loc[p]:
        for b0, _ in loc[c]:
            pairs = [(x, y) for x, _ in loc[p] for y, _ in loc[c] if abs(x - (y + a0 - b0)) < 3]
            best = None
            for d in range(-2, 3):
                s = a0 - b0 + d
                diffs = []
                for x, y in pairs:
                    bx, by = band(p, y + s), band(c, y)
                    if bx is not None and by is not None and bx.shape == by.shape:
                        diffs.append((bx ^ by).mean())
                if diffs and (best is None or np.mean(diffs) < best[1]):
                    best = (s, float(np.mean(diffs)), len(diffs))
            if best: cands.append(best)
    if not cands: return None
    ok = [x for x in cands if x[1] <= .06 and x[0] >= -3]   # 谱面只会往下走（片尾跳回开头的画面已从 plan 去掉）
    return max(ok, key=lambda x: (x[2], -x[1])) if ok else min(cands, key=lambda x: x[1])


off = {order[0]: 0.0}
for p, c in zip(order, order[1:]):
    m = match(p, c)
    if m is None or m[1] > .06:   # 播放光标、高亮压在共有行上时差异会到 3% 左右
        raise SystemExit(f'{p} 和 {c} 找不到内容相同的谱行（差异 {m and round(m[1], 3)}），'
                         f'两张截图之间没有重叠，在它们之间补采（capture_plan.py --add 秒数）后重跑')
    off[c] = off[p] + m[0]
pts = sorted((t + off[c], c, t) for c in loc for t, _ in loc[c])
clusters = []
for y, c, t in pts:
    if clusters and y - clusters[-1][-1][0] < 2 * SP: clusters[-1].append((y, c, t))
    else: clusters.append([(y, c, t)])
tops = [float(np.mean([p[0] for p in cl])) for cl in clusters]
h = 4 * SP
pitch = float(np.median(np.diff(tops))) if len(tops) > 1 else h * 3
gap = pitch - h
print(f'谱面横向范围 x={XL}–{XR}')
print(f'{len(tops)} 行, 线距 {SP:.2f}px, 行距 {pitch:.0f}px')
missed = [k + 1 for k in range(len(tops) - 1) if tops[k + 1] - tops[k] > pitch * 1.6]
if missed: print('警告: 这些行之后间距过大，可能漏了行（截图没覆盖到或谱面异常），先看图:', missed)


HIDE = wm[3] if wm[1] == 0 and wm[2] - wm[0] > W * .9 else 0   # 通栏工具条（软件界面）以上算看不见


def sees(c, y0, y1): return y0 - off[c] >= HIDE and y1 - off[c] <= H


def cut_in(c, y0, y1):
    """截图 c 中 [y0,y1) 全局区间内最长空白段的中点；没有空白时返回 None。"""
    l0, l1 = int(round(y0 - off[c])), int(round(y1 - off[c]))
    best, run = None, None
    for i, v in enumerate(list(ink[c][l0:l1]) + [1]):
        if v == 0 and run is None: run = i
        if v != 0 and run is not None:
            if best is None or i - run > best[1] - best[0]: best = (run, i)
            run = None
    if not best: return None
    return l0 + (best[0] + best[1]) // 2 + off[c], l0 + best[0] + off[c], l0 + best[1] - 1 + off[c]


def gap_cut(k):
    """第 k 行与第 k+1 行之间（k=0 为标题之下，k=len 为末行之下）的全局切线。"""
    if k == 0: lo, hi, need = tops[0] - pitch, tops[0] - 3, (tops[0] - 3, tops[0] + h)
    elif k == len(tops): lo, hi, need = tops[-1] + h + 3, tops[-1] + h + gap, (tops[-1], tops[-1] + h + 3)
    else: lo, hi, need = tops[k - 1] + h + 3, tops[k] - 3, (tops[k - 1] + h + 3, tops[k] - 3)
    for c in sorted(rgb, key=lambda c: abs((lo + hi) / 2 - off[c] - H / 2)):
        lo2, hi2 = max(lo, off[c] + (wm[3] if k == 0 else 0)), min(hi, off[c] + H)
        if hi2 - lo2 > 4 and sees(c, *need):
            y = cut_in(c, lo2, hi2)
            if y is not None or k not in (0, len(tops)): return y
    return None


runs = [gap_cut(k) for k in range(len(tops) + 1)]       # (切线, 空白带上沿, 空白带下沿)
if runs[0] is None or runs[-1] is None: raise SystemExit('标题下方或末行下方找不到空白切线')
cuts = [r[0] if r else None for r in runs]
force = set()
for part in filter(None, a.merge.split(',')):
    x, y = map(int, part.split('-')); force |= set(range(x, y))   # 合并第 x..y 行 = 去掉它们之间的切线
blocks, cur = [], [0]
for k in range(1, len(tops)):
    if cuts[k] is None or k in force: cur.append(k)
    else: blocks.append(cur); cur = [k]
blocks.append(cur)


for blk in blocks:
    # 翻页式视频里某行可能只在画面边缘出现：切线在各自空白带内滑动，找一张能完整看到这一块的截图
    k0, k1 = blk[0], blk[-1] + 1
    if any(sees(c, cuts[k0], cuts[k1]) for c in rgb): continue
    for c in rgb:
        t = max(cuts[k0], off[c] + HIDE); b = min(cuts[k1], off[c] + H - 1)
        if t <= runs[k0][2] and b >= runs[k1][1] and sees(c, t, b):
            cuts[k0], cuts[k1] = t, b
            break


def clean_line(c, y):
    """在本截图里确认切线无墨迹；偏移误差导致压线时在 ±4px 内挪到空白行。"""
    ly = int(round(y - off[c]))
    for d in [0, -1, 1, -2, 2, -3, 3, -4, 4]:
        if 0 <= ly + d < H and ink[c][ly + d] == 0: return ly + d
    raise SystemExit(f'{c} 第 {ly} 行附近没有空白行，切线无法落下')


regions, report = [], []
for blk in blocks:
    y0, y1 = cuts[blk[0]], cuts[blk[-1] + 1]
    best = None
    for c in rgb:
        if not sees(c, y0, y1): continue
        ly0, ly1 = y0 - off[c], y1 - off[c]
        b = rgb[c][int(ly0):int(ly1)].astype(int)
        blue = int(((((b[:, :, 2] - b[:, :, 0]) > 25) & ((b[:, :, 2] - b[:, :, 1]) > 8) & (b[:, :, 2] > 150) & (b[:, :, 0] > 150)) |   # 蓝色播放高亮（浅蓝 199,217,237 也要算）
                    (((b[:, :, 0] - b[:, :, 2]) > 20) & (b[:, :, 1] > 200) & (b[:, :, 0] > 200))).sum())   # 黄色高亮
        hit_wm = ly0 < wm[3] and ly1 > wm[1]
        score = hit_wm * 10 + min(blue / 1000, 6) + abs((ly0 + ly1) / 2 - H / 2) / H
        if best is None or score < best[0]: best = (score, c, blue, hit_wm)
    if best is None:
        need = y0 - off[min(rgb, key=lambda c: abs(off[c] - y0))]
        raise SystemExit(f'行 {blk[0] + 1}–{blk[-1] + 1}（全局 y {y0:.0f}–{y1:.0f}）没有一张截图能完整看到；'
                         f'在滚动偏移约 {y0 - 40:.0f}px 的时刻补采（capture_plan.py --add 秒数）后重跑')
    c = best[1]
    t = clean_line(c, y0); bot = clean_line(c, y1) + 1          # bbox 下边界不含，最后一行像素也要空白
    s0, s4 = min(loc[c], key=lambda s: abs(s[0] - (tops[blk[0]] - off[c])))
    regions.append({'position': f'row-{blk[0] + 1:02d}' + (f'-{blk[-1] + 1:02d}' if len(blk) > 1 else ''),
                    'capture': c, 'bbox': [XL, t, XR, bot], 'kind': 'system',
                    'staff_top': round(s0 - t, 2), 'staff_spacing': round((s4 - s0) / 4, 2)})
    report.append({'rows': [k + 1 for k in blk], 'cap': c, 'blue': best[2], 'watermark': bool(best[3])})

hc = min((c for c in order if sees(c, cuts[0] - 1, cuts[0])), key=lambda c: off[c])   # 最靠前的一张（标题在最上面）
top0 = a.header_top
hb = clean_line(hc, cuts[0])
if top0 is None:
    m = _m[hc].copy(); m[wm[1]:wm[3], wm[0]:wm[2]] = False
    rows_ink = np.where(m[:, XL:XR].sum(1)[:hb] > 0)[0]
    top0 = max(0, int(rows_ink[0]) - 20) if len(rows_ink) else 0
    while top0 > 0 and ink[hc][top0]: top0 -= 1
regions.insert(0, {'position': 'header', 'capture': hc, 'bbox': [XL, top0, XR, hb], 'kind': 'header'})

sys_r = regions[1:]


def tight(k):
    """行间可能有记号被切到错的一行：切线所在空白带很窄（两侧记号几乎相接），或这个行间比一般的高很多。"""
    ub, lt, y = tops[k - 1] + h, tops[k], cuts[k]
    c = next(c for c in sorted(rgb, key=lambda c: abs((ub + lt) / 2 - off[c] - H / 2)) if sees(c, ub, lt))
    ly = int(round(y - off[c])); u = d = 0
    while ly - u - 1 >= 0 and ink[c][ly - u - 1] == 0: u += 1
    while ly + d + 1 < H and ink[c][ly + d + 1] == 0: d += 1
    return u + d + 1 < SP * .6 or (lt - ub) > gap * 1.15


inside = {k for blk in blocks for k in blk[1:]}
odd = [f'{k}|{k + 1}' for k in range(1, len(tops)) if k not in inside and tight(k)]
json.dump(regions, open(f'{a.out}/regions.json', 'w'), ensure_ascii=False, indent=0)
rep = {'rows': len(tops), 'regions': len(sys_r), 'offsets': off, 'line_spacing': SP,
       'merged': [r['rows'] for r in report if len(r['rows']) > 1], 'maybe_missed_after': missed,
       'staff_top_outliers': odd,
       'with_blue': [r['rows'] for r in report if r['blue'] > 2500],
       'with_watermark': [r['rows'] for r in report if r['watermark']], 'sources': [r['cap'] for r in report]}
json.dump(rep, open(f'{a.out}/rows_report.json', 'w'), ensure_ascii=False, indent=1)
print('来源:', rep['sources'])
if rep['merged']: print('因行间无空白而合并的行（导出后要跑 restaff.py）:', rep['merged'])
if odd: print('这些行间的记号可能被切给了离得远的那一行，重点看图，必要时 --merge:', odd)
print('含播放高亮:', rep['with_blue'], ' 被水印遮挡:', rep['with_watermark'])

n = a.per_strip
for p in range(0, len(regions), n):
    ims = []
    for r in regions[p:p + n]:
        im = Image.fromarray(rgb[r['capture']]).crop(r['bbox'])
        d = ImageDraw.Draw(im); d.rectangle([0, 0, im.width - 1, im.height - 1], outline=(255, 0, 0))
        d.text((W - 110, 4), r['position'], fill=(255, 0, 0)); ims.append(im)
    S = Image.new('RGB', (W, sum(i.height for i in ims)), 'white'); y = 0
    for i in ims: S.paste(i, (0, y)); y += i.height
    S.save(f'{a.out}/strip_{p // n + 1}.png')
print(f'看图: {a.out}/strip_*.png')
