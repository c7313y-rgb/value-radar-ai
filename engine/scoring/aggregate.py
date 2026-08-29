# -*- coding: utf-8 -*-
"""
VALUE SCORE の合成と、最終推奨点の算出

  VALUE SCORE   = Σ(レイヤー得点 × 配点) / 100
  最終推奨点     = VALUE SCORE × 確信度 − Risk Penalty ＋ 議長調整

そして「良い会社 ≠ 良い株価」を守るために、
  企業評価グレード（Quality/Growth/Governance/Trend）
  価格評価グレード（Value ＋ 割高キャップ）
を必ず分けて出す。Quality S でも PER 80倍・FCF利回り1%なら価格評価は C になる。
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple

from .layers import (LAYER_WEIGHTS, LAYER_LABELS, quality, value, growth, health,
                     momentum_with_extension, governance, diversification)
from .normalize import PeerNormalizer
from .risk import risk_penalty, confidence
from .valuation import fair_value, implied_growth_years, entry_zone
from ..committee.agents import run_committee
from ..committee.narrator import reason

GRADE_BANDS = [(78, "S"), (68, "A"), (57, "B"), (45, "C"), (0, "D")]


def to_grade(score: float) -> str:
    for th, g in GRADE_BANDS:
        if score >= th:
            return g
    return "D"


def price_grade_of(value_score: float, f) -> Tuple[str, List[str]]:
    """価格評価。割高の絶対条件に触れた場合はグレードに上限を課す。"""
    g = to_grade(value_score)
    caps: List[str] = []
    order = ["S", "A", "B", "C", "D"]

    def cap(limit: str, why: str) -> None:
        nonlocal g
        if order.index(g) < order.index(limit):
            g = limit
        caps.append(why)

    if f.per > 80:
        cap("D", f"PER {f.per:.0f}倍（80倍超）")
    elif f.per > 55:
        cap("C", f"PER {f.per:.0f}倍（55倍超）")
    if f.peg > 3.5:
        cap("C", f"PEG {f.peg:.1f}（3.5超）")
    if 0 < f.fcf_yield < 1.0:
        cap("C", f"FCF利回り {f.fcf_yield:.1f}%（1%未満）")
    if f.ev_ebitda > 40:
        cap("C", f"EV/EBITDA {f.ev_ebitda:.0f}倍")
    return g, caps


def verdict_of(final: float, company_grade: str, price_grade: str) -> Tuple[str, str]:
    order = ["S", "A", "B", "C", "D"]
    cg, pg = order.index(company_grade), order.index(price_grade)
    if final >= 68 and cg <= 1 and pg <= 1:
        return "STRONG_CANDIDATE", "本日の有力候補"
    if final >= 58 and pg <= 2:
        return "CANDIDATE", "検討候補"
    if cg <= 1 and pg >= 3:
        return "QUALITY_WAIT", "良い会社・価格待ち"
    if final >= 48:
        return "WATCH", "監視"
    return "PASS", "見送り"


def stars_of(final: float, risk_pts: float, f, company) -> int:
    """初心者向けの★（1〜5）。得点だけでなく、値動きと流動性で割り引く。"""
    s = final
    if f.vol_ann > 0.45: s -= 6
    if f.vol_ann > 0.60: s -= 6
    if company.mcap_musd < 3000: s -= 6
    if f.adv_musd < 30: s -= 4
    if risk_pts > 12: s -= 5
    if s >= 72: return 5
    if s >= 62: return 4
    if s >= 52: return 3
    if s >= 42: return 2
    return 1


def evaluate_universe(companies, fund: Dict[str, object], node_state: Dict[str, dict],
                      opp_index: Dict[str, dict], as_of: str, synthetic: bool) -> List[dict]:
    from ..demand.propagation import company_trend_score
    from ..demand.graph import paths_to, chain_label, NODE_MAP

    tickers = [c.ticker for c in companies if c.ticker in fund]
    cmap = {c.ticker: c for c in companies}

    rows_metrics: Dict[str, dict] = {}
    meta: Dict[str, dict] = {}
    for t in tickers:
        f = fund[t]
        d = f.to_dict()
        rows_metrics[t] = {k: (None if v in (0, 0.0) and k in _NULLABLE else v)
                           for k, v in d.items() if isinstance(v, (int, float))}
        meta[t] = {"sector": cmap[t].sector, "region": cmap[t].region}

    norm = PeerNormalizer(rows_metrics, meta)

    # ポートフォリオ文脈（世界分散適合度の基準）
    n = len(tickers) or 1
    region_share: Dict[str, float] = {}
    sector_share: Dict[str, float] = {}
    for t in tickers:
        region_share[cmap[t].region] = region_share.get(cmap[t].region, 0) + 1 / n
        sector_share[cmap[t].sector] = sector_share.get(cmap[t].sector, 0) + 1 / n
    pctx = {"region_share": region_share, "sector_share": sector_share}

    out: List[dict] = []
    for t in tickers:
        c, f = cmap[t], fund[t]

        q_s, q_c, q_d = quality(norm, t)
        v_s, v_c, v_d = value(norm, t)
        g_s, g_c, g_d = growth(norm, t)
        h_s, h_c, h_d = health(norm, t)
        m_s, m_c, m_d = momentum_with_extension(norm, t, f)
        gv_s, gv_c, gv_d = governance(norm, t)
        dv_s, dv_c, dv_d = diversification(c, pctx)
        tr_s, tr_detail = company_trend_score(c.nodes, node_state, opp_index)

        layers = {"quality": q_s, "value": v_s, "growth": g_s, "health": h_s,
                  "momentum": m_s, "diversification": dv_s, "governance": gv_s,
                  "trend": tr_s}
        layer_cov = {"quality": q_c, "value": v_c, "growth": g_c, "health": h_c,
                     "momentum": m_c, "diversification": dv_c, "governance": gv_c,
                     "trend": 1.0}
        layer_detail = {"quality": q_d, "value": v_d, "growth": g_d, "health": h_d,
                        "momentum": m_d, "diversification": dv_d, "governance": gv_d}

        value_score = sum(layers[k] * w for k, w in LAYER_WEIGHTS.items()) / 100.0

        # ピア中央値（説明用）
        _, peers = norm.group_for(t)
        pers = sorted(fund[p].per for p in peers if p in fund and fund[p].per > 0)
        fcys = sorted(fund[p].fcf_yield for p in peers if p in fund and fund[p].fcf_yield > 0)
        peer_per = pers[len(pers) // 2] if pers else 0.0
        peer_fcy = fcys[len(fcys) // 2] if fcys else 0.0

        fv, methods = fair_value(f, peer_per, peer_fcy, q_s, g_s)
        upside = (fv / f.price - 1.0) * 100.0 if f.price else 0.0
        implied = implied_growth_years(f)

        risk_pts, risk_items = risk_penalty(f, c, layers, c.nodes)

        top_chain = ""
        if tr_detail:
            ps = paths_to(tr_detail[0]["node"])
            if ps:
                longest = max(ps, key=len)
                top_chain = chain_label(longest)

        ctx = {
            "f": f, "company": c, "layers": layers, "trend_detail": tr_detail,
            "risk_points": risk_pts, "risk_items": risk_items,
            "upside_pct": upside, "implied_years": implied,
            "value_pct": norm.percentile(t, "per", -1) or 50.0,
            "top_chain": top_chain,
        }
        committee = run_committee(ctx)

        conf, conf_parts = confidence(f, layer_cov, committee, synthetic)
        final = value_score * conf - risk_pts + committee["chair_adjustment"]
        final = max(0.0, min(100.0, final))

        company_score = (0.32 * q_s + 0.20 * g_s + 0.26 * gv_s + 0.22 * tr_s)
        cgrade = to_grade(company_score)
        pgrade, caps = price_grade_of(v_s, f)
        vkey, vlabel = verdict_of(final, cgrade, pgrade)
        lo, hi = entry_zone(fv, f.price, risk_pts, c.currency)

        row = {
            "ticker": t, "name": c.name, "name_en": c.name_en,
            "region": c.region, "country": c.country, "currency": c.currency,
            "exchange": c.exchange, "sector": c.sector, "industry": c.industry,
            "biz": c.biz, "sites": c.sites, "lot": c.lot,
            "yutai": c.yutai, "div_yield": f.div_yield,
            "as_of": as_of,
            "price": f.price, "prev_close": f.prev_close,
            "change_pct": round((f.price / f.prev_close - 1) * 100, 2) if f.prev_close else 0.0,
            "min_investment": round(f.price * c.lot, 2),
            "fair_value": round(fv, 2), "fair_methods": methods,
            "upside_pct": round(upside, 1),
            "entry_low": lo, "entry_high": hi,
            "implied_years": round(implied, 1) if implied else None,
            "value_score": round(value_score, 1),
            "confidence": conf, "confidence_parts": conf_parts,
            "risk_points": round(risk_pts, 1), "risk_items": risk_items,
            "final_score": round(final, 1),
            "layers": {k: round(v, 1) for k, v in layers.items()},
            "layer_detail": layer_detail,
            "layer_coverage": {k: round(v, 2) for k, v in layer_cov.items()},
            "company_score": round(company_score, 1),
            "company_grade": cgrade, "price_grade": pgrade, "price_caps": caps,
            "verdict": vkey, "verdict_label": vlabel,
            "stars": stars_of(final, risk_pts, f, c),
            "committee": committee,
            "trend_detail": tr_detail, "top_chain": top_chain,
            "peer_median_per": round(peer_per, 1),
            "peer_median_fcf_yield": round(peer_fcy, 2),
            "peer_group": norm.group_for(t)[0],
            "nodes": c.nodes,
            "f": f.to_dict(),
        }
        row["reason"] = reason(row)
        out.append(row)

    out.sort(key=lambda r: -r["final_score"])
    for i, r in enumerate(out, 1):
        r["rank"] = i
    return out


# 0 を「欠損」とみなしてよい指標（0が正当な値になり得るものは除外する）
_NULLABLE = {
    "roe", "roic", "op_margin", "fcf_margin", "earnings_stability",
    "per", "forward_per", "pbr", "ev_ebitda", "fcf_yield", "peg",
    "rev_cagr3", "eps_cagr3", "fcf_cagr3",
    "de_ratio", "current_ratio", "interest_coverage",
    "moat_score", "governance_score", "capital_allocation",
    "culture_engagement", "ir_dialogue", "adv_musd",
}
