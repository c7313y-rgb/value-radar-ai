# -*- coding: utf-8 -*-
"""
為替レート（1通貨あたりの円）

デモは固定レート。実運用では為替APIに差し替える（ここも1関数の差し替えで済む）。
最低投資額と予算配分は必ず円換算で出す。海外株を「株価だけ」で見せると、
実際にいくら必要なのかが分からないため。
"""

from __future__ import annotations
import os
from typing import Dict

DEMO_RATES_JPY: Dict[str, float] = {
    "JPY": 1.0,
    "USD": 152.0,
    "EUR": 166.0,
    "CHF": 178.0,
    "KRW": 0.108,
    "TWD": 4.8,
    "GBP": 195.0,
}


def get_rates() -> Dict[str, float]:
    src = os.getenv("VR_FX_PROVIDER", "demo").lower()
    if src == "demo":
        return dict(DEMO_RATES_JPY)
    raise NotImplementedError(
        f"FX provider '{src}' は未実装です。engine/output/fx.py に実装を追加してください。"
    )


def to_jpy(amount: float, currency: str, rates: Dict[str, float] | None = None) -> float:
    r = rates or get_rates()
    return amount * r.get(currency, 1.0)
