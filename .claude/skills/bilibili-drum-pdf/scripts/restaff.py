"""给已导出的矢量 PDF 补画五线：上游每个 region 只修补声明的那一组五线，
合并成一个 region 的多行谱里其余各组的细线会在轮廓转描中丢失。

本脚本在每个 system 原裁剪里找出全部五线组，把未被上游修补的组按原位置、原长度画回 PDF。
用法: restaff.py <task> out.pdf [--all --width 0.6]     （读取 task/record.json 当前 output）
  --all 连上游已修补的那组也重画，配合 --width（单位 pt）加粗：上游五线只有约 0.3pt，手机缩小看会断续。
不改任务记录；输出是另一个文件，交付时用它。
"""
import io, json, sys
import numpy as np
from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen.canvas import Canvas

task, out = sys.argv[1:3]
ALL = '--all' in sys.argv
WIDTH = float(sys.argv[sys.argv.index('--width') + 1]) if '--width' in sys.argv else None
rec = json.load(open(f'{task}/record.json'))
o = rec['output']
mats = json.load(open(f"{task}/{o['pdf'].rsplit('/', 1)[0]}/materials.json"))['blocks']


def line_center(gray, W, H, y, fallback):
    """一条五线的竖直中心（浮点，转描坐标里像素行 k 的中心就是 k）：取 ±2 行内各行横向中位灰度，
    减去附近空白行的底色后按墨色加权平均。"""
    c = int(round(y))
    med = lambda k: float(np.median(gray[k, int(W * .1):int(W * .9)]))
    bg = float(np.median([med(k) for k in range(max(0, c - 6), min(H, c + 7)) if abs(k - c) > 3]))
    rows = list(range(max(0, c - 2), min(H, c + 3)))
    w = [bg - med(k) if bg - med(k) > 15 else 0.0 for k in rows]
    return sum(k * v for k, v in zip(rows, w)) / sum(w) if sum(w) else fallback


def staves(gray, sp):
    """按已知线距做五线模板匹配：y + i*sp (i=0..4) 五处都是长横线才算一组（密集符梁不会同时满足）。"""
    W, H = gray.shape[1], gray.shape[0]
    dark = gray < 215
    cnt = dark.sum(1)
    near = lambda y: max(cnt[max(0, y - 1):min(H, y + 2)])
    score = [min(near(int(round(y + i * sp))) for i in range(5)) if y + 4 * sp < H - 1 else 0 for y in range(H)]
    found = []
    for y in sorted(range(H), key=lambda y: -score[y]):
        if score[y] < W * .25: break
        if all(abs(y - f) > 4 * sp for f in found): found.append(y)
    out = []
    for y0 in sorted(found):
        g = []
        for i in range(5):   # 每条线取 ±1px 内墨迹最多的那一行
            c = int(round(y0 + i * sp)); g.append(max(range(max(0, c - 1), min(H, c + 2)), key=lambda y: cnt[y]))
        spans = []
        for y in g:
            xs = np.where(dark[int(round(y))])[0]
            # 最长的连续段（允许 40px 内的断口，如符头遮挡）
            best, s = (0, 0), xs[0]
            for a, b in zip(xs, list(xs[1:]) + [10 ** 9]):
                if b - a > 40:
                    if a - s > best[1] - best[0]: best = (s, a)
                    s = b
            spans.append(best)
        # 画线位置改用墨色加权中心：gray<215 的计数在抗锯齿的相邻行上常和真线并列，max 取到最上面那行，
        # 粗线就偏上约 1px，和转描里的线错开，转描出的半行残段（如第 21 小节第二线）露在下面显得变粗。
        g = [line_center(gray, W, H, y0 + i * sp, g[i]) for i in range(5)]
        out.append((g, min(s[0] for s in spans), max(s[1] for s in spans)))
    return out


reader = PdfReader(f"{task}/{o['pdf']}")
pw, ph = float(reader.pages[0].mediabox.width), float(reader.pages[0].mediabox.height)
overlays = {}
added = 0
for p in o['placements']:
    b = mats[p['region']]
    if b['kind'] != 'system': continue
    gray = np.asarray(Image.open(f"{task}/{b['path']}").convert('L')).astype(int)
    x0, _, _, ytop = p['bbox']; s = p['scale']
    for g, xa, xb in staves(gray, b['staff_spacing']):
        if not ALL and abs(g[0] - b['staff_top']) < b['staff_spacing']: continue   # 上游已修补
        c = overlays.setdefault(p['page'], [])
        c.extend((x0 + xa * s, ytop - y * s, x0 + xb * s) for y in g)
        added += 1
w = PdfWriter()
for i, page in enumerate(reader.pages, 1):
    if i in overlays:
        buf = io.BytesIO(); c = Canvas(buf, pagesize=(pw, ph)); c.setLineWidth(WIDTH or 1.1 * o['placements'][0]['scale'])
        for xa, y, xb in overlays[i]: c.line(xa, y, xb, y)
        c.save(); buf.seek(0)
        page.merge_page(PdfReader(buf).pages[0])
    w.add_page(page)
w.write(out)
print(f'补画 {added} 组五线 -> {out}')
