# -*- coding: utf-8 -*-
"""
テーマ別 投資ガイドの自動生成

需要連鎖グラフのノード1つを「テーマ」とみなし、
  なぜこのテーマが重要なのか（因果と実需のエビデンス）
  どこで需要が発生しているのか（実証現場・拠点）
  候補TOP5の比較表（株価／購入検討価格帯／最低投資額／優待・配当／評価）
  予算別の購入例
  初心者が押さえる3点と注意点
を、その日の計算結果からまるごと組み立てる。

紙のガイド／配布資料に落とせる粒度まで構造化しておくのが狙い。
"""

from __future__ import annotations
from typing import Dict, List

from ..demand.graph import NODE_MAP, paths_to, chain_label, SIGNAL_LABELS
from .budget import allocate
from .fx import to_jpy, get_rates

GUIDE_BUDGETS = [50_000, 100_000, 300_000, 500_000]


def _stars(n: int) -> str:
    return "★" * n + "☆" * (5 - n)


def _eval_comment(r: dict) -> str:
    """初心者向けの一言評価。良い点と懸念を必ず1つずつ含める。"""
    good, bad = [], []
    L = r["layers"]
    if L["quality"] >= 62: good.append("収益性が高い")
    if L["growth"] >= 62: good.append("成長が続いている")
    if L["value"] >= 62: good.append("同業比で株価が割安")
    if L["trend"] >= 62: good.append("需要の追い風が強い")
    if L["health"] >= 62: good.append("財務が堅い")
    if not good: good.append("突出した強みは限定的")

    for it in sorted(r["risk_items"], key=lambda x: -x["points"])[:1]:
        bad.append(f"{it['name']}に注意（{it['why']}）")
    if r["price_caps"]:
        bad.append("価格面の割高条件に該当：" + "・".join(r["price_caps"][:1]))
    if not bad:
        bad.append("大きな減点要因は検出されていない")

    return "、".join(good[:2]) + "。ただし" + bad[0] + "。"


def build_theme_guide(node_id: str, rows: List[dict], node_state: Dict[str, dict],
                      opp: Dict[str, dict], as_of: str, top_n: int = 5) -> dict:
    node = NODE_MAP[node_id]
    st = node_state.get(node_id, {})
    op = opp.get(node_id, {})
    rates = get_rates()

    members = [r for r in rows if r["nodes"].get(node_id, 0) > 0]
    members.sort(key=lambda r: -(r["final_score"] + r["nodes"][node_id] * 12))
    top = members[:top_n]

    # 実証現場・拠点（重複除去して最大6件）
    sites: List[str] = []
    for r in members:
        for s in r["sites"]:
            if s not in sites:
                sites.append(s)
    sites = sites[:6]

    paths = [chain_label(p) for p in paths_to(node_id)]
    paths = sorted(set(paths), key=len, reverse=True)[:3]

    table = []
    for i, r in enumerate(top, 1):
        table.append({
            "rank": i,
            "ticker": r["ticker"], "name": r["name"], "region": r["region"],
            "price": r["price"], "currency": r["currency"],
            "entry_low": r["entry_low"], "entry_high": r["entry_high"],
            "lot": r["lot"],
            "min_investment": r["min_investment"],
            "min_investment_jpy": round(to_jpy(r["min_investment"], r["currency"], rates)),
            "div_yield": r["div_yield"], "yutai": r["yutai"],
            "stars": r["stars"], "stars_text": _stars(r["stars"]),
            "final_score": r["final_score"],
            "company_grade": r["company_grade"], "price_grade": r["price_grade"],
            "verdict_label": r["verdict_label"],
            "biz": r["biz"],
            "exposure": round(r["nodes"][node_id], 2),
            "comment": _eval_comment(r),
        })

    budgets = [allocate(top, b, max_names=min(3, len(top))) for b in GUIDE_BUDGETS]

    why: List[str] = [node.desc]
    ev_lines = []
    for d in st.get("drivers", [])[:2]:
        ev_lines.append(f"{d['from_label']} からの波及（伝播係数 {d['elasticity']:.2f}／"
                        f"遅れ {d['lag_months']:.0f}ヶ月）{('：' + d['note']) if d['note'] else ''}")
    why += ev_lines
    why.append(f"実需エビデンス水準 {st.get('evidence', 0):.0f}／100、"
               f"3ヶ月変化 {st.get('momentum', 0):+.0f}pt、需要圧力 {st.get('pressure', 0):.0f}")
    if op:
        why.append(f"株価の織り込み度は {op.get('priced_in', 0):.0f}、"
                   f"未織り込みギャップは {op.get('unpriced_gap', 0):+.0f}")

    return {
        "node": node_id,
        "title": f"{node.label} 関連銘柄 投資ガイド",
        "subtitle": f"需要連鎖から抽出した注目銘柄 TOP{len(top)}",
        "as_of": as_of,
        "desc": node.desc,
        "why": why,
        "chains": paths,
        "signals": [SIGNAL_LABELS[s] for s in node.signals],
        "sites": sites,
        "pressure": st.get("pressure", 0),
        "evidence": st.get("evidence", 0),
        "unpriced_gap": op.get("unpriced_gap", 0),
        "depth": st.get("depth", 0),
        "table": table,
        "budget_examples": budgets,
        "beginner_points": [
            "低位株＝割安ではない。株価の絶対値ではなく、利益や資産に対する倍率（PER・PBR）と成長率で見る。",
            "「良い会社」と「良い株価」を分けて見る。企業評価がSでも価格評価がCなら、今日買う理由にはならない。",
            "需要の追い風は決算の受注残・設備投資・リードタイムなど事実で確認する。話題性だけで判断しない。",
        ],
        "cautions": [
            "小型株は値動きが大きく、流動性が低い場合がある。余裕資金で行うこと。",
            "本ガイドの数値はスクリーニングの出力であり、個別銘柄の売買推奨ではない。",
            "優待・配当の内容は変更されることがある。必ず各社IRの一次情報を確認すること。",
        ],
    }


def build_all_guides(rows: List[dict], node_state: Dict[str, dict],
                     opp_rows: List[dict], as_of: str, limit: int = 30,
                     min_members: int = 2) -> List[dict]:
    """
    未織り込みギャップ順に、該当企業が min_members 社以上あるノードのガイドを作る。
    需要マップのノードをクリックして「ガイドがない」に当たる確率を下げるため、
    ドライバー以外のノードもできる限り網羅する。
    """
    opp = {o["id"]: o for o in opp_rows}
    seen = {o["id"] for o in opp_rows}
    order = [o["id"] for o in opp_rows] + [n for n in node_state if n not in seen]

    guides = []
    for nid in order:
        if len(guides) >= limit:
            break
        if node_state.get(nid, {}).get("is_driver"):
            continue
        members = [r for r in rows if r["nodes"].get(nid, 0) > 0]
        if len(members) < min_members:
            continue
        guides.append(build_theme_guide(nid, rows, node_state, opp, as_of))
    return guides
