#!/usr/bin/env bash
# ローカルで毎日の定期監視を回すスクリプト（GitHub Actions を使わない場合）。
#
#   ./scripts/run_daily.sh
#   VR_PROVIDER=yfinance ./scripts/run_daily.sh
#
# cron に登録する例（毎朝6時30分）:
#   30 6 * * * cd /path/to/value-radar-ai && ./scripts/run_daily.sh >> logs/daily.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p logs
DATE="$(date +%F)"
echo "=== VALUE RADAR AI  $DATE  provider=${VR_PROVIDER:-demo} ==="

python3 -m engine.pipeline --fallback-demo

# 高重要度アラートを標準出力へ（メール通知やSlack連携はここに足す）
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("data/alerts.json")
if p.exists():
    d = json.loads(p.read_text(encoding="utf-8"))
    high = [a for a in d["alerts"] if a["severity"] == "high"]
    if high:
        print(f"\n[要確認] 高重要度アラート {len(high)}件")
        for a in high:
            print(f"  ・{a['title']}")
            if a.get("detail"):
                print(f"    {a['detail']}")
    else:
        print("\n高重要度アラートはありません。")
PY

if [ -d .git ] && [ "${VR_GIT_COMMIT:-0}" = "1" ]; then
  git add data/ && git commit -m "chore(data): 日次再評価 $DATE" || true
fi
