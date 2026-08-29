#!/usr/bin/env bash
# 毎朝6時30分に run_daily.sh を実行する cron エントリを登録する（macOS / Linux）。
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
LINE="30 6 * * * cd $DIR && ./scripts/run_daily.sh >> $DIR/logs/daily.log 2>&1"
( crontab -l 2>/dev/null | grep -v "value-radar-ai" ; echo "$LINE  # value-radar-ai" ) | crontab -
echo "登録しました:"
crontab -l | grep value-radar-ai
