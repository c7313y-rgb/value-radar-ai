# -*- coding: utf-8 -*-
"""
適正価値（フェアバリュー）と購入検討価格帯

単一手法は必ず外すので、3つの独立した見方を加重平均する。
  A. ピア相対PER法   … 同業・同地域の妥当PERに、品質と成長で補正をかける
  B. FCF利回り法     … 要求FCF利回りまで価格が調整されるべき、という見方
  C. 成長織り込み法  … PEG=1.5 を妥当上限とみなす見方

さらに「今の株価がすでに何年分の成長を織り込んでいるか（implied years）」を出す。
これは Contrarian Analyst の主要な反論材料になる。
"""

from __future__ import annotations
import math
from typing import Dict, Optional, Tuple


def _round_tick(price: float, currency: str) -> float:
    if currency == "JPY":
        if price >= 10000: return round(price / 10) * 10
        if price >= 1000:  return round(price / 5) * 5
        return round(price)
    if currency == "KRW":
        return round(price / 100) * 100
    return round(price, 2)


def fair_value(f, peer_median_per: float, peer_median_fcfy: float,
               quality_score: float, growth_score: float) -> Tuple[float, Dict[str, float]]:
    px = f.price
    methods: Dict[str, float] = {}

    # A. ピア相対PER法
    if f.per > 0 and peer_median_per > 0:
        q_adj = 1.0 + (quality_score - 50.0) / 100.0 * 0.55   # 高品質はプレミアム容認
        g_adj = 1.0 + (growth_score - 50.0) / 100.0 * 0.45
        fair_per = peer_median_per * q_adj * g_adj
        methods["peer_per"] = px * (fair_per / f.per)

    # B. FCF利回り法
    if f.fcf_yield > 0.05 and peer_median_fcfy > 0.05:
        target = peer_median_fcfy * (1.0 - (quality_score - 50.0) / 100.0 * 0.35)
        target = max(target, 0.8)
        methods["fcf_yield"] = px * (f.fcf_yield / target)

    # C. 成長織り込み法（PEG 1.5 を妥当上限）
    if f.per > 0 and f.eps_cagr3 > 2.0:
        fair_per = min(f.eps_cagr3 * 1.5, 55.0)
        methods["peg"] = px * (fair_per / f.per)

    if not methods:
        return px, {}

    # 各手法を個別にクリップしてから合成する。
    # 1つの手法（特にPEG法は高成長時に発散しやすい）が全体を支配するのを防ぐ。
    methods = {k: max(px * 0.40, min(px * 2.20, v)) for k, v in methods.items()}

    w = {"peer_per": 0.45, "fcf_yield": 0.30, "peg": 0.25}
    tw = sum(w[k] for k in methods)
    fv = sum(v * w[k] for k, v in methods.items()) / tw
    # 極端な値は切る（モデルの誤差を利益に見せない）
    fv = max(px * 0.40, min(px * 2.00, fv))
    return fv, {k: round(v, 2) for k, v in methods.items()}


def implied_growth_years(f, base_per: float = 18.0) -> Optional[float]:
    """
    現在のPERが、EPS成長率で何年ぶん先の利益を先取りしているか。
    PER_now / (1+g)^n = base_per を解く。Contrarian の反論に使う。
    """
    if f.per <= 0 or f.eps_cagr3 <= 1.0 or f.per <= base_per:
        return None
    g = f.eps_cagr3 / 100.0
    try:
        return math.log(f.per / base_per) / math.log(1.0 + g)
    except (ValueError, ZeroDivisionError):
        return None


def entry_zone(fair: float, price: float, risk_pts: float, currency: str) -> Tuple[float, float]:
    """
    購入検討価格帯。リスクが大きいほど大きな安全域（margin of safety）を要求する。
    上限は「適正価値からこれだけ引いた水準」、下限はその 9割。
    現在株価がすでに帯の下なら、帯は現在株価近傍へ寄せる。
    """
    mos = 0.18 + min(risk_pts, 25.0) / 25.0 * 0.22      # 18%〜40%
    hi = fair * (1.0 - mos)
    lo = hi * 0.90
    if price < lo:
        hi, lo = price * 1.03, price * 0.93
    return _round_tick(lo, currency), _round_tick(hi, currency)
