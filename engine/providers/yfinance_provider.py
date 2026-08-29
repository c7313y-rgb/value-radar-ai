# -*- coding: utf-8 -*-
"""
実データプロバイダ（yfinance / Yahoo Finance 公開データ）

初期版の「無料の公開情報層」の実装例。
`pip install yfinance` が必要で、ネットワークとレート制限に依存する。
取得できなかった項目は 0 のまま残し、data_coverage を下げて確信度に反映させる
（欠損を平均値で埋めて見かけ上のスコアを作らない、というのが設計上の約束）。

  VR_PROVIDER=yfinance python -m engine.pipeline
"""

from __future__ import annotations
from typing import Dict, List
import math

from ..universe import by_ticker
from .base import Fundamentals, ProviderError


class YFinanceProvider:
    name = "yfinance"
    is_synthetic = False

    def __init__(self) -> None:
        try:
            import yfinance  # noqa: F401
        except ImportError as e:  # pragma: no cover
            raise ProviderError(
                "yfinance が未インストールです。`pip install -r requirements-live.txt` を実行してください。"
            ) from e

    def fundamentals(self, tickers: List[str], as_of: str) -> Dict[str, Fundamentals]:
        import yfinance as yf

        out: Dict[str, Fundamentals] = {}
        for t in tickers:
            c = by_ticker(t)
            try:
                tk = yf.Ticker(t)
                info = tk.info or {}
                hist = tk.history(period="1y", auto_adjust=True)
            except Exception:
                continue
            if not info and hist.empty:
                continue

            px = float(info.get("currentPrice") or (hist["Close"].iloc[-1] if len(hist) else 0) or 0)
            prev = float(info.get("previousClose") or px)

            def mom(days: int) -> float:
                if len(hist) <= days:
                    return 0.0
                a = float(hist["Close"].iloc[-days - 1])
                b = float(hist["Close"].iloc[-1])
                return (b / a - 1.0) * 100.0 if a else 0.0

            closes = list(hist["Close"]) if len(hist) else []
            rets = [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes))] if len(closes) > 2 else []
            mean = sum(rets) / len(rets) if rets else 0.0
            var = sum((r - mean) ** 2 for r in rets) / len(rets) if rets else 0.0
            vol_ann = math.sqrt(var) * math.sqrt(252) if var else 0.0
            peak, mdd = 0.0, 0.0
            for cl in closes:
                peak = max(peak, cl)
                if peak:
                    mdd = min(mdd, cl / peak - 1.0)
            hi52 = float(info.get("fiftyTwoWeekHigh") or (max(closes) if closes else px) or px)

            filled = 0
            keys = ["returnOnEquity", "operatingMargins", "trailingPE", "forwardPE",
                    "priceToBook", "enterpriseToEbitda", "revenueGrowth", "earningsGrowth",
                    "debtToEquity", "currentRatio", "marketCap"]
            for k in keys:
                if info.get(k) not in (None, 0):
                    filled += 1
            coverage = filled / len(keys)

            fcf = info.get("freeCashflow") or 0
            mcap = float(info.get("marketCap") or 0)
            fcf_yield = (fcf / mcap * 100.0) if (fcf and mcap) else 0.0
            per = float(info.get("trailingPE") or 0)
            eps_g = float(info.get("earningsGrowth") or 0) * 100.0
            peg = (per / eps_g) if (per and eps_g > 0) else 0.0

            out[t] = Fundamentals(
                ticker=t, as_of=as_of, price=px, prev_close=prev,
                currency=(c.currency if c else info.get("currency", "USD")),
                mcap_musd=mcap / 1e6,
                roe=float(info.get("returnOnEquity") or 0) * 100.0,
                roic=0.0,
                op_margin=float(info.get("operatingMargins") or 0) * 100.0,
                fcf_margin=0.0, earnings_stability=0.0,
                per=per, forward_per=float(info.get("forwardPE") or 0),
                pbr=float(info.get("priceToBook") or 0),
                ev_ebitda=float(info.get("enterpriseToEbitda") or 0),
                fcf_yield=fcf_yield, peg=peg,
                div_yield=float(info.get("dividendYield") or 0) * 100.0,
                rev_cagr3=float(info.get("revenueGrowth") or 0) * 100.0,
                eps_cagr3=eps_g, fcf_cagr3=0.0, margin_trend=0.0, eps_revision_3m=0.0,
                de_ratio=float(info.get("debtToEquity") or 0) / 100.0,
                net_debt_ebitda=0.0,
                current_ratio=float(info.get("currentRatio") or 0),
                interest_coverage=0.0,
                mom_1m=mom(21), mom_3m=mom(63), mom_6m=mom(126), mom_12m=mom(250),
                vol_ann=vol_ann, max_drawdown_1y=mdd * 100.0,
                dist_52w_high=((px / hi52 - 1.0) * 100.0 if hi52 else 0.0),
                volume_ratio=1.0,
                moat_score=0.0, governance_score=0.0, capital_allocation=0.0,
                culture_engagement=0.0, ir_dialogue=0.0,
                data_coverage=coverage, source="yfinance", is_synthetic=False,
            )
        if not out:
            raise ProviderError("yfinance から1銘柄も取得できませんでした（レート制限またはネットワーク遮断）")
        return out
