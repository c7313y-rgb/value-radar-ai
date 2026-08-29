# -*- coding: utf-8 -*-
"""
日次の差分アラート（定期監視の心臓部）

毎朝スコアを再計算するだけでは「何が変わったのか」が分からない。
前回スナップショットとの差分から、人間が見るべき変化だけを抽出する。

検知するもの:
  1. TOP10 への新規参入 / 脱落
  2. 最終推奨点の急変（±6点以上）
  3. 投資判断（verdict）の変化
  4. 価格評価グレードの改善（＝良い会社がついに買える価格になった）
  5. 株価が購入検討価格帯へ入った
  6. 需要ノードの圧力急変（±8pt以上）
"""

from __future__ import annotations
from typing import Dict, List, Optional

SEV = {"high": 3, "medium": 2, "low": 1}


def diff(prev: Optional[dict], cur: dict) -> List[dict]:
    if not prev:
        return [{
            "type": "bootstrap", "severity": "low",
            "title": "初回スナップショットを作成しました",
            "detail": "翌営業日以降、前日差分のアラートが出力されます。",
        }]

    out: List[dict] = []
    pr = {r["ticker"]: r for r in prev.get("rows", [])}
    cr = {r["ticker"]: r for r in cur.get("rows", [])}

    prev_top = [r["ticker"] for r in prev.get("rows", [])[:10]]
    cur_top = [r["ticker"] for r in cur.get("rows", [])[:10]]

    for t in cur_top:
        if t not in prev_top:
            r = cr[t]
            out.append({
                "type": "top10_in", "severity": "high", "ticker": t, "name": r["name"],
                "title": f"{r['name']}（{t}）が TOP10 に新規参入",
                "detail": f"最終推奨点 {r['final_score']}／順位 {r['rank']}位。{r['reason'][0]}",
            })
    for t in prev_top:
        if t not in cur_top and t in cr:
            r = cr[t]
            out.append({
                "type": "top10_out", "severity": "medium", "ticker": t, "name": r["name"],
                "title": f"{r['name']}（{t}）が TOP10 から脱落",
                "detail": f"現在 {r['rank']}位／最終推奨点 {r['final_score']}。",
            })

    for t, r in cr.items():
        p = pr.get(t)
        if not p:
            continue
        d = r["final_score"] - p["final_score"]
        if abs(d) >= 6.0:
            out.append({
                "type": "score_jump", "severity": "high" if abs(d) >= 10 else "medium",
                "ticker": t, "name": r["name"],
                "title": f"{r['name']}（{t}）の最終推奨点が {d:+.1f}点",
                "detail": f"{p['final_score']} → {r['final_score']}。"
                          f"寄与の中心は {_top_layer_change(p, r)}。",
            })
        if r["verdict"] != p["verdict"]:
            out.append({
                "type": "verdict_change", "severity": "high",
                "ticker": t, "name": r["name"],
                "title": f"{r['name']}（{t}）の投資判断が「{p['verdict_label']}」→「{r['verdict_label']}」",
                "detail": r["reason"][2] if len(r["reason"]) > 2 else "",
            })
        order = ["S", "A", "B", "C", "D"]
        if order.index(r["price_grade"]) < order.index(p["price_grade"]) and r["company_grade"] in ("S", "A"):
            out.append({
                "type": "price_grade_up", "severity": "high",
                "ticker": t, "name": r["name"],
                "title": f"{r['name']}（{t}）の価格評価が {p['price_grade']} → {r['price_grade']} に改善",
                "detail": f"企業評価 {r['company_grade']} の銘柄が買える価格に近づいています"
                          f"（PER {r['f']['per']:.0f}倍／上値余地 {r['upside_pct']:+.0f}%）。",
            })
        if p["price"] > p["entry_high"] >= 0 and r["entry_low"] <= r["price"] <= r["entry_high"]:
            out.append({
                "type": "entry_zone", "severity": "high",
                "ticker": t, "name": r["name"],
                "title": f"{r['name']}（{t}）が購入検討価格帯に入りました",
                "detail": f"現在 {r['price']:,.2f} {r['currency']}／検討帯 "
                          f"{r['entry_low']:,.2f}〜{r['entry_high']:,.2f}。",
            })

    pn = {n["id"]: n for n in prev.get("nodes", [])}
    for n in cur.get("nodes", []):
        p = pn.get(n["id"])
        if not p:
            continue
        d = n["pressure"] - p["pressure"]
        if abs(d) >= 8.0:
            out.append({
                "type": "demand_shift", "severity": "medium",
                "node": n["id"],
                "title": f"需要テーマ「{n['label']}」の需要圧力が {d:+.1f}pt",
                "detail": f"{p['pressure']} → {n['pressure']}。"
                          f"実需エビデンス {n['evidence']}／上流からの流入 {n['inflow']:+.1f}。",
            })

    out.sort(key=lambda a: -SEV.get(a["severity"], 1))
    return out


def _top_layer_change(p: dict, r: dict) -> str:
    from ..scoring.layers import LAYER_LABELS
    best, bd = "", 0.0
    for k, v in r["layers"].items():
        d = v - p["layers"].get(k, v)
        if abs(d) > abs(bd):
            best, bd = k, d
    return f"{LAYER_LABELS.get(best, best)}（{bd:+.1f}）" if best else "複数レイヤー"
