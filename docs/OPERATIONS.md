# 運用ガイド

## 1. 日次サイクル

```
06:30 JST  GitHub Actions（または cron）が起動
  ├─ データ取得（provider に依存）
  ├─ 8レイヤー評価・需要伝播・委員会
  ├─ data/latest.json          … アプリが読む唯一のファイル
  ├─ data/history/YYYY-MM-DD.json … 軽量スナップショット
  ├─ data/series.json          … 銘柄別スコア推移（直近90営業日）
  ├─ data/alerts.json          … 前回差分
  ├─ 高重要度アラートがあれば Issue を自動作成
  └─ コミット → GitHub Pages へ配信
```

## 2. 初期セットアップ

```bash
git init && git add -A && git commit -m "feat: VALUE RADAR AI 初期版"
git branch -M main
git remote add origin git@github.com:<user>/value-radar-ai.git
git push -u origin main
```

GitHub の Settings で：

1. **Pages** → Source を **GitHub Actions** に設定
2. **Actions → General** → Workflow permissions を **Read and write** に
3. （実データを使う場合）**Variables** に `VR_PROVIDER`、**Secrets** に `VR_PREMIUM_KEY` を登録

## 3. 手動実行

```bash
python3 -m engine.pipeline                       # 当日
python3 -m engine.pipeline --date 2026-09-01     # 日付指定（再現実行）
python3 -m engine.pipeline --regions JP,US       # 地域を絞る
python3 -m engine.pipeline --no-write            # 標準出力のみ
```

GitHub 上からは Actions → daily-scan → **Run workflow** で
provider と日付を指定して手動実行できます。

## 4. 監視すべきこと

| 症状 | 疑うところ |
|---|---|
| 毎日 TOP10 がほとんど動かない | 需要エビデンスの変化幅が小さすぎる。`DemoEvidenceProvider` は緩やかに動く設計 |
| 毎日 TOP10 が総入れ替え | モメンタム系の重みが効きすぎ。`MOMENTUM_METRICS` を見直す |
| 全銘柄が50点付近に潰れる | ピアグループが大きすぎるか `LAYER_SPREAD` が小さい |
| 特定業種が常に上位 | ピアグループのフォールバックが効きすぎ。`MIN_GROUP` を調整 |
| 確信度が一律に低い | `data_coverage` が低い。プロバイダの取得項目を増やす |
| 予算プランが常に米国株 | `region_cap` を下げる（既定 0.70） |

## 5. パフォーマンス

デモ82銘柄で全パイプラインが約0.15秒（標準ライブラリのみ、Python 3.11）。
`evaluate_universe` を2周回しているのは、織り込み度の計算に評価結果が必要なためです。

ユニバースを数千銘柄に拡張する場合の注意：

- `PeerNormalizer` はピアグループごとに統計をキャッシュ済み（O(N)）
- `paths_to()` は全経路を列挙するので、グラフを深くする場合は `max_depth` に注意
- `latest.json` が数MBを超えたら、`rows` を TOP100 に絞り、残りは別ファイルへ分割する

## 6. 拡張の順序（推奨）

1. **バックテスト** … 最優先。現状このスコアリングの有効性は未検証
2. **ユニバース拡張** … MSCI ACWI 構成銘柄の実データ取得
3. **セグメント売上からの露出度自動推定** … 現在は手動設定
4. **需要エビデンスの実データ化** … 受注残・リードタイム・政府予算から
5. **LLM による定性評価の抽出** … 有報・統合報告書から出典付きで
6. **通知** … Slack / メール（`scripts/run_daily.sh` に追記点あり）

## 7. やってはいけないこと

- `--fallback-demo` を本番で使う（合成値に落ちたことに気づけない）
- 欠損を平均値で埋める（「データが無い」が「平均的」に化ける）
- 需要エビデンスを出典なしで登録する
- LLM に数値を生成させる（narrator は事実の束を受け取って表現だけを担当する設計）
- デモデータの出力を実在企業の評価として引用する
