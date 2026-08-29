# -*- coding: utf-8 -*-
"""
日次パイプライン

  公開データ取得 → 正規化 → 8レイヤー評価 → 需要連鎖伝播 → AI投資委員会
  → TOP100/30/10 → 理由生成 → 予算別プラン → テーマ別ガイド → 差分アラート
  → data/latest.json

  python -m engine.pipeline                    # デモデータ
  VR_PROVIDER=yfinance python -m engine.pipeline --fallback-demo
  python -m engine.pipeline --date 2026-08-30  # 日付を指定して再現実行
"""

from __future__ import annotations
import argparse
import datetime as _dt
import json
import os
import sys
from pathlib import Path
from typing import Dict, List

from .universe import get_universe
from .demand.graph import NODES, NODE_MAP, EDGES, validate as validate_graph, depth_map
from .demand.propagation import propagate, opportunities
from .providers.registry import get_market_provider, get_evidence_provider, describe
from .scoring.aggregate import evaluate_universe
from .scoring.normalize import PeerNormalizer
from .output.budget import build_all
from .output.theme_guide import build_all_guides
from .output.alerts import diff
from .output.fx import get_rates

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
HISTORY = DATA / "history"


def _percentiles(rows: List[dict]) -> tuple[Dict[str, float], Dict[str, float]]:
    """織り込み度の計算に使う、ユニバース内での割高度・モメンタムの順位。"""
    pers = sorted((r["f"]["per"] for r in rows if r["f"]["per"] > 0))
    moms = sorted(r["f"]["mom_12m"] for r in rows)

    def pct(xs, v):
        if not xs:
            return 50.0
        return sum(1 for x in xs if x < v) / len(xs) * 100.0

    val = {r["ticker"]: pct(pers, r["f"]["per"]) for r in rows}
    mom = {r["ticker"]: pct(moms, r["f"]["mom_12m"]) for r in rows}
    return val, mom


