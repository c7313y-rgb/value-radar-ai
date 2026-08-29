# -*- coding: utf-8 -*-
"""
需要連鎖の伝播計算 ＝ Second Order Opportunity Engine

やっていること:
  (1) 各ノードの Demand Evidence Score を実需シグナルから算出（人気ではなく事実）
  (2) 上流ノードの「需要の勢い」を、lag と elasticity で減衰させながら下流へ流す
      → これが「まだ決算に出ていないが、これから来る需要圧力」
  (3) そのノードに属する企業群の株価がどれだけ既に織り込んでいるかを測る
      （バリュエーション・パーセンタイルとモメンタムの合成 ＝ Priced-in Score）
  (4) 波及圧力 − 織り込み度 ＝ 未織り込みギャップ（Unpriced Gap）
      これが大きいノードが「NVIDIAの次に利益が流れ込むのに、まだ評価されていない場所」

lag の扱いが肝で、遅れが大きいエッジほど「今はまだ効いていないが、
残り時間が短くなるほど確度が上がる」ものとして減衰させている。
"""

from __future__ import annotations
import math
from typing import Dict, List, Tuple

from .graph import NODES, NODE_MAP, EDGES, parents, children, depth_map, paths_to, chain_label
from ..providers.base import EvidenceItem

# シグナルごとの重み。実需に近いものほど重い。
SIGNAL_WEIGHT = {
    "orders_backlog": 1.30,
    "lead_time": 1.20,
    "capex_plan": 1.15,
    "plant_construction": 1.10,
    "power_demand": 1.10,
    "shipment_stats": 1.05,
    "utilization": 1.00,
    "gov_budget": 0.95,
    "price_index": 0.85,
    "job_postings": 0.80,
    "patents": 0.60,
    "exec_commentary": 0.55,
}


def evidence_score(items: List[EvidenceItem]) -> Tuple[float, float]:
    """
    Demand Evidence Score（水準）と Demand Momentum（変化）を返す。
    水準だけ見ると「すでに大きい産業」が常に勝ってしまうので、変化を別に持つ。
    """
    if not items:
        return 50.0, 0.0
    wl = sum(SIGNAL_WEIGHT.get(i.signal, 1.0) for i in items)
    level = sum(i.value * SIGNAL_WEIGHT.get(i.signal, 1.0) for i in items) / wl
    mom = sum(i.change_3m * SIGNAL_WEIGHT.get(i.signal, 1.0) for i in items) / wl
    return level, mom


def lag_weight(lag_months: float, horizon: float = 18.0) -> float:
    """
    lag が長いほど「今期の業績」には効かないので割り引く。
    ただし完全にゼロにはしない（先回りできる余地こそが超過リターンの源泉）。
    """
    return 0.35 + 0.65 * math.exp(-lag_months / horizon)


def propagate(evidence: Dict[str, List[EvidenceItem]]) -> Dict[str, dict]:
    """
    トポロジカル順に上流→下流へ需要圧力を流す。
    戻り値: {node_id: {evidence, momentum, inflow, pressure, depth, drivers}}
    """
    from .graph import topo_order
    depth = depth_map()
    state: Dict[str, dict] = {}

    for nid in topo_order():
        lvl, mom = evidence_score(evidence.get(nid, []))
        inflow = 0.0
        contrib: List[dict] = []
        for e in parents(nid):
            p = state.get(e.src)
            if not p:
                continue
            w = e.elasticity * lag_weight(e.lag_months)
            # 上流の「勢い」を流す。水準ではなく変化を流すのが要点。
            flow = (p["momentum"] * 0.75 + (p["evidence"] - 50.0) * 0.25) * w
            inflow += flow
            contrib.append({
                "from": e.src, "from_label": NODE_MAP[e.src].label,
                "lag_months": e.lag_months, "elasticity": e.elasticity,
                "flow": round(flow, 2), "note": e.note,
            })
        contrib.sort(key=lambda x: -x["flow"])
        # 自ノードの実需（水準・変化）と、上流からの流入を合成
        pressure = 50.0 + 0.45 * (lvl - 50.0) + 0.35 * mom + 0.45 * inflow
        state[nid] = {
            "id": nid,
            "label": NODE_MAP[nid].label,
            "desc": NODE_MAP[nid].desc,
            "depth": depth.get(nid, 0),
            "is_driver": NODE_MAP[nid].is_driver,
            "evidence": round(lvl, 1),
            "momentum": round(mom, 1),
            "inflow": round(inflow, 2),
            "pressure": round(max(0.0, min(100.0, pressure)), 1),
            "drivers": contrib[:4],
        }
    return state


