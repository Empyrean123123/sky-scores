# 光遇(Sky)琴谱制作工具包

给光遇「自动弹谱器」做 15 键钢琴谱。输入是 Songsterr / Online Sequencer / 本地 MIDI 的多轨谱，输出是弹谱器能直接导入的 `.txt`。

## 用法

```bash
python3 make.py <歌key...>        # 生成琴谱（本机输出到 ~/Desktop，没有桌面时输出到 ./output/）
python3 make.py --search 歌名     # 在 Songsterr 搜谱
python3 make.py --tracks <songId> # 看某份谱的轨道（找人声/主奏/贝斯/鼓/钢琴）
```

新歌：在 `local_songs.json`（格式同 `extra_songs.json`）里加一项（轨道号、`levels` 段落档位、`opts`），再 `python3 make.py <key>`。
**做谱不要修改仓库**：这个仓库是公开的，新歌配置只写进 `local_songs.json`（已 gitignore），不要改 `songs.py`/`extra_songs.json`，不要为做谱提交或推送。`mid/`、`sky1984/` 里的谱源也不进仓库。
`opts` 覆盖 `arrange.py` 顶部的参数，每个参数的含义见那里的注释。

做好后把 `.txt` 直接用文件发给用户（云端会话用发送文件功能），不要走微信。

## 输出格式（不能变）

- UTF-16（带 BOM），JSON 数组里一个对象，字段顺序固定：
  `name, author, transcribedBy, isComposed, bpm, bitsPerPage, pitchLevel, isEncrypted, songNotes`
- `songNotes=[{"time":毫秒整数,"key":"1KeyN"}]`，N=0..14，按时间排序，末尾换行。模板见 `template.txt`。
- 文件名和 `name` 用**原曲名**（日文/中文原文，不要罗马音），`author` 填原唱。
- `make.py` 生成后会自检格式，必须显示「格式OK」。

## 用户偏好（最重要）

1. **主唱旋律第一**：主唱每一个起音都必须保留，节奏不能简化。不开同音精简（`REPEAT_MIN` 保持 0），不因量化合并，伴奏/鼓加花与主唱冲突时一律让伴奏让路。每做完一首都要从输出反查主唱起音是否 100% 在。
2. **要厚，但分段落**：不用考虑人手能不能弹；但主歌稀、副歌满，段落要听得出来（`levels` 用 0 稀 / 1 中 / 2 满）。高音别太多。
3. **前奏必须听得出是哪首**：前奏旋律常在合成器/电钢/主奏轨，单吉他谱的前奏会听不出来。
4. **钢琴轨优先**：用户在光遇里弹的是钢琴。谱源有钢琴/键盘轨时，用 `FAITHFUL=[钢琴轨号]` 如实照搬它的节奏和音高（放在主唱下方）。改动大的先另存「(钢琴版)」让用户对比。
5. **有鼓就跟鼓**：有鼓轨的歌开 `DRUM=鼓轨号`（齐奏/停顿/加花处伴奏跟鼓走）。`DRUM_GROOVE`（普通小节也跟鼓）不是所有歌都适合，会和主唱抢节奏，开了要让用户听后再定，保留旧版可回退。
6. **快速音型换键**：光遇同一个键连按上限约 70ms（`SAMEKEY_MIN=0.07`）。伴奏里的双踩、鼓加花、快速连打不要删音，而是分配到不同键上交替（根音/五度/八度轮换）。只用于伴奏，主唱不换键。

## 标准做法

