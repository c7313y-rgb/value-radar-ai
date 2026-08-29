# -*- coding: utf-8 -*-
"""
データプロバイダ抽象層

評価エンジンとデータAPIを完全に分離するための境界。
無料の公開情報で作った初期版から、Bloomberg / LSEG(Refinitiv) / S&P Capital IQ /
FactSet / Morningstar / MSCI といった有料データへ「この層だけ」を差し替えて
移行できるようにする。エンジン側は Fundamentals / PriceSeries / EvidenceItem の
3つのデータ契約しか知らない。
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Protocol
import datetime as _dt


# ---------------------------------------------------------------------------
# データ契約（この形さえ守れば、どんなデータソースでも差し替え可能）
# ---------------------------------------------------------------------------

@dataclass
class Fundamentals:
    ticker: str
    as_of: str

    # 価格・時価
    price: float = 0.0
    prev_close: float = 0.0
    currency: str = "USD"
    mcap_musd: float = 0.0
    adv_musd: float = 0.0            # 平均売買代金（百万USD）

    # 品質
    roe: float = 0.0                 # %
    roic: float = 0.0                # %
    op_margin: float = 0.0           # %
    fcf_margin: float = 0.0          # %
    earnings_stability: float = 0.0  # 0-1（過去利益の変動の小ささ）

    # 割安度
    per: float = 0.0
    forward_per: float = 0.0
    pbr: float = 0.0
    ev_ebitda: float = 0.0
    fcf_yield: float = 0.0           # %
    peg: float = 0.0
    div_yield: float = 0.0           # %

    # 成長
    rev_cagr3: float = 0.0           # %
    eps_cagr3: float = 0.0           # %
    fcf_cagr3: float = 0.0           # %
    margin_trend: float = 0.0        # pt（3年での営業利益率変化）
    eps_revision_3m: float = 0.0     # %（アナリスト予想の3ヶ月改定率）

    # 財務健全性
    de_ratio: float = 0.0            # 倍
    net_debt_ebitda: float = 0.0     # 倍
    current_ratio: float = 0.0       # 倍
    interest_coverage: float = 0.0   # 倍

    # 株価・需給
    mom_1m: float = 0.0              # %
    mom_3m: float = 0.0
    mom_6m: float = 0.0
    mom_12m: float = 0.0
    vol_ann: float = 0.0             # 年率ボラティリティ（小数）
    max_drawdown_1y: float = 0.0     # %（負値）
    dist_52w_high: float = 0.0       # %（52週高値からの乖離、負値）
    volume_ratio: float = 1.0        # 直近出来高 / 3ヶ月平均

    # 定性（経営・競争力・ガバナンス）
    moat_score: float = 0.0          # 0-100
    governance_score: float = 0.0    # 0-100
    capital_allocation: float = 0.0  # 0-100
    culture_engagement: float = 0.0  # 0-100
    ir_dialogue: float = 0.0         # 0-100

    # メタ
    data_coverage: float = 1.0       # 0-1（欠損の少なさ＝確信度の材料）
    source: str = "demo"
    is_synthetic: bool = True        # デモ合成値なら True

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EvidenceItem:
    """需要の「実需」証拠。人気（株価）ではなく事実を数値化するための単位。"""
    node: str
    signal: str            # SIGNAL_LABELS のキー
    value: float           # 0-100 に正規化した水準
    change_3m: float       # 直近3ヶ月の変化（pt）
    headline: str
    source: str
    source_url: str = ""
    observed_at: str = ""
    is_synthetic: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# プロバイダのインターフェース
# ---------------------------------------------------------------------------

class MarketDataProvider(Protocol):
    name: str
    is_synthetic: bool

    def fundamentals(self, tickers: List[str], as_of: str) -> Dict[str, Fundamentals]:
        ...


class EvidenceProvider(Protocol):
    name: str
    is_synthetic: bool

    def evidence(self, node_ids: List[str], as_of: str) -> Dict[str, List[EvidenceItem]]:
        ...


class ProviderError(RuntimeError):
    pass


def today() -> str:
    return _dt.date.today().isoformat()