def priced_in(node_id: str, exposures: Dict[str, Dict[str, float]],
              val_pct: Dict[str, float], mom_pct: Dict[str, float]) -> Tuple[float, int]:
    """
    そのノードに露出する企業群が、どれだけ既に株価に織り込んでいるか（0-100）。
    バリュエーションの高さ 60% ＋ モメンタムの強さ 40%。
    exposures: {ticker: {node: weight}}
    val_pct  : {ticker: 割高側パーセンタイル(0-100, 高いほど割高)}
    mom_pct  : {ticker: モメンタムのパーセンタイル(0-100, 高いほど買われている)}
    """
    num = den = 0.0
    n = 0
    for t, nodes in exposures.items():
        w = nodes.get(node_id, 0.0)
        if w <= 0:
            continue
        v = val_pct.get(t)
        m = mom_pct.get(t)
        if v is None or m is None:
            continue
        num += w * (0.60 * v + 0.40 * m)
        den += w
        n += 1
    if den <= 0:
        return 50.0, 0
    return num / den, n


def opportunities(state: Dict[str, dict], exposures, val_pct, mom_pct,
                  min_companies: int = 1, min_pressure: float = 55.0) -> List[dict]:
    """
    未織り込みギャップの大きい順にノードを並べる。
    「需要圧力は高いのに、そこにいる企業がまだ買われていない」場所を上に出す。
    """
    rows: List[dict] = []
    for nid, st in state.items():
        if NODE_MAP[nid].is_driver:
            continue
        # 需要圧力そのものが弱い場所は「安いだけ」であって機会ではない。
        if st["pressure"] < min_pressure:
            continue
        pin, n = priced_in(nid, exposures, val_pct, mom_pct)
        if n < min_companies:
            continue
        gap = st["pressure"] - pin
        # 深いノードほど「発見価値」が高い（誰も見ていない）ため微加点
        discovery = 1.0 + 0.06 * max(0, st["depth"] - 1)
        rows.append({
            **st,
            "priced_in": round(pin, 1),
            "companies": n,
            "unpriced_gap": round(gap * discovery, 1),
            "paths": [chain_label(p) for p in paths_to(nid)][:3],
        })
    rows.sort(key=lambda r: -r["unpriced_gap"])
    return rows


def company_trend_score(exposure: Dict[str, float], state: Dict[str, dict],
                        opp_index: Dict[str, dict]) -> Tuple[float, List[dict]]:
    """
    企業の「未来需要 Trend」レイヤー得点（0-100）。
    露出ノードの需要圧力を露出度で加重し、未織り込みギャップをボーナスとして足す。
    """
    if not exposure:
        return 45.0, []
    tot = sum(exposure.values()) or 1.0
    base = 0.0
    detail: List[dict] = []
    for nid, w in sorted(exposure.items(), key=lambda x: -x[1]):
        st = state.get(nid)
        if not st:
            continue
        gap = opp_index.get(nid, {}).get("unpriced_gap", 0.0)
        contrib = st["pressure"] + max(0.0, gap) * 0.30
        base += contrib * w
        detail.append({
            "node": nid, "label": st["label"], "exposure": round(w, 3),
            "pressure": st["pressure"], "unpriced_gap": round(gap, 1),
            "depth": st["depth"],
        })
    score = base / tot
    # 露出の合計が小さい企業（テーマとの接点が薄い）は中庸に寄せる
    coverage = min(1.0, tot / 0.6)
    score = 50.0 + (score - 50.0) * (0.55 + 0.45 * coverage) * 1.55
    return max(0.0, min(100.0, score)), detail
