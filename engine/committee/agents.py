# -*- coding: utf-8 -*-
"""
AI投資委員会（6エージェント）

単一のモデルに「買いか売りか」を答えさせない。
役割の違う6人に別々の目的関数で評価させ、最後に議長役が反対意見ごと読む。
特に Contrarian は「他の5人が賛成しているときほど厳しく反論する」設計にしてある。

各エージェントは必ず (スタンス, 確信度, 根拠テキスト, 参照した数値) を返す。
根拠のない結論は出力できない構造にしている。
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

STANCE_VALUE = {"STRONG_BUY": 2, "BUY": 1, "HOLD": 0, "AVOID": -1, "STRONG_AVOID": -2}
STANCE_LABEL = {
    "STRONG_BUY": "強く支持", "BUY": "支持", "HOLD": "中立",
    "AVOID": "反対", "STRONG_AVOID": "強く反対",
}


@dataclass
class AgentView:
    agent: str
    role: str
    stance: str
    conviction: float          # 0-1
    comment: str
    evidence: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["stance_label"] = STANCE_LABEL[self.stance]
        return d


def _stance(score: float, hi: float = 72, mid: float = 60, lo: float = 45, vlo: float = 33) -> str:
    if score >= hi:  return "STRONG_BUY"
    if score >= mid: return "BUY"
    if score >= lo:  return "HOLD"
    if score >= vlo: return "AVOID"
    return "STRONG_AVOID"


# ---------------------------------------------------------------------------

def value_analyst(ctx) -> AgentView:
    f, L = ctx["f"], ctx["layers"]
    s = L["value"]
    fv_up = ctx["upside_pct"]
    comment = (f"PER {f.per:.0f}倍・PBR {f.pbr:.1f}倍・FCF利回り {f.fcf_yield:.1f}%。"
               f"同業同地域のピア内で割安度は上位 {100 - ctx['value_pct']:.0f}% 圏。"
               f"三手法平均の適正価値に対する上値余地は {fv_up:+.0f}%。")
    if f.peg > 0:
        comment += f" PEG {f.peg:.1f}。"
    conv = min(1.0, 0.35 + abs(s - 50) / 60.0)
    return AgentView("Value Analyst", "割安度", _stance(s), conv, comment,
                     {"per": f.per, "fcf_yield": f.fcf_yield, "upside_pct": fv_up})


def growth_analyst(ctx) -> AgentView:
    f, L = ctx["f"], ctx["layers"]
    s = L["growth"] * 0.7 + L["quality"] * 0.3
    comment = (f"売上3年CAGR {f.rev_cagr3:+.0f}%、EPS {f.eps_cagr3:+.0f}%、FCF {f.fcf_cagr3:+.0f}%。"
               f"営業利益率トレンドは {f.margin_trend:+.1f}pt、予想改定率は3ヶ月で {f.eps_revision_3m:+.0f}%。")
    if f.margin_trend < -1.0:
        comment += " 売上は伸びても利益率が劣化しており、成長の質に懸念がある。"
    conv = min(1.0, 0.35 + abs(s - 50) / 55.0)
    return AgentView("Growth Analyst", "成長", _stance(s), conv, comment,
                     {"rev_cagr3": f.rev_cagr3, "eps_cagr3": f.eps_cagr3})


def macro_analyst(ctx) -> AgentView:
    f, L, c = ctx["f"], ctx["layers"], ctx["company"]
    s = L["diversification"] * 0.4 + L["health"] * 0.35 + L["momentum"] * 0.25
    rate_sensitive = f.net_debt_ebitda > 2.5 or c.sector in ("公益", "不動産")
    comment = (f"{c.country}／{c.currency}建て、{c.sector}セクター。"
               f"ネット負債/EBITDA {f.net_debt_ebitda:.1f}倍。")
    if rate_sensitive:
        comment += " 金利上昇局面では相対的に逆風を受けやすい構造。"
        s -= 6
    else:
        comment += " 金利感応度は相対的に低い。"
    if c.region != "US":
        comment += " 為替は米ドル一極への集中を薄める効果がある。"
    conv = 0.45
    return AgentView("Macro Analyst", "マクロ・分散", _stance(s), conv, comment,
                     {"net_debt_ebitda": f.net_debt_ebitda})


def technology_analyst(ctx) -> AgentView:
    L, td = ctx["layers"], ctx["trend_detail"]
    s = L["trend"] * 0.75 + L["governance"] * 0.25
    if td:
        top = td[0]
        chain = ctx.get("top_chain", "")
        comment = (f"主要な需要接点は「{top['label']}」（露出度 {top['exposure']:.0%}、"
                   f"需要圧力 {top['pressure']:.0f}、未織り込みギャップ {top['unpriced_gap']:+.0f}）。")
        if chain:
            comment += f" 因果経路は {chain}。"
        if len(td) > 1:
            comment += f" 次点は「{td[1]['label']}」。"
    else:
        comment = "明確な需要テーマへの接続が確認できない。構造的な追い風は限定的。"
        s = min(s, 45)
    conv = min(1.0, 0.4 + abs(s - 50) / 55.0)
    return AgentView("Technology Analyst", "技術・需要連鎖", _stance(s), conv, comment,
                     {"trend": L["trend"]})


def risk_analyst(ctx) -> AgentView:
    f = ctx["f"]
    pen, items = ctx["risk_points"], ctx["risk_items"]
    s = 100.0 - pen * 3.6
    top = sorted(items, key=lambda x: -x["points"])[:2]
    if top:
        comment = "主なリスクは " + "、".join(f"{i['name']}（{i['why']}）" for i in top) + "。"
    else:
        comment = "定量的に検出される固有リスクは小さい。"
    comment += f" 減点は合計 {pen:.1f}点。年率ボラティリティ {f.vol_ann*100:.0f}%。"
    conv = min(1.0, 0.45 + pen / 25.0 * 0.5)
    return AgentView("Risk Analyst", "リスク", _stance(s, 78, 66, 52, 38), conv, comment,
                     {"risk_points": pen, "vol_ann": f.vol_ann})


def contrarian_analyst(ctx) -> AgentView:
    """
    他の5人の賛成が強いほど厳しく反論する役。
    「成長は本物だが、価格がすでに何年先まで織り込んでいるか」を突く。
    """
    f = ctx["f"]
    others = ctx["others_mean_stance"]     # -2..2
    implied = ctx["implied_years"]
    s = 55.0

    reasons: List[str] = []
    if implied is not None and implied > 5.0:
        s -= min(30.0, (implied - 5.0) * 4.0)
        reasons.append(f"現在のPER {f.per:.0f}倍は、EPS成長率 {f.eps_cagr3:.0f}% が続く前提で"
                       f"約{implied:.0f}年先の利益まで既に織り込んでいる")
    if f.mom_12m > 70:
        s -= min(12.0, (f.mom_12m - 70) * 0.12)
        reasons.append(f"12ヶ月で {f.mom_12m:+.0f}% 上昇しており、需給が一方向に傾いている")
    if f.peg > 2.5:
        s -= min(10.0, (f.peg - 2.5) * 4.0)
        reasons.append(f"PEG {f.peg:.1f} は成長を勘案しても割高圏")
    if 0 < f.fcf_yield < 1.5:
        s -= 8.0
        reasons.append(f"FCF利回り {f.fcf_yield:.1f}% では、成長が鈍化した瞬間に支えがない")
    if f.margin_trend < -1.0:
        s -= 6.0
        reasons.append(f"営業利益率が3年で {f.margin_trend:+.1f}pt 悪化しており、"
                       "需要の強さが利益に変換できていない")
    if ctx["layers"]["value"] > 65 and ctx["layers"]["quality"] > 60:
        s += 12.0
        reasons.append("品質の割に価格が抑えられており、逆張りの余地はむしろこちら側にある")

    # 賛成が強いほど基準を上げる（同調圧力への対抗）
    s -= max(0.0, others) * 4.0

    if not reasons:
        reasons.append("突出した過熱・織り込み過剰は検出されない")
    comment = "／".join(reasons) + "。"
    conv = min(1.0, 0.4 + abs(s - 55) / 45.0)
    return AgentView("Contrarian Analyst", "反対仮説", _stance(s, 70, 58, 44, 32), conv, comment,
                     {"implied_years": implied or 0.0, "mom_12m": f.mom_12m})


AGENTS = [value_analyst, growth_analyst, macro_analyst,
          technology_analyst, risk_analyst]


def run_committee(ctx) -> dict:
    views = [fn(ctx) for fn in AGENTS]
    mean_stance = sum(STANCE_VALUE[v.stance] * v.conviction for v in views) / \
                  max(sum(v.conviction for v in views), 1e-6)
    ctx["others_mean_stance"] = mean_stance
    contra = contrarian_analyst(ctx)
    views.append(contra)

    vals = [STANCE_VALUE[v.stance] for v in views]
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    agreement = max(0.0, 1.0 - var / 2.6)      # 分散が大きいほど一致度が下がる

    # 議長役：反対意見の重みを明示的に扱う
    adj = 0.0
    dissent = None
    if contra.stance in ("AVOID", "STRONG_AVOID") and contra.conviction >= 0.6 and mean_stance > 0.4:
        adj = -(contra.conviction * 6.0)
        dissent = (f"5名が前向きな一方、Contrarian Analyst が確信度 {contra.conviction:.0%} で反論。"
                   f"{contra.comment} 議長はこの反論を採用し、最終点を {adj:.1f}点 調整した。")
    elif contra.stance in ("STRONG_BUY", "BUY") and mean_stance < -0.2:
        adj = contra.conviction * 3.0
        dissent = (f"多数が慎重な一方、Contrarian Analyst は逆張り機会と判断（確信度 "
                   f"{contra.conviction:.0%}）。{contra.comment}")

    return {
        "views": [v.to_dict() for v in views],
        "mean_stance": round(mean, 2),
        "agreement": round(agreement, 3),
        "chair_adjustment": round(adj, 2),
        "dissent": dissent,
        "vote": {STANCE_LABEL[k]: sum(1 for v in views if v.stance == k)
                 for k in STANCE_VALUE if any(v.stance == k for v in views)},
    }
