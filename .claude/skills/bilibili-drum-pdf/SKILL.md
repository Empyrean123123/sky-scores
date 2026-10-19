---
name: bilibili-drum-pdf
description: 把 B站（或本地）动态鼓谱视频——白底多行谱面向上滚动的那种——整理成可打印的 A4 PDF。用户给 b23.tv / bilibili.com 鼓谱视频链接、说"动态鼓谱转 PDF"、"把这个鼓谱视频做成 PDF"时使用。和光遇琴谱无关。
---

# B站动态鼓谱视频 → A4 PDF

底层用上游 [kenqia/bilibili-drum-score-to-pdf](https://github.com/kenqia/bilibili-drum-score-to-pdf)（MIT，固定提交，`setup.sh` 自动取得）的任务记录、裁剪门禁、矢量转描和排版。本目录的脚本替代上游里要 Agent 手工做的部分：测滚动、挑截图、找谱行、放切线、填审阅证据。

**和光遇琴谱工具无关**：不要动仓库里的 `make.py` 等文件，产物放 scratchpad，不提交。

所有命令里 `$S` = 本 Skill 的 `scripts/` 绝对路径，`$W` = scratchpad 下新建的工作目录。Python 脚本用 `uv run --quiet --with numpy --with pillow python`（下面记作 `$PY`）运行。

## 流程

1. **环境**：`bash $S/setup.sh $W` —— 克隆上游到 `~/.cache/bilibili-drum-score-to-pdf`，生成 `$W/cv.sh`（上游 CLI 包装，相对路径会自动转绝对），检查 ffmpeg/ffprobe/pdftoppm/uv。需要 `prerequisites_ready = True`。

2. **下载视频**：b23.tv 短链先 `curl -sI` 取 `location` 得到 BV 号。上游匿名下载在云端常被 B站拒绝（`public_api_unavailable`），直接用 yt-dlp：
   ```bash
   mkdir -p $W/src && cd $W/src && uvx yt-dlp -F 'https://www.bilibili.com/video/BVxxxx'   # 选 1080p avc 纯视频流
   uvx yt-dlp -f 30080 -o 'v.%(ext)s' 'https://www.bilibili.com/video/BVxxxx'
   ```
   分 P 加 `?p=N`。只要画面，不要音频。

3. **准备任务**：`$W/cv.sh $W/src/v.mp4 --output $W/task --summary` → `needs_source_review`。

4. **先自己看视频**：`ffmpeg -ss 2 -i v.mp4 -frames:v 1 f.png` 抽几帧实际看。确认是白底、多行、向上滚动、行首印小节号；记下标题、作者、速度、水印位置。横向滚动、翻页式、比例变化的视频不在本流程范围（上游也不支持），告诉用户。

5. **测滚动、定截图点**：`$PY $S/scroll_plan.py $W/src/v.mp4 $W/plan.json` —— 输出总滚动量和截图计划（相邻截图偏移 ≤600px，整行重叠）。出现"非平移变化"或"单步滚动超过 max-step"时人工看那几秒。

6. **截图**：`$PY $S/capture_plan.py $W/cv.sh $W/task $W/plan.json $W/caps.json`

7. **找谱行、放切线**：`mkdir $W/rows && $PY $S/rows.py $W/task $W/caps.json $W/rows`
   - 每行从完整可见的截图里选：**优先避开水印**（水印转描后是一团垃圾），其次避开蓝色播放高亮（浅色，不影响转描），再选居中的。水印不在右上角时用 `--wm x0,y0,x1,y1` 指定。
   - 切线放在全局滚动坐标里**最长空白段的中点**，相邻两行共用同一条线，不丢不重。
   - `contested_gaps` 非空 = 两行的记号在高度上交错、找不到空白线，需要人工决定（见下面"坑"）。
   - **必须实际看 `$W/rows/strip_*.png` 每一张**：标题块完整、每行完整、没有半行、没有水印压到音符，并**逐行读出行首小节号**，核对每行小节数和下一行起始号吻合，末行有终止线。

8. **登记看图 + 粗拼**：
   ```bash
   # present：identifiers 为 caps.json 里所有 id，notes 写实际看到的内容
   $W/cv.sh --operation present --task $W/task --request present.json
   $PY $S/assemble_request.py $W/rows/regions.json $W/caps.json $W/a.json --title 谱名 \
       --bars 1,5,11,... --notes "实际看图备注" --first-last "首行…末行…" --title-notes "标题块里看到的字"
   $W/cv.sh --operation assemble --task $W/task --request $W/a.json --summary     # → ready_to_redraw
   $W/cv.sh --operation crop-checks --task $W/task --request $W/empty.json        # 必须 passed
   ```
   `--bars` 是你自己从图上读出的行首小节号，不要猜；`--title` 用谱面上的原曲名。

9. **重绘**：云端会话没有生图工具 → `python3 $S/finish.py $W/cv.sh $W/task vector`（每组登记 unavailable，转上游的轮廓矢量 + 五线修补）。宿主真有生图工具时改走上游 `redraw-requests → dispatch-redraw → finish-redraw → review-redraw`，见上游 `references/stage-recovery-layout.md`。

10. **排版导出**：`python3 $S/finish.py $W/cv.sh $W/task export [--margin 24] [--gap 6]` —— 打印每页包含的 region 范围和预览图路径。
    - **实际看每一页预览**（必要时 `pdftoppm -r 200` 放大抽查）：标题、速度、拍号、顺序、首尾、连音/装饰音/开镲记号、有无截断重叠。
    - 检查分页处：如果某行顶部带着上一行的记号（例如上一行下方的三连音括号），分页落在这两行之间会让记号孤零零挂在下一页顶上——调 `--gap`/`--margin` 直到这两行同页。

11. **最终审阅**：`python3 $S/finish.py $W/cv.sh $W/task review --notes "实际逐页看到的内容和已知瑕疵"` → `complete`。

12. **交付**：把 `$W/task/exports/<revision>/<谱名>.pdf` 复制成**纯英文文件名**（中文/日文名在 App 里可能打不开），用 SendUserFile 发，`display: "attach"`。说明页数、小节范围、走的是矢量转描还是生图、已知瑕疵。

## 坑

- **上游匿名下载**在云端被 B站拒（网页返回"出错啦"）；yt-dlp 能拿到。不要去改上游的下载代码或加 Cookie。
- **staff_spacing 要用实测小数**：矢量转描在 `staff_top + i*staff_spacing` ±2px 处找五线，取整成 14 而实际是 13.5 时第五线偏 2px，导出报"五线边界不可确认"。`rows.py` 已用每行实测首末线位置。
- **裁剪门禁是硬门槛**：切线压到任何墨迹（哪怕 2 个像素的符头顶）都会 `crop_edge` 阻止导出。`rows.py` 只在空白行下刀，并在每张截图里 ±4px 校正滚动测量误差。
- **记号高度交错**（contested gap）：比如第 44 小节下方三连音括号和第 45 小节上方开镲 o 同高，没有能把两者分开的水平线。选二者之上的空白线，让括号跟下一行走——两行在 PDF 里紧挨着时位置和原谱一致；然后按第 10 步保证它们不被分页拆开，并在交付说明里讲清楚。
- **重叠裁剪不可取**：两行区域重叠会让记号在 PDF 里出现两次。
- 换来源截图、改切线后要重新 `assemble`（上游会撤销旧冻结），再跑 crop-checks。
- `cv.sh` 每次调用都 `uv run --isolated`，单次要几秒；不要并行调用同一个任务。
