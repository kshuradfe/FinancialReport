#!/usr/bin/env bash
# FinScope 一键启动（Git Bash / macOS / Linux）
set -euo pipefail
cd "$(dirname "$0")"

if [ -x ".venv/Scripts/python.exe" ]; then
  PY=".venv/Scripts/python.exe"          # Windows venv under Git Bash
elif [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
elif command -v python >/dev/null 2>&1; then
  PY="python"
else
  echo "没有找到 Python。请先安装 Python 3.10+ (https://www.python.org)。" >&2
  exit 1
fi

exec "$PY" run_finscope.py "$@"