- **教科书是 Neo-Aspect**（Songsterr 6948261）：人声/主奏/节奏/贝斯/鼓五轨完整，主唱白键 100%，`PLANS=THICK2` + 鼓齐奏停顿 + 鼓加花，不开鼓律动。新歌以它为标准。
- 用户认可的参照：Neo-Aspect（标准流程）、黒のバースデイ（钢琴叠加 `FAITHFUL_PLUS`）、少女A（鼓律动）、メギツネ、携帯恋話、六兆年と一夜物語（钢琴版，用户评价「写得非常好」）。
- **术力口（VOCALOID/UTAU/SynthV 曲）**：按六兆年、少女A、携帯恋話的路子做。
  1. 先找这首的**钢琴编曲**（Online Sequencer 搜钢琴版 / 谱源里的钢琴轨 / 用户给的 MIDI），有就像六兆年那样整首如实照搬：`sid='os:ID', vocal=钢琴, bass=钢琴, harm=[钢琴], PLANS={0:{},1:{},2:{}}, OFFBEAT_LV=9, VOCAL_TOP=True, FAITHFUL=[钢琴], FAITHFUL_NOBASS=True`，`OS_BPM` 用 VocaDB 时长核对。六兆年的来源是 OS 1905900（单轨钢琴，186bpm）。
  2. 没有钢琴编曲再走乐队做法：`THICK2` + `DRUM` + `DRUMFILL`，另出一份「(鼓律动版)」开 `DRUM_GROOVE=True, GROOVE_THICK=1`（少女A 路子）让用户对比选。
  3. 分档照认可歌：前奏 0→1、主歌 0、pre-chorus 1、副歌 2、间奏 1、停顿 0、尾奏 1。
- 「只留主唱+钢琴」（Fabulous）是用户对那首 chill 曲的单独要求，**不是通用做法**。
- 编配：人声 = 右手旋律，只在长空档（≥4 拍）用主奏补；伴奏 = 贝斯根音 + 从和声轨统计的和弦，放在旋律下方。
- 新歌开 `MELFLOOR_FIX=True`；人声太低就按段落升八度（`VOCAL_OCT`）；有转调用 `KEYSEG` 分段移调。

## 找谱

选谱标准：谱源完整度（最好有人声轨 + 段落 marker）、主唱白键比例、是否录音室版（时长/速度要对，曾误用现场版）、有无钢琴轨。注意人声轨可能不叫 Vocal（例如叫角色名、或是大提琴轨）。

1. **Songsterr（首选）**：`/api/songs?pattern=` 搜，`/api/meta/{id}` 拿 revisionId+image，轨道 JSON 在 `dqsljvtekg760.cloudfront.net/{id}/{rev}/{image}/{i}.json`（gzip）。`ssget.py` 已封装，缓存在 `ss_<id>/`（不进仓库）。
2. **Online Sequencer**：Songsterr 没人声时试。`onlinesequencer.net/app/api/get_proto.php?id=`，`sid` 写 `'os:ID'`，轨道号 = 乐器号。它标的 bpm 可能错，用 VocaDB API 的 `lengthSeconds` 核对。
3. **Sky1984 谱库 + U-FRET**：以上都没有时，GitHub `Ai-Vonie/Sky1984-Sheets-Collection`（1.6 万份光遇谱，用 `git/trees/HEAD?recursive=1` 搜文件名）常有别人做的单音光遇谱，可当旋律源；和弦从 U-FRET 页面里的 `ufret_chord_datas` 拿，按小节铺成贝斯/和弦轨，合成 MIDI 放进 `mid/`（不进仓库），走 `sid='mid:名字'`。范例：`build_kurikaeshi.py`（繰り返し一粒）。别人的谱可能中途错位一格，先按每行 16 格打印网格检查；和弦要逐小节核对旋律命中率。
4. MidiShow 有 Cloudflare+鉴权下不了；MuseScore 下载要付费，用户不买。不要从录音自动扒谱。

## 踩过的坑

- Songsterr 的 duration 已含附点/三连音，别再乘。
- 主奏乐器取每拍最高音（去掉持续音）。
- 主歌听着卡时先查伴奏律动，别删主唱的音。
- 光遇不能中途变调：原曲转调的段落按同级数处理（或用 `KEYSEG` 移到白键上）。

## 练琴网页（practice/index.html）

- 线上版是 artifact https://claude.ai/artifact/H7WRWNwhPTa8aKzMXfhYTJ 。仓库里的 `practice/index.html` 必须和线上 artifact **逐字节一致**：每次改完先发布 artifact，再用 Artifact 工具的 `read` 取回线上完整 HTML（结果里给的保存文件），原样复制到 `practice/index.html`，用 sha256 核对两边相同后再提交推送。不要手写另一套外壳。
