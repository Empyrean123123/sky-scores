# 光遇(Sky)琴谱制作工具

把 Songsterr / Online Sequencer / 本地 MIDI 的多轨谱，编成《光·遇》15 键琴谱，输出「自动弹谱器」能直接导入的 `.txt`（UTF-16 JSON）。

- 主唱旋律完整保留（每个起音都在，只挪到白键上）
- 伴奏由贝斯根音和从和声轨统计出的和弦组成，始终放在旋律下方
- 按段落分档（主歌稀、副歌满），可跟鼓轨的齐奏、停顿和加花
- 可以把谱源里的钢琴轨如实搬过来
- 同一个键连按太快（< 70ms）时，伴奏自动换到别的键

## 环境

Python 3，不需要第三方库。需要能访问网络（下载 Songsterr 谱）并装有 `curl`。

## 用法

```bash
python3 make.py                      # 列出已配置的歌
python3 make.py <歌key...>           # 生成琴谱（有 ~/Desktop 就输出到桌面，否则输出到 ./output/）
python3 make.py --search 歌名        # 在 Songsterr 搜谱
python3 make.py --tracks <songId>    # 看某份谱有哪些轨道
```

生成后会自检格式，显示「格式OK」即可导入弹谱器。

## 加一首新歌

1. `--search` 找谱，`--tracks` 看轨道，找出人声、主奏、贝斯、和声、鼓、钢琴各是几号轨。
2. 在仓库根目录新建 `local_songs.json`（已 gitignore，只在你本地），加一项，例如：

   ```json
   {"runit": {"title": "RUN IT", "author": "Stray Kids", "sid": 5767835,
              "vocal": 1, "leads": [], "bass": 0, "harm": [],
              "levels": [[0, 15, 0], [16, 23, 1], [24, 39, 2], [40, 999, 1]],
              "opts": {"OFFBEAT_LV": 2, "SKYLINE": 7, "MELFLOOR_FIX": true}}}
   ```

   `levels` 是 `[起小节, 止小节, 档位]`，档位 0 稀 / 1 中 / 2 满。

   `opts` 里的参数（`DRUM`、`FAITHFUL`、`KEYSEG`、`VOCAL_OCT` 等）会覆盖 `arrange.py` 顶部的默认值，每个参数的含义见那里的注释。
3. `python3 make.py <key>`。

谱源也可以是 Online Sequencer（`sid='os:ID'`）或你自己放在 `mid/` 下的 MIDI 文件（`sid='mid:文件名'`，`mid/` 不进仓库）。

## 练琴网页

`practice/index.html` 是一个手弹练习页面：导入生成的 `.txt` 琴谱，右上是光遇 3×5 圆形琴键（音符快到时外圈的金色弧线转满一圈就按），下方是往前走的音符轨（图标下写着要按的键，走到金色竖线时按），并放出琴声。可以调速、AB 段循环、只看主旋律；等待模式下现在要按的键发金光、下一组画虚线框，按对了才往下走。**支持改键**：点「设置与改键」，点一个键位再按新键（重复的键会互换），也可以一键切到预设（光遇 PC 默认 `Y U I O P / H J K L ; / N M , . /`、左手 QWERT 等），设置会记在浏览器里。点封面可以换成自己的图片（只在本次打开时有效）。只在浏览器本地读取文件，不联网上传，也不和游戏交互。钢琴音色是内嵌的 Salamander Grand Piano 采样（Alexander Holm，CC BY 3.0），离线也能用。

```bash
cd practice && python3 -m http.server 8765
# 浏览器打开 http://localhost:8765
```

也可以直接双击 `practice/index.html` 打开。端口被占用时把 8765 换成别的数字（如 8766）即可。

## 文件

| 文件 | 作用 |
|---|---|
| `make.py` | 命令行入口：生成、搜索、看轨道、格式自检 |
| `arrange.py` | 编配核心 |
| `songs.py` / `extra_songs.json` | 已做过的歌的配置（可当例子） |
| `local_songs.json` | 你自己的歌的配置（不进仓库） |
| `ssget.py` / `ssparse.py` | 下载、解析 Songsterr 谱 |
| `osload.py` / `os_parse.py` | 读 Online Sequencer 谱 |
| `midload.py` | 读 MIDI |
| `template.txt` | 输出格式模板 |
| `practice/index.html` | 手弹练习网页 |
| `sheets/` | 做好的琴谱 |

## 说明

- `sheets/` 里是用本工具做好的光遇琴谱（`.txt`，可直接导入弹谱器或 `practice/` 练琴网页）。谱源数据在运行时从 Songsterr 等网站下载到本地缓存（`ss_*/`、`os/`，不进仓库）。
- 琴谱仅供个人练习使用。歌曲版权归原作者所有，请勿商用。
- 使用第三方网站的数据时请遵守各网站的使用条款。

## 许可证

[MIT](LICENSE)（只适用于代码；`sheets/` 里的琴谱不在此列，歌曲版权归原作者）
