# -*- coding: utf-8 -*-
"""
リスクペナルティと確信度

最終推奨点 = VALUE SCORE × 確信度 − Risk Penalty

確信度を掛け算にしているのは、「データが薄い」「委員会の意見が割れている」銘柄の
高得点をそのまま信じないため。Risk Penalty を引き算にしているのは、
リスクは点数の比例ではなく絶対的な減点として効くべきだから。
"""

from __future__ import annotations
from typing import Dict, List, Tuple


def risk_penalty(f, company, layers: Dict[str, float], exposure: Dict[str, float]) -> Tuple[float, List[dict]]:
    """0〜25点の減点。内訳を必ず返す（説明できない減点はしない）。"""
    items: List[dict] = []

    def add(name: str, pts: float, why: str) -> None:
        if pts > 0.05:
            items.append({"name": name, "points": round(pts, 2), "why": why})

    # 1. ボラティリティ
    v = max(0.0, f.vol_ann - 0.30) * 18.0
    add("価格変動", min(v, 5.0), f"年率ボラティリティ {f.vol_ann*100:.0f}%")

    # 2. ドローダウン耐性
    dd = max(0.0, abs(f.max_drawdown_1y) - 30.0) * 0.08
    add("最大下落", min(dd, 3.5), f"過去1年の最大下落 {f.max_drawdown_1y:.0f}%")

    # 3. 財務レバレッジ
    lev = 0.0
    if f.net_debt_ebitda > 3.0:
        lev += (f.net_debt_ebitda - 3.0) * 0.9
    if 0 < f.interest_coverage < 5.0:
        lev += (5.0 - f.interest_coverage) * 0.5
    add("財務レバレッジ", min(lev, 5.0),
        f"ネット有利子負債/EBITDA {f.net_debt_ebitda:.1f}倍・利払カバレッジ {f.interest_coverage:.0f}倍")

    # 4. バリュエーションの伸び切り（ここが「高すぎる優良株」を弾く本体）
    stretch = 0.0
    if f.per > 40:
        stretch += (f.per - 40) * 0.07
    if f.peg > 2.5:
        stretch += (f.peg - 2.5) * 1.2
    if 0 < f.fcf_yield < 1.5:
        stretch += (1.5 - f.fcf_yield) * 1.6
    add("バリュエーション過熱", min(stretch, 6.0),
        f"PER {f.per:.0f}倍・PEG {f.peg:.1f}・FCF利回り {f.fcf_yield:.1f}%")

    # 5. 流動性
    liq = 0.0
    if f.adv_musd < 30:
        liq += (30 - max(f.adv_musd, 1)) * 0.06
    if company.mcap_musd < 3000:
        liq += 1.2
    add("流動性", min(liq, 3.0), f"平均売買代金 約{f.adv_musd:.0f}百万USD")

    # 6. ガバナンス
    gov = 0.0
    if f.governance_score and f.governance_score < 45:
        gov += (45 - f.governance_score) * 0.06
    add("ガバナンス", min(gov, 3.0), f"ガバナンス評価 {f.governance_score:.0f}/100")

    # 7. テーマ集中（1本足打法のリスク）
    conc = 0.0
    if exposure:
        top = max(exposure.values())
        if top > 0.45:
            conc = (top - 0.45) * 12.0
    add("テーマ集中", min(conc, 3.0), "単一の需要テーマへの依存度が高い")

    # 8. 群集（高モメンタム × 高バリュエーション）
    crowd = 0.0
    if f.mom_12m > 60 and f.per > 45:
        crowd = min(3.0, (f.mom_12m - 60) * 0.03 + (f.per - 45) * 0.03)
    add("過熱・群集", crowd, f"12ヶ月騰落 {f.mom_12m:+.0f}% と高PERの併存")

    total = sum(i["points"] for i in items)
    return min(total, 25.0), items


def confidence(f, layer_coverage: Dict[str, float], committee: dict,
               synthetic: bool) -> Tuple[float, List[dict]]:
    """0.55〜1.00。低いほど「点数を信じるな」という意思表示。"""
    parts: List[dict] = []

    cov = f.data_coverage
    parts.append({"name": "データ網羅性", "value": round(cov, 3)})

    layer_cov = sum(layer_coverage.values()) / max(len(layer_coverage), 1)
    parts.append({"name": "指標の欠損の少なさ", "value": round(layer_cov, 3)})

    # 委員会の一致度（意見が割れているほど確信度を落とす）
    agree = committee.get("agreement", 0.7)
    parts.append({"name": "委員会の一致度", "value": round(agree, 3)})

    # 利益の安定性が低い＝予想が当たりにくい
    stab = f.earnings_stability if f.earnings_stability else 0.5
    parts.append({"name": "利益の安定性", "value": round(stab, 3)})

    raw = 0.32 * cov + 0.24 * layer_cov + 0.28 * agree + 0.16 * stab
    conf = 0.55 + 0.45 * max(0.0, min(1.0, raw))
    if synthetic:
        # デモ合成データであることを確信度にも正直に反映する
        conf *= 0.92
        parts.append({"name": "デモ合成データによる割引", "value": 0.92})
    return round(min(conf, 1.0), 3), parts
