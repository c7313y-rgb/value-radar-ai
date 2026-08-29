# -*- coding: utf-8 -*-
"""
有料データ層への接続スタブ（Bloomberg / LSEG(Refinitiv) / S&P Capital IQ /
FactSet / Morningstar / MSCI）

投資判定の運用フェーズに入った時点で、ここに実装を足すだけでエンジン側は
一切変更せずに精緻な指標へ切り替わる、という差し替え点を明示するためのファイル。

    VR_PROVIDER=premium VR_PREMIUM_VENDOR=lseg VR_PREMIUM_KEY=xxxx \
        python -m engine.pipeline

各ベンダのフィールド対応表は docs/DATA_PROVIDERS.md を参照。
未実装の状態で呼ぶと ProviderError を投げ、pipeline は --fallback-demo が
指定されていればデモへ退避する（本番では退避させないこと）。
"""

from __future__ import annotations
import os
from typing import Dict, List

from .base import Fundamentals, ProviderError

# ベンダごとの「エンジン側フィールド → ベンダ側フィールド」対応表。
# 実装時はこのマップだけを埋めれば済むようにしてある。
FIELD_MAP = {
    "bloomberg": {
        "roe": "RETURN_COM_EQY", "roic": "RETURN_ON_INV_CAPITAL",
        "op_margin": "OPER_MARGIN", "per": "PE_RATIO",
        "forward_per": "BEST_PE_RATIO", "pbr": "PX_TO_BOOK_RATIO",
        "ev_ebitda": "CURRENT_EV_TO_T12M_EBITDA", "fcf_yield": "FREE_CASH_FLOW_YIELD",
        "eps_revision_3m": "BEST_EPS_3MO_CHG", "net_debt_ebitda": "NET_DEBT_TO_EBITDA",
    },
    "lseg": {
        "roe": "TR.ROEPercent", "roic": "TR.ROICPercent",
        "op_margin": "TR.OperatingMargPct", "per": "TR.PE",
        "forward_per": "TR.FwdPE", "pbr": "TR.PriceToBVPerShare",
        "ev_ebitda": "TR.EVToEBITDA", "fcf_yield": "TR.FCFYield",
        "eps_revision_3m": "TR.EPSMean(Period=FY1,WP=90D)", "net_debt_ebitda": "TR.NetDebtToEBITDA",
    },
    "factset": {
        "roe": "FF_ROE", "roic": "FF_ROIC", "op_margin": "FF_OPER_MGN",
        "per": "FF_PE", "forward_per": "FE_PE_MEAN", "pbr": "FF_PBK",
        "ev_ebitda": "FF_ENTRPR_VAL_EBITDA_OPER", "fcf_yield": "FF_FREE_CF_YLD",
        "eps_revision_3m": "FE_EPS_REV_3M", "net_debt_ebitda": "FF_NET_DEBT_EBITDA_OPER",
    },
    "capiq": {
        "roe": "IQ_RETURN_EQUITY", "roic": "IQ_RETURN_CAPITAL",
        "op_margin": "IQ_EBIT_MARGIN", "per": "IQ_PE_EXCL",
        "forward_per": "IQ_PE_EXCL_FWD", "pbr": "IQ_PBV",
        "ev_ebitda": "IQ_TEV_EBITDA", "fcf_yield": "IQ_FCF_YIELD",
        "eps_revision_3m": "IQ_EST_EPS_REV_3M", "net_debt_ebitda": "IQ_NET_DEBT_EBITDA",
    },
}


class PremiumProvider:
    """未実装スタブ。実装者は _fetch() だけを書けばよい。"""

    name = "premium"
    is_synthetic = False

    def __init__(self) -> None:
        self.vendor = os.getenv("VR_PREMIUM_VENDOR", "lseg").lower()
        self.api_key = os.getenv("VR_PREMIUM_KEY", "")
        self.endpoint = os.getenv("VR_PREMIUM_ENDPOINT", "")
        if self.vendor not in FIELD_MAP:
            raise ProviderError(f"未知のベンダ: {self.vendor}（対応: {list(FIELD_MAP)}）")

    def fundamentals(self, tickers: List[str], as_of: str) -> Dict[str, Fundamentals]:
        return self._fetch(tickers, as_of)

    def _fetch(self, tickers: List[str], as_of: str) -> Dict[str, Fundamentals]:  # pragma: no cover
        raise ProviderError(
            f"PremiumProvider({self.vendor}) は未実装です。"
            " docs/DATA_PROVIDERS.md の手順に従って _fetch() を実装してください。"
            " エンジン側の変更は不要です（Fundamentals を返すだけ）。"
        )
