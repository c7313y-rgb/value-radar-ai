#!/usr/bin/env bash
# ローカルでアプリを開く（ビルド不要）。
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f data/latest.json ] || python3 -m engine.pipeline
echo "→ http://localhost:${1:-8000}/"
python3 -m http.server "${1:-8000}"
