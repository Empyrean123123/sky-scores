"""测量上滚鼓谱视频每一时刻的累计滚动量，挑出静止且相互重叠的截图时间点。

用法: scroll_plan.py video.mp4 out_plan.json [--fps 2] [--max-step 600]
输出 [[累计偏移px, 秒], ...]。相邻两点偏移不超过 max-step，保证截图之间有整行重叠。
"""
import argparse, json, subprocess
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('video'); ap.add_argument('out')
ap.add_argument('--fps', type=float, default=2)
ap.add_argument('--max-step', type=int, default=600)
a = ap.parse_args()

probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                            'stream=width,height', '-of', 'json', a.video]))['streams'][0]
W, H = probe['width'], probe['height']
raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', a.video, '-vf', f'fps={a.fps},format=gray',
                               '-f', 'rawvideo', '-'])
frames = np.frombuffer(raw, np.uint8).reshape(-1, H, W)
x0, x1, m = int(W * .04), int(W * .96), int(H * .09)   # 去掉左右边和顶部水印带
prof = [(f[:, x0:x1] < 120).sum(1).astype(np.float32) for f in frames]

offs, tot, bad, moved = [0], 0, [], [False]
for i in range(1, len(prof)):
    p0, p1 = prof[i - 1], prof[i]
    if np.abs(p0[m:H - m] - p1[m:H - m]).mean() < 1:      # 画面没动（高亮移动不算）
        offs.append(tot); moved.append(False); continue
    # 至少留 150px 重叠，否则重叠太短时误差趋近 0，会被误判成大跳
    errs = [np.abs(p0[s + m:H - m] - p1[m:H - m - s]).mean() for s in range(1, H - 2 * m - 150)]
    s = int(np.argmin(errs)) + 1
    if errs[s - 1] > 5 and errs[s - 1] > 0.5 * np.mean(prof[i]):
        bad.append(round(i / a.fps, 2))   # 不是平移（翻页/跳转/转场），需要人工看
    tot += s; offs.append(tot); moved.append(True)

segs = []   # (偏移, 起, 止) 静止段：连续未变化的帧
for i, o in enumerate(offs):
    if segs and not moved[i]: segs[-1][2] = i
    else: segs.append([o, i, i])
mid = [(o, round((b + c) / 2 / a.fps, 2)) for o, b, c in segs]
pick = [mid[0]]
for i, (o, t) in enumerate(mid):
    if o - pick[-1][0] > a.max_step:
        if mid[i - 1] == pick[-1]:
            print(f'警告: {t}s 附近单步滚动 {o - pick[-1][0]}px 超过 max-step')
            pick.append(mid[i])
        else:
            pick.append(mid[i - 1])
if pick[-1] != mid[-1]: pick.append(mid[-1])
jumps = [b - a for (a, _), (b, _) in zip(mid, mid[1:]) if b - a > H * .4]
if bad or jumps:
    # 翻页式/大跳：滚动量测不准，每个停留 ≥1 秒的画面都截（重复画面由 rows.py 按内容对齐时自动合并）
    pick = [(o, round((b + c) / 2 / a.fps, 2)) for o, b, c in segs if (c - b + 1) / a.fps >= 1] or mid
    print('检测到翻页/大跳，改为每个静止画面都截；rows.py 会按谱行内容重新对齐偏移')
end_t = round((len(frames) - 1) / a.fps, 2)
if offs[-1] == pick[-1][0] and end_t - pick[-1][1] >= 1:
    pick.append((offs[-1], end_t))   # 片尾停住后的画面：最后一行通常已没有播放高亮（若片尾跳回开头，这张要删掉）
json.dump(pick, open(a.out, 'w'))
print(f'{W}x{H}, {len(frames)} 帧, 总滚动 {tot}px, 静止段 {len(segs)}, 截图 {len(pick)} 张')
print('计划:', pick)
if bad: print('非平移变化（需人工查看）:', bad[:20])
