# -*- coding: utf-8 -*-
"""プロバイダの選択。環境変数 VR_PROVIDER / VR_EVIDENCE_PROVIDER で切り替える。"""

from __future__ import annotations
import os
from typing import Tuple

from .base import ProviderError
from .demo_provider import DemoProvider, DemoEvidenceProvider


def get_market_provider(name: str | None = None, fallback_demo: bool = False):
    name = (name or os.getenv("VR_PROVIDER", "demo")).lower()
    try:
        if name == "demo":
            return DemoProvider()
        if name == "yfinance":
            from .yfinance_provider import YFinanceProvider
            return YFinanceProvider()
        if name == "premium":
            from .premium_provider import PremiumProvider
            return PremiumProvider()
        raise ProviderError(f"未知のプロバイダ: {name}")
    except Exception as e:
        if fallback_demo:
            print(f"[warn] provider '{name}' の初期化に失敗しました: {e} → demo へ退避します")
            return DemoProvider()
        raise


def get_evidence_provider(name: str | None = None, fallback_demo: bool = False):
    name = (name or os.getenv("VR_EVIDENCE_PROVIDER", "demo")).lower()
    if name == "demo":
        return DemoEvidenceProvider()
    if fallback_demo:
        print(f"[warn] evidence provider '{name}' は未実装 → demo へ退避します")
        return DemoEvidenceProvider()
    raise ProviderError(
        f"evidence provider '{name}' は未実装です。"
        " ニュース／特許／求人／政府予算のAPIを繋ぐ場合は EvidenceProvider を実装してください。"
    )


def describe(mp, ep) -> Tuple[str, bool]:
    synthetic = bool(getattr(mp, "is_synthetic", True) or getattr(ep, "is_synthetic", True))
    return f"market={mp.name}, evidence={ep.name}", synthetic
