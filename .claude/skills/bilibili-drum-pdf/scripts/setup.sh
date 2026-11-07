#!/bin/bash
# 取得上游 bilibili-drum-score-to-pdf（固定提交），并生成 convert.py 包装脚本 cv.sh。
# 用法: setup.sh <工作目录>     之后用 <工作目录>/cv.sh --operation ... 调用上游 CLI
set -euo pipefail
WORK=${1:?工作目录}
REV=332922000d088803f4d74e8d7a4a7ebf93f26fc8
UP=${UPSTREAM_DIR:-$HOME/.cache/bilibili-drum-score-to-pdf}
if [ ! -d "$UP/.git" ]; then
  GIT_LFS_SKIP_SMUDGE=1 git clone --quiet https://github.com/kenqia/bilibili-drum-score-to-pdf "$UP"
fi
if [ "$(git -C "$UP" rev-parse HEAD)" != "$REV" ]; then
  git -C "$UP" fetch --quiet --depth 1 origin "$REV" && git -C "$UP" -c advice.detachedHead=false checkout --quiet "$REV"
fi
SK="$UP/skills/bilibili-drum-score-to-pdf"
mkdir -p "$WORK"
cat > "$WORK/cv.sh" <<EOF
#!/bin/bash
# 上游 CLI 要在 Skill 根目录运行；先把相对路径参数转成绝对路径
args=(); prev=
for x in "\$@"; do
  if [[ \$prev == --task || \$prev == --request || \$prev == --output ]]; then x=\$(realpath -m -- "\$x")
  elif [[ \$prev != --* && \$x != -* && -e \$x ]]; then x=\$(realpath -- "\$x"); fi
  args+=("\$x"); prev=\$x
done
set -- "\${args[@]}"
cd "$SK" && exec uv run --python 3.12 --quiet --isolated --with-requirements scripts/requirements.txt python scripts/convert.py "\$@"
EOF
chmod +x "$WORK/cv.sh"
echo '{}' > "$WORK/empty.json"
for t in ffmpeg ffprobe pdftoppm uv; do command -v $t >/dev/null || echo "缺少 $t"; done
cd "$SK" && uv run --python 3.12 --quiet --isolated --with-requirements scripts/requirements.txt python scripts/host_check.py \
  | python3 -c "import json,sys;d=json.load(sys.stdin);print('prerequisites_ready =',d['prerequisites_ready'])"
echo "cv.sh -> $WORK/cv.sh"
