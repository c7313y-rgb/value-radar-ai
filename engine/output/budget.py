# -*- coding: utf-8 -*-
"""
予算別のポートフォリオ提案

株価だけを見せても投資判断はできない。
「その予算で、何株を、何銘柄に、いくらで買えるのか」まで出して初めて意思決定になる。

  日本株  : 売買単位（多くは100株）の整数倍でしか買えない
  米欧株  : 1株単位
  韓国・台湾: 銘柄により単位が異なる（universe の lot を使う）

配分は「スコア加重 × リスク逆数」で決め、単元の制約に合わせて整数へ丸める。
余った現金は無理に使い切らない（端数を埋めるための劣後銘柄購入をしない）。
"""

from __future__ import annotations
from typing import Dict, List, Optional

from .fx import get_rates, to_jpy

BUDGET_PRESETS = [50_000, 100_000, 300_000, 500_000, 1_000_000, 3_000_000, 10_000_000]

# 予算に応じた「無理のない銘柄数」
def target_names(budget: int) -> int:
    if budget < 80_000:    return 2
    if budget < 250_000:   return 2
    if budget < 450_000:   return 3
    if budget < 900_000:   return 4
    if budget < 2_500_000: return 6
    if budget < 8_000_000: return 8
    return 12


# 「良い会社・価格待ち」「見送り」は購入プランに載せない。
# アプリ自身が待てと言っているものを買わせないための整合性チェック。
BUYABLE = {"STRONG_CANDIDATE", "CANDIDATE", "WATCH"}


def allocate(rows: List[dict], budget: int, max_names: Optional[int] = None,
             max_weight: float = 0.40, region_cap: float = 0.70,
             respect_verdict: bool = True) -> dict:
    """
    rows は final_score 降順で渡す。戻り値は購入プランと未消化現金。
    """
    rates = get_rates()
    if respect_verdict:
        filtered = [r for r in rows if r.get("verdict") in BUYABLE]
        rows = filtered or rows
    n_target = max_names or target_names(budget)
    # 1〜2銘柄しか買えない予算でウェイト上限を課すと現金が余りすぎるため緩める
    max_weight = max(max_weight, 1.0 / n_target + (0.0 if n_target > 2 else 0.60))
    max_weight = min(max_weight, 1.0)

    # 単価が予算に対して大きすぎる銘柄は先に落とす（買えないものは提案しない）
    feasible = []
    for r in rows:
        unit_jpy = to_jpy(r["price"] * r["lot"], r["currency"], rates)
        if unit_jpy <= budget * max_weight * 1.35 and unit_jpy <= budget:
            feasible.append((r, unit_jpy))
    if not feasible:
        # 1銘柄すら買えない場合は、買える中で最良のものを1つだけ探す
        alt = [(r, to_jpy(r["price"] * r["lot"], r["currency"], rates)) for r in rows]
        alt = [x for x in alt if x[1] <= budget]
        if not alt:
            return {"budget": budget, "positions": [], "invested": 0, "cash": budget,
                    "note": "この予算で購入できる銘柄が候補内にありません（最低投資額が予算を超過）。"}
        feasible = alt[:1]

    # 銘柄の選定。
    # 小さい予算では「1銘柄で予算を食い潰す高価な銘柄」を後回しにする。
    # そうしないと5万円の提案が常に米国大型株1銘柄になり、分散の意味がなくなる。
    slot = budget / max(n_target, 1)
    cheap = [(r, u) for (r, u) in feasible if u <= slot * 1.6]
    rest = [(r, u) for (r, u) in feasible if u > slot * 1.6]
    ordered = cheap + rest

    picks = []
    seen_region: Dict[str, float] = {}
    seen_sector: Dict[str, float] = {}
    step = 1.0 / max(n_target, 1)
    for r, unit in ordered:
        if len(picks) >= n_target:
            break
        if seen_region.get(r["region"], 0.0) + step > region_cap + 1e-9:
            continue
        if n_target >= 4 and seen_sector.get(r["sector"], 0.0) + step > 0.55 + 1e-9:
            continue
        picks.append((r, unit))
        seen_region[r["region"]] = seen_region.get(r["region"], 0.0) + step
        seen_sector[r["sector"]] = seen_sector.get(r["sector"], 0.0) + step
    if not picks:
        picks = ordered[:n_target]

    raw = []
    for r, unit in picks:
        risk_adj = 1.0 / max(0.6, (r["risk_points"] / 8.0 + r["f"]["vol_ann"] * 2.2))
        raw.append(max(0.01, (r["final_score"] ** 1.6) * risk_adj))
    tot = sum(raw) or 1.0
    weights = [min(max_weight, x / tot) for x in raw]
    wsum = sum(weights) or 1.0
    weights = [w / wsum for w in weights]

    positions = []
    invested = 0.0
    for (r, unit), w in zip(picks, weights):
        target_jpy = budget * w
        lots = int(target_jpy // unit)
        if lots < 1 and target_jpy >= unit * 0.75 and invested + unit <= budget:
            lots = 1
        if lots < 1:
            continue
        cost = lots * unit
        while invested + cost > budget and lots > 0:
            lots -= 1
            cost = lots * unit
        if lots < 1:
            continue
        invested += cost
        positions.append({
            "ticker": r["ticker"], "name": r["name"], "region": r["region"],
            "currency": r["currency"], "price": r["price"], "lot": r["lot"],
            "lots": lots, "shares": lots * r["lot"],
            "unit_cost_jpy": round(unit), "cost_jpy": round(cost),
            "weight": round(cost / budget, 3),
            "final_score": r["final_score"], "stars": r["stars"],
            "sector": r["sector"], "verdict_label": r["verdict_label"],
        })

    # 余力があれば上位から1単元ずつ追加（ウェイト上限は守る）
    changed = True
    while changed and positions:
        changed = False
        for p in positions:
            unit = p["unit_cost_jpy"]
            if invested + unit <= budget and (p["cost_jpy"] + unit) / budget <= max_weight:
                p["lots"] += 1
                p["shares"] = p["lots"] * p["lot"]
                p["cost_jpy"] += unit
                p["weight"] = round(p["cost_jpy"] / budget, 3)
                invested += unit
                changed = True

    return {
        "budget": budget,
        "positions": sorted(positions, key=lambda p: -p["cost_jpy"]),
        "invested": round(invested),
        "cash": round(budget - invested),
        "cash_ratio": round((budget - invested) / budget, 3),
        "names": len(positions),
        "note": "端数を使い切るための追加購入はしていません（現金を残すのも判断のうち）。",
    }


def build_all(rows: List[dict]) -> List[dict]:
    return [allocate(rows, b) for b in BUDGET_PRESETS]
