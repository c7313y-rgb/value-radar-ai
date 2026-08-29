# -*- coding: utf-8 -*-
"""
指標の標準化

設計上の要点:
  1. PER と ROE のように単位も分布も違う指標を「そのまま平均」しない。
  2. 比較は必ず同じ土俵で行う ＝ 業種 × 地域のピアグループ内で標準化する。
  3. 外れ値は winsorize（±2.5σ）で切る。1銘柄の異常値が順位を壊さないように。
  4. 欠損は平均で埋めない。欠損はレイヤー内の重みを再配分し、
     同時に data_coverage を通じて「確信度」を下げる形で罰する。
"""

from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple

MIN_GROUP = 8
WINSOR = 2.5

# レイヤー内で複数指標を平均すると分散が縮み、全銘柄が50点付近に潰れる。
# 順位関係を変えずに 0-100 のレンジを使い切るための拡張係数。
LAYER_SPREAD = 1.45


def _mean_std(xs: List[float]) -> Tuple[float, float]:
    n = len(xs)
    if n == 0:
        return 0.0, 1.0
    m = sum(xs) / n
    if n == 1:
        return m, 1.0
    var = sum((x - m) ** 2 for x in xs) / (n - 1)
    return m, math.sqrt(var) if var > 1e-12 else 1.0


def logistic_score(z: float, slope: float = 1.10) -> float:
    """z値を 0-100 に写す。z=0→50, z=+2→約90, z=-2→約10。"""
    z = max(-WINSOR, min(WINSOR, z))
    return 100.0 / (1.0 + math.exp(-slope * z))


class PeerNormalizer:
    """
    ピアグループ（業種×地域 → 業種 → 全体）に段階的にフォールバックしながら
    z値を計算する。小さすぎる母集団で標準化すると偶然が支配するため。
    """

    def __init__(self, rows: Dict[str, dict], meta: Dict[str, dict]):
        """
        rows : {ticker: {metric: value}}
        meta : {ticker: {"sector": str, "region": str}}
        """
        self.rows = rows
        self.meta = meta
        self._cache: Dict[Tuple[str, str], Tuple[float, float]] = {}
        self._group_cache: Dict[str, List[str]] = {}

    # ---------------------------------------------------------------
    def group_for(self, ticker: str) -> Tuple[str, List[str]]:
        if ticker in self._group_cache:
            key = self._group_cache[ticker][0]
            return key, self._group_cache[ticker][1:]
        m = self.meta.get(ticker, {})
        sec, reg = m.get("sector", "?"), m.get("region", "?")
        peers = [t for t, mm in self.meta.items()
                 if mm.get("sector") == sec and mm.get("region") == reg]
        key = f"{sec}/{reg}"
        if len(peers) < MIN_GROUP:
            peers = [t for t, mm in self.meta.items() if mm.get("sector") == sec]
            key = f"{sec}/ALL"
        if len(peers) < MIN_GROUP:
            peers = list(self.meta.keys())
            key = "UNIVERSE"
        self._group_cache[ticker] = [key] + peers
        return key, peers

    def _stats(self, group_key: str, peers: List[str], metric: str) -> Tuple[float, float]:
        ck = (group_key, metric)
        if ck in self._cache:
            return self._cache[ck]
        xs = [self.rows[t][metric] for t in peers
              if t in self.rows and self.rows[t].get(metric) is not None]
        m, s = _mean_std(xs)
        self._cache[ck] = (m, s)
        return m, s

    # ---------------------------------------------------------------
    def z(self, ticker: str, metric: str, direction: int = 1) -> Optional[float]:
        """direction=+1: 大きいほど良い / -1: 小さいほど良い。欠損は None。"""
        v = self.rows.get(ticker, {}).get(metric)
        if v is None:
            return None
        key, peers = self.group_for(ticker)
        m, s = self._stats(key, peers, metric)
        z = (v - m) / s
        z = max(-WINSOR, min(WINSOR, z))
        return z * direction

    def score(self, ticker: str, metric: str, direction: int = 1) -> Optional[float]:
        z = self.z(ticker, metric, direction)
        return None if z is None else logistic_score(z)

    def percentile(self, ticker: str, metric: str, direction: int = 1) -> Optional[float]:
        """ピア内のパーセンタイル（0-100）。バリュエーション位置の説明に使う。"""
        v = self.rows.get(ticker, {}).get(metric)
        if v is None:
            return None
        _, peers = self.group_for(ticker)
        xs = sorted(self.rows[t][metric] for t in peers
                    if t in self.rows and self.rows[t].get(metric) is not None)
        if not xs:
            return None
        below = sum(1 for x in xs if x < v)
        p = below / len(xs) * 100.0
        return p if direction > 0 else 100.0 - p


def weighted_layer(parts: List[Tuple[str, Optional[float], float]]) -> Tuple[float, float, List[dict]]:
    """
    (指標名, スコア or None, 重み) のリストから、欠損分の重みを再配分して
    レイヤースコアを出す。戻り値は (スコア, カバレッジ, 内訳)。
    """
    used = [(n, s, w) for (n, s, w) in parts if s is not None]
    total_w = sum(w for _, _, w in parts)
    used_w = sum(w for _, _, w in used)
    if used_w <= 0:
        return 50.0, 0.0, []
    score = sum(s * w for _, s, w in used) / used_w
    score = max(0.0, min(100.0, 50.0 + (score - 50.0) * LAYER_SPREAD))
    detail = [{"metric": n, "score": round(s, 1), "weight": round(w / used_w, 3)} for n, s, w in used]
    return score, used_w / total_w, detail
