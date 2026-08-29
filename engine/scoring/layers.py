# -*- coding: utf-8 -*-
"""
VALUE SCORE の8レイヤー

  企業品質 Quality        20
  割安度   Value          20
  成長     Growth         15
  財務健全性 Health       10
  株価・需給 Momentum     10
  世界分散適合度 Diversify  5
  経営・競争力 Governance  10
  未来需要 Trend          10
                        ----
                         100

「良い会社 ≠ 良い株価」を保つため、Value レイヤーは他と独立に評価し、
最後に企業評価グレードと価格評価グレードを分けて出力する（aggregate.py）。
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple

from .normalize import PeerNormalizer, weighted_layer, logistic_score

LAYER_WEIGHTS = {
    "quality": 20.0,
    "value": 20.0,
    "growth": 15.0,
    "health": 10.0,
    "momentum": 10.0,
    "diversification": 5.0,
    "governance": 10.0,
    "trend": 10.0,
}

LAYER_LABELS = {
    "quality": "企業品質",
    "value": "割安度",
    "growth": "成長",
    "health": "財務健全性",
    "momentum": "株価・需給",
    "diversification": "世界分散適合度",
    "governance": "経営・競争力",
    "trend": "未来需要",
}

# (metric, direction, weight)
QUALITY_METRICS = [("roe", 1, 0.26), ("roic", 1, 0.26), ("op_margin", 1, 0.18),
                   ("fcf_margin", 1, 0.18), ("earnings_stability", 1, 0.12)]
VALUE_METRICS = [("per", -1, 0.20), ("forward_per", -1, 0.20), ("pbr", -1, 0.12),
                 ("ev_ebitda", -1, 0.16), ("fcf_yield", 1, 0.20), ("peg", -1, 0.12)]
GROWTH_METRICS = [("rev_cagr3", 1, 0.26), ("eps_cagr3", 1, 0.28), ("fcf_cagr3", 1, 0.20),
                  ("margin_trend", 1, 0.14), ("eps_revision_3m", 1, 0.12)]
HEALTH_METRICS = [("de_ratio", -1, 0.28), ("net_debt_ebitda", -1, 0.30),
                  ("current_ratio", 1, 0.20), ("interest_coverage", 1, 0.22)]
MOMENTUM_METRICS = [("mom_1m", 1, 0.15), ("mom_3m", 1, 0.25), ("mom_6m", 1, 0.25),
                    ("mom_12m", 1, 0.20), ("volume_ratio", 1, 0.15)]
GOVERNANCE_METRICS = [("moat_score", 1, 0.30), ("governance_score", 1, 0.22),
                      ("capital_allocation", 1, 0.22), ("culture_engagement", 1, 0.13),
                      ("ir_dialogue", 1, 0.13)]


def _layer(norm: PeerNormalizer, ticker: str, metrics) -> Tuple[float, float, List[dict]]:
    parts = [(m, norm.score(ticker, m, d), w) for (m, d, w) in metrics]
    return weighted_layer(parts)


def quality(norm, t):        return _layer(norm, t, QUALITY_METRICS)
def value(norm, t):          return _layer(norm, t, VALUE_METRICS)
def growth(norm, t):         return _layer(norm, t, GROWTH_METRICS)
def health(norm, t):         return _layer(norm, t, HEALTH_METRICS)
def momentum_layer(norm, t): return _layer(norm, t, MOMENTUM_METRICS)
def governance(norm, t):     return _layer(norm, t, GOVERNANCE_METRICS)


def momentum_with_extension(norm, ticker: str, f) -> Tuple[float, float, List[dict]]:
    """
    需給レイヤーには「52週高値からの距離」を加える。
    ただし高値圏そのものは減点しない（トレンドフォローを完全に否定しない）。
    高値から離れすぎている＝需給が壊れている場合のみ緩やかに減点する。
    """
    s, cov, detail = momentum_layer(norm, ticker)
    d = f.dist_52w_high
    penalty = 0.0
    if d < -35.0:
        penalty = min(12.0, (abs(d) - 35.0) * 0.35)
    s = max(0.0, s - penalty)
    if penalty:
        detail.append({"metric": "dist_52w_high", "score": round(100 - penalty * 4, 1), "weight": 0.0})
    return s, cov, detail


def diversification(company, portfolio_ctx: Optional[dict] = None) -> Tuple[float, float, List[dict]]:
    """
    世界分散適合度。
    「その銘柄を1つ足したときに、世界分散ポートフォリオとしての形が良くなるか」を見る。
    デモでは (地域, 通貨, 業種, 時価総額帯) の希少性で近似する。
    実運用では既存保有との相関・寄与リスクに置き換える差し替え点。
    """
    ctx = portfolio_ctx or {}
    region_share = ctx.get("region_share", {}).get(company.region, 0.25)
    sector_share = ctx.get("sector_share", {}).get(company.sector, 0.15)
    # シェアが小さい（＝まだ持っていない領域）ほど高得点
    region_s = logistic_score((0.30 - region_share) / 0.15)
    sector_s = logistic_score((0.18 - sector_share) / 0.10)
    size = company.mcap_musd
    size_s = 70.0 if 5_000 <= size <= 300_000 else (55.0 if size > 300_000 else 62.0)
    fx_s = 62.0 if company.currency != "USD" else 48.0
    score = region_s * 0.35 + sector_s * 0.30 + size_s * 0.20 + fx_s * 0.15
    detail = [
        {"metric": "region_fit", "score": round(region_s, 1), "weight": 0.35},
        {"metric": "sector_fit", "score": round(sector_s, 1), "weight": 0.30},
        {"metric": "size_fit", "score": round(size_s, 1), "weight": 0.20},
        {"metric": "currency_fit", "score": round(fx_s, 1), "weight": 0.15},
    ]
    return score, 1.0, detail