def run(as_of: str, provider_name: str | None, fallback_demo: bool,
        regions: List[str] | None = None, write: bool = True) -> dict:
    validate_graph()

    companies = get_universe(regions)
    mp = get_market_provider(provider_name, fallback_demo=fallback_demo)
    ep = get_evidence_provider(None, fallback_demo=True)
    desc, synthetic = describe(mp, ep)

    tickers = [c.ticker for c in companies]
    fund = mp.fundamentals(tickers, as_of)
    if not fund:
        raise SystemExit("データ取得に失敗しました（0銘柄）")

    node_ids = [n.id for n in NODES]
    evidence = ep.evidence(node_ids, as_of)
    state = propagate(evidence)

    # --- 1周目：織り込み度を測るために暫定評価が必要なので、2段階で回す ----
    exposures = {c.ticker: c.nodes for c in companies if c.ticker in fund}
    tmp_rows = [{"ticker": t, "f": fund[t].to_dict()} for t in fund]
    val_pct, mom_pct = _percentiles(tmp_rows)
    opp_rows = opportunities(state, exposures, val_pct, mom_pct)
    opp_index = {o["id"]: o for o in opp_rows}

    rows = evaluate_universe(companies, fund, state, opp_index, as_of, synthetic)

    # --- 2周目：確定した評価で織り込み度を再計算し、ギャップを精緻化 --------
    val_pct, mom_pct = _percentiles(rows)
    opp_rows = opportunities(state, exposures, val_pct, mom_pct)
    opp_index = {o["id"]: o for o in opp_rows}
    rows = evaluate_universe(companies, fund, state, opp_index, as_of, synthetic)

    budgets = build_all(rows[:60])
    guides = build_all_guides(rows, state, opp_rows, as_of)

    depth = depth_map()
    payload = {
        "meta": {
            "app": "VALUE RADAR AI",
            "version": "0.1.0",
            "as_of": as_of,
            "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "provider": desc,
            "is_demo_data": synthetic,
            "universe_size": len(rows),
            "fx_rates_jpy": get_rates(),
            "disclaimer": (
                "本出力は投資判断の支援を目的としたスクリーニング結果であり、"
                "特定銘柄の売買を推奨するものではありません。"
                + ("現在のデータは実際の市場データではなくデモ用の合成値です。"
                   if synthetic else "")
            ),
            "layer_weights": {
                "quality": 20, "value": 20, "growth": 15, "health": 10,
                "momentum": 10, "diversification": 5, "governance": 10, "trend": 10,
            },
        },
        "rows": rows,
        "top10": [r["ticker"] for r in rows[:10]],
        "top30": [r["ticker"] for r in rows[:30]],
        "top100": [r["ticker"] for r in rows[:100]],
        "nodes": [state[n] for n in sorted(state, key=lambda x: -state[x]["pressure"])],
        "edges": [{"src": e.src, "dst": e.dst, "lag_months": e.lag_months,
                   "elasticity": e.elasticity, "note": e.note,
                   "src_label": NODE_MAP[e.src].label, "dst_label": NODE_MAP[e.dst].label}
                  for e in EDGES],
        "node_depth": depth,
        "opportunities": opp_rows[:20],
        "budgets": budgets,
        "guides": guides,
    }

    prev = None
    latest = DATA / "latest.json"
    if latest.exists():
        try:
            prev = json.loads(latest.read_text(encoding="utf-8"))
        except Exception:
            prev = None
    payload["alerts"] = diff(prev, payload)

    if write:
        DATA.mkdir(exist_ok=True)
        _update_series(as_of, rows)
        HISTORY.mkdir(exist_ok=True)
        latest.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                          encoding="utf-8")
        (HISTORY / f"{as_of}.json").write_text(
            json.dumps(_slim(payload), ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8")
        (DATA / "alerts.json").write_text(
            json.dumps({"as_of": as_of, "alerts": payload["alerts"]},
                       ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


SERIES_KEEP = 90


def _update_series(as_of: str, rows: List[dict]) -> None:
    """銘柄ごとの最終推奨点の推移を data/series.json に追記する（直近90営業日）。"""
    path = DATA / "series.json"
    series: Dict[str, list] = {}
    if path.exists():
        try:
            series = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            series = {}
    for r in rows:
        hist = [x for x in series.get(r["ticker"], []) if x.get("d") != as_of]
        hist.append({"d": as_of, "v": r["final_score"]})
        hist.sort(key=lambda x: x["d"])
        series[r["ticker"]] = hist[-SERIES_KEEP:]
    path.write_text(json.dumps(series, ensure_ascii=False, separators=(",", ":")),
                    encoding="utf-8")


def _slim(p: dict) -> dict:
    """履歴は軽量版のみ残す（リポジトリを太らせない）。"""
    return {
        "meta": p["meta"],
        "rows": [{k: r[k] for k in ("ticker", "name", "rank", "final_score", "value_score",
                                    "price", "layers", "verdict", "verdict_label",
                                    "company_grade", "price_grade", "risk_points",
                                    "entry_low", "entry_high", "upside_pct")}
                 for r in p["rows"]],
        "nodes": [{k: n[k] for k in ("id", "label", "pressure", "evidence", "momentum", "inflow")}
                  for n in p["nodes"]],
        "alerts": p["alerts"],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="VALUE RADAR AI daily pipeline")
    ap.add_argument("--date", default=_dt.date.today().isoformat())
    ap.add_argument("--provider", default=None, help="demo / yfinance / premium")
    ap.add_argument("--fallback-demo", action="store_true",
                    help="実データ取得に失敗した場合デモへ退避（本番では使わないこと）")
    ap.add_argument("--regions", default="", help="JP,US,EU,ASIA のカンマ区切り")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)

    regions = [x.strip() for x in a.regions.split(",") if x.strip()] or None
    p = run(a.date, a.provider, a.fallback_demo, regions, write=not a.no_write)

    m = p["meta"]
    print(f"[VALUE RADAR AI] {m['as_of']}  provider: {m['provider']}"
          f"  demo_data={m['is_demo_data']}  universe={m['universe_size']}")
    print("--- 本日の投資候補 TOP10 ---")
    for r in p["rows"][:10]:
        print(f" #{r['rank']:<2} {r['final_score']:5.1f}  {r['name']}（{r['ticker']}）"
              f" 企業{r['company_grade']}/価格{r['price_grade']} {r['verdict_label']}"
              f" 上値{r['upside_pct']:+.0f}%")
    print("--- 未織り込みギャップ上位（二次・三次波及候補） ---")
    for o in p["opportunities"][:6]:
        print(f"  {o['unpriced_gap']:+6.1f}  {o['label']}（圧力{o['pressure']} / 織込{o['priced_in']}）")
    print(f"--- アラート {len(p['alerts'])}件 ---")
    for al in p["alerts"][:6]:
        print(f"  [{al['severity']}] {al['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
