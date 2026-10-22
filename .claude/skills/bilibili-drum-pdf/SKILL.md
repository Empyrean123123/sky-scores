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
   分 P 加 `?p=N`。只要画面，不要音频。下载可能超过 2 分钟，用后台运行（`run_in_background`）。
   yt-dlp 也失败（`Unable to extract initial state` / 412）时的匿名备用路线：`api.bilibili.com/x/player/pagelist?bvid=…` 取 cid → `x/player/playurl?bvid=…&cid=…&fnval=4048&try_look=1`（不带 try_look 只给 480p）取 1080p avc 的 `baseUrl`；默认 CDN 报 HTTP 567 时把主机换成 `upos-sz-mirrorcos.bilivideo.com`。请求带普通浏览器 UA 和 `Referer: https://www.bilibili.com`，不用 Cookie。

3. **准备任务**：`$W/cv.sh $W/src/v.mp4 --output $W/task --summary` → `needs_source_review`。

4. **先自己看视频**：`ffmpeg -ss 2 -i v.mp4 -frames:v 1 f.png` 抽几帧实际看。确认是白底、多行、向上滚动、行首印小节号；记下标题、作者、速度、水印位置。横向滚动、翻页式、比例变化的视频不在本流程范围（上游也不支持），告诉用户。

5. **测滚动、定截图点**：`$PY $S/scroll_plan.py $W/src/v.mp4 $W/plan.json` —— 输出总滚动量和截图计划（相邻截图偏移 ≤600px，整行重叠）。出现"非平移变化"或"单步滚动超过 max-step"时人工看那几秒。

6. **截图**：`$PY $S/capture_plan.py $W/cv.sh $W/task $W/plan.json $W/caps.json`
   之后要补采（rows.py 说某几行没有完整截图时）：`$PY $S/capture_plan.py $W/cv.sh $W/task --add 秒数 $W/caps.json`

7. **找谱行、放切线**：`mkdir $W/rows && $PY $S/rows.py $W/task $W/caps.json $W/rows`
   - 五线按实测线距做模板匹配，短行、半行末行也能找到；行距突然变大会警告"可能漏了行"。
   - 每个区域从完整可见的截图里选：**优先避开水印**（水印转描后是一团垃圾），其次避开蓝色播放高亮（浅色，不影响转描），再选居中的。水印不在右上角时用 `--wm x0,y0,x1,y1` 指定。
   - 切线放在全局滚动坐标里**最长空白段的中点**，相邻两行共用同一条线，不丢不重；墨迹判定比上游 crop-checks 更严，预检过了门禁就过。
   - **行间没有空白行**（上一行下方的连音/符梁和下一行上方的重音/开镲同高）时自动把这几行合并成一个区域，报告"合并的行"。合并块里只有第一组五线会被上游修补，交付前用 `deliver` 补画其余五线。
   - 报告"记号可能被切给了离得远的那一行"的行间（空白带很窄或行间特别高）：**重点看这几处的 strip**。若上一行的记号（如三连音括号）落到了下一行顶部，用 `--merge 18-19`（行号）把两行合并后重跑。
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
   `--bars` 是你自己从图上读出的**原谱每一行**的行首小节号（合并块里的几行也逐行给），不要猜；`--title` 用谱面上的原曲名。

9. **重绘**：云端会话没有生图工具 → `python3 $S/finish.py $W/cv.sh $W/task vector`（每组登记 unavailable，转上游的轮廓矢量 + 五线修补）。宿主真有生图工具时改走上游 `redraw-requests → dispatch-redraw → finish-redraw → review-redraw`，见上游 `references/stage-recovery-layout.md`。

10. **排版导出**：`python3 $S/finish.py $W/cv.sh $W/task export [--margin 24] [--gap 6]` —— 打印每页包含的 region 范围和预览图路径。
    - **实际看每一页预览**（必要时 `pdftoppm -r 200` 放大抽查）：标题、速度、拍号、顺序、首尾、连音/装饰音/开镲记号、有无截断重叠。
    - 检查分页处：如果某行顶部带着上一行的记号（例如上一行下方的三连音括号），分页落在这两行之间会让记号孤零零挂在下一页顶上——调 `--gap`/`--margin` 直到这两行同页。

11. **最终审阅**：`python3 $S/finish.py $W/cv.sh $W/task review --notes "实际逐页看到的内容和已知瑕疵"` → `complete`。

12. **交付**：`python3 $S/finish.py $W/cv.sh $W/task deliver --name xxx-drums.pdf --thick` —— 给合并块补画五线（`restaff.py`，按原裁剪实测的线位和长度），输出 `$W/out/xxx-drums.pdf`。用**纯英文文件名**（中文/日文名在 App 里可能打不开）。有合并块时再看一眼补线后的页面。用 SendUserFile 发，`display: "attach"`。说明页数、小节范围、走的是矢量转描还是生图、已知瑕疵（具体到小节）。

## 多首并行

用户一次给多个视频时，每首开一个后台子代理（Agent 工具，`general-purpose`），各自独立工作目录，共用同一个上游克隆（`UPSTREAM_DIR=…`，只读）。子代理不要发文件给用户；收到报告后自己看至少一页再发。

## 坑

- **上游匿名下载**在云端被 B站拒（网页返回"出错啦"）；yt-dlp 能拿到。不要去改上游的下载代码或加 Cookie。
- **staff_spacing 要用实测小数**：矢量转描在 `staff_top + i*staff_spacing` ±2px 处找五线，取整成 14 而实际是 13.5 时第五线偏 2px，导出报"五线边界不可确认"。`rows.py` 已用每行实测首末线位置。
- **裁剪门禁是硬门槛**：切线压到任何墨迹（哪怕 2 个像素的符头顶）都会 `crop_edge` 阻止导出。`rows.py` 只在空白行下刀，并在每张截图里 ±4px 校正滚动测量误差。
- **记号高度交错**：没有空白线时 rows.py 自动合并；有很窄的空白线但记号被分错行时（例如第 44 小节下方三连音括号落到第 45 行顶部）要么 `--merge`，要么保证这两行不被分页拆开（第 10 步），并在交付说明里讲清楚。
- **翻页式 / 软件界面录屏**（画面整屏跳、顶部有 Guitar Pro 类工具条、右侧滚动条、黄色高亮）：scroll_plan.py 会自动改为"每个静止画面都截"，rows.py 按共有谱行内容对齐偏移（不信滚动测量）。顶部工具条用 `--wm 0,0,1920,<工具条下沿>` 覆盖，通栏的水印框以上视为不可见；谱面左右范围按五线端点自动收窄，避开滚动条和左边缘的当前行标记。视频末尾跳回开头的画面要从 plan 里删掉——先抽帧确认真的跳回了开头；`非平移变化` 很多时候只是播放高亮在动，平滑滚动的视频也常被判成翻页模式（只是多截几张，结果不受影响）。
- **悬空记号**：两行之间单独漂着的开镲 o、连音数字、括号，rows.py 不一定能判断归属（切在最长空白带中间）。看 strip 时专门看每行上下边缘有没有不属于本行的记号，有就 `--merge`。
- **重叠裁剪不可取**：两行区域重叠会让记号在 PDF 里出现两次。
- **bbox 下边界不含**：上游检查 `bottom-1` 那一行，rows.py 已把下边界设为空白行 +1。
- **stage/export 报 invalid_state**：finish.py 会直接调上游函数打印真正的异常（常见是"五线边界不可确认"= staff_top/staff_spacing 不准）。
- **细笔画丢失**：浅于上游墨迹阈值（gray 165）的细字笔画（作者名小字、细五线）转描后会断，五线由修补/补画解决，小字只能在交付说明里提。
- 换来源截图、改切线后要重新 `assemble`（上游会撤销旧冻结），再跑 crop-checks。
- `cv.sh` 每次调用都 `uv run --isolated`，单次要几秒；不要并行调用同一个任务。
