# -*- coding: utf-8 -*-
"""
デモ用データプロバイダ（Python標準ライブラリのみ・ネットワーク不要）

目的は「APIキーなし・オフラインでも毎日必ず動く体験デモ」を作ること。
数値は profile パラメータを種にした決定論的な合成値であり、実際の財務数値ではない。
同じ日付・同じ銘柄なら何度実行しても同じ値になる（再現性）。
日付が進むと緩やかに変動するため、TOP10 は毎日少しずつ入れ替わる。

!!! この Provider が返す Fundamentals は is_synthetic=True である。
    UI とレポートは必ず「デモデータ」バッジを表示すること。
"""

from __future__ import annotations
import hashlib
import math
import datetime as _dt
from typing import Dict, List

from ..universe import UNIVERSE, by_ticker
from ..demand.graph import NODES, NODE_MAP, SIGNAL_LABELS, depth_map
from .base import Fundamentals, EvidenceItem

SALT = "value-radar-ai/v1"


def _u(*parts) -> float:
    """決定論的な 0-1 の一様乱数。"""
    h = hashlib.sha256(("|".join(str(p) for p in parts) + "|" + SALT).encode()).digest()
    return int.from_bytes(h[:8], "big") / float(1 << 64)


def _n(*parts) -> float:
    """決定論的な近似正規乱数（平均0・標準偏差1）。"""
    a = _u("n1", *parts)
    b = _u("n2", *parts)
    a = min(max(a, 1e-9), 1 - 1e-9)
    return math.sqrt(-2.0 * math.log(a)) * math.cos(2.0 * math.pi * b)


def _day_index(as_of: str) -> int:
    d = _dt.date.fromisoformat(as_of)
    return (d - _dt.date(2020, 1, 1)).days


def _wave(ticker: str, as_of: str, period_days: float, tag: str = "") -> float:
    """-1〜1 の滑らかな時間変動。日次で少しずつ動くので体験が自然になる。"""
    t = _day_index(as_of)
    phase = _u("phase", ticker, tag) * 2 * math.pi
    return math.sin(2 * math.pi * t / period_days + phase)


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


class DemoProvider:
    name = "demo"
    is_synthetic = True

    def fundamentals(self, tickers: List[str], as_of: str) -> Dict[str, Fundamentals]:
        out: Dict[str, Fundamentals] = {}
        for t in tickers:
            c = by_ticker(t)
            if c is None:
                continue
            out[t] = self._one(t, as_of)
        return out

    # ------------------------------------------------------------------
    def _one(self, ticker: str, as_of: str) -> Fundamentals:
        c = by_ticker(ticker)
        assert c is not None
        q, g, v, lev, vol, mom, gov = c.q, c.g, c.v, c.lev, c.vol, c.mom, c.gov

        # --- 価格：基準株価に対して緩やかなトレンド＋ノイズ ---------------
        drift = 0.16 * _wave(ticker, as_of, 240, "px") + 0.05 * _wave(ticker, as_of, 47, "px2")
        noise = 0.012 * _n("px", ticker, as_of)
        px = c.price_anchor * (1.0 + drift * (0.5 + vol) + noise)
        px = max(px, 0.01)
        prev = px / (1.0 + 0.011 * _n("pxprev", ticker, as_of) * (0.5 + vol))

        # --- モメンタム（波の位相差から自然に導出） -----------------------
        base_mom = (mom - 0.5) * 40.0
        m1 = base_mom * 0.25 + 9.0 * _wave(ticker, as_of, 41, "m1") + 2.0 * _n("m1", ticker, as_of)
        m3 = base_mom * 0.55 + 15.0 * _wave(ticker, as_of, 96, "m3")
        m6 = base_mom * 0.9 + 22.0 * _wave(ticker, as_of, 190, "m6")
        m12 = base_mom * 1.5 + 30.0 * _wave(ticker, as_of, 360, "m12")

        dist_high = -abs(6.0 + 34.0 * (1.0 - mom) * (0.6 + _u("dh", ticker, as_of)))
        mdd = -abs(12.0 + 45.0 * vol * (0.6 + 0.6 * _u("mdd", ticker)))
        vol_ann = _clip(vol * (0.9 + 0.25 * _u("v", ticker, as_of)), 0.10, 0.95)
        volume_ratio = _clip(1.0 + 0.35 * _wave(ticker, as_of, 23, "vr") + 0.10 * _n("vr", ticker, as_of), 0.4, 3.5)

        # --- 品質 ---------------------------------------------------------
        roe = _clip(2.0 + 34.0 * q + 5.0 * _n("roe", ticker, as_of) * 0.4, -8.0, 62.0)
        roic = _clip(roe * (0.62 + 0.25 * q) + 1.5 * _n("roic", ticker, as_of) * 0.3, -6.0, 48.0)
        opm = _clip(1.5 + 33.0 * q + 3.0 * _n("opm", ticker, as_of) * 0.4, -5.0, 58.0)
        fcfm = _clip(opm * (0.42 + 0.35 * q) + 2.0 * _n("fcfm", ticker, as_of) * 0.4, -12.0, 42.0)
        stab = _clip(0.25 + 0.6 * q + 0.12 * _n("stab", ticker) * 0.3 - 0.25 * vol, 0.02, 0.99)

        # --- 成長 ---------------------------------------------------------
        rev_g = _clip(-3.0 + 42.0 * g + 4.0 * _n("rg", ticker, as_of) * 0.5, -18.0, 78.0)
        eps_g = _clip(rev_g * (1.0 + 0.7 * q) + 5.0 * _n("eg", ticker, as_of) * 0.5, -35.0, 130.0)
        fcf_g = _clip(eps_g * (0.6 + 0.4 * stab) + 5.0 * _n("fg", ticker, as_of) * 0.5, -45.0, 120.0)
        mtrend = _clip((g - 0.45) * 9.0 + 1.2 * _n("mt", ticker, as_of) * 0.5, -8.0, 12.0)
        revision = _clip((mom - 0.5) * 14.0 + 3.0 * _wave(ticker, as_of, 63, "rev"), -22.0, 26.0)

        # --- 割安度（v が高いほど割高） -----------------------------------
        per_base = 7.0 + 78.0 * (v ** 1.9)
        per = _clip(per_base * (1.0 + 0.10 * _wave(ticker, as_of, 150, "per")), 3.0, 190.0)
        fwd_per = _clip(per / (1.0 + max(eps_g, -40.0) / 100.0 * 0.85), 2.5, 170.0)
        pbr = _clip(0.35 + per * (0.02 + 0.030 * q) + 0.25 * _n("pbr", ticker), 0.15, 26.0)
        ev_eb = _clip(per * (0.52 + 0.22 * lev) + 0.6 * _n("ev", ticker), 2.0, 85.0)
        fcf_y = _clip(100.0 / max(per, 3.0) * (0.55 + 0.55 * stab), 0.05, 18.0)
        peg = _clip(per / max(eps_g, 2.0), 0.15, 12.0)

        # --- 財務健全性 ---------------------------------------------------
        de = _clip(0.02 + 2.6 * (lev ** 1.6) + 0.10 * abs(_n("de", ticker)), 0.0, 4.2)
        nde = _clip(-1.6 + 6.2 * lev + 0.3 * _n("nde", ticker), -3.5, 7.5)
        cr = _clip(2.6 - 1.7 * lev + 0.18 * _n("cr", ticker), 0.5, 5.0)
        icov = _clip(90.0 * (1.0 - lev) ** 2.4 + 2.0, 0.6, 120.0)

        # --- 定性（経営・競争力・ガバナンス） ------------------------------
        moat = _clip(100.0 * (0.30 * q + 0.30 * gov + 0.25 * min(opm / 40.0, 1.0) + 0.15 * stab), 5, 99)
        govs = _clip(100.0 * gov + 4.0 * _n("gov", ticker), 3, 99)
        capalloc = _clip(100.0 * (0.55 * gov + 0.3 * q + 0.15 * (1 - lev)), 3, 99)
        culture = _clip(100.0 * (0.6 * gov + 0.25 * q + 0.15 * _u("cul", ticker)), 3, 99)
        ir = _clip(100.0 * (0.5 * gov + 0.3 * min(c.mcap_musd / 200000.0, 1.0) + 0.2 * _u("ir", ticker)), 3, 99)

        coverage = _clip(0.80 + 0.19 * min(c.mcap_musd / 120000.0, 1.0) - 0.10 * _u("cov", ticker), 0.55, 1.0)
        adv = c.mcap_musd * (0.0035 + 0.010 * _u("adv", ticker)) * volume_ratio

        return Fundamentals(
            ticker=ticker, as_of=as_of,
            price=round(px, 2), prev_close=round(prev, 2), currency=c.currency,
            mcap_musd=round(c.mcap_musd * (1 + drift * 0.5), 1), adv_musd=round(adv, 1),
            roe=round(roe, 2), roic=round(roic, 2), op_margin=round(opm, 2),
            fcf_margin=round(fcfm, 2), earnings_stability=round(stab, 3),
            per=round(per, 2), forward_per=round(fwd_per, 2), pbr=round(pbr, 2),
            ev_ebitda=round(ev_eb, 2), fcf_yield=round(fcf_y, 2), peg=round(peg, 2),
            div_yield=c.div_yield,
            rev_cagr3=round(rev_g, 2), eps_cagr3=round(eps_g, 2), fcf_cagr3=round(fcf_g, 2),
            margin_trend=round(mtrend, 2), eps_revision_3m=round(revision, 2),
            de_ratio=round(de, 2), net_debt_ebitda=round(nde, 2),
            current_ratio=round(cr, 2), interest_coverage=round(icov, 1),
            mom_1m=round(m1, 2), mom_3m=round(m3, 2), mom_6m=round(m6, 2), mom_12m=round(m12, 2),
            vol_ann=round(vol_ann, 3), max_drawdown_1y=round(mdd, 1),
            dist_52w_high=round(dist_high, 1), volume_ratio=round(volume_ratio, 2),
            moat_score=round(moat, 1), governance_score=round(govs, 1),
            capital_allocation=round(capalloc, 1), culture_engagement=round(culture, 1),
            ir_dialogue=round(ir, 1),
            data_coverage=round(coverage, 3), source="demo", is_synthetic=True,
        )


# ---------------------------------------------------------------------------
# 需要エビデンス（デモ）
# ---------------------------------------------------------------------------

_HEADLINE_TMPL = {
    "orders_backlog": "{label}関連の受注残が前年同期比 {d:+.0f}% 水準",
    "capex_plan": "{label}に紐づく設備投資計画が {d:+.0f}% 改定",
    "gov_budget": "{label}向けの政府予算・補助枠が {d:+.0f}% 変化",
    "job_postings": "{label}分野の求人数が {d:+.0f}% 変化",
    "plant_construction": "{label}に関する着工・用地取得が {d:+.0f}% 変化",
    "power_demand": "{label}に関わる電力需要・系統接続申請が {d:+.0f}% 変化",
    "shipment_stats": "{label}の出荷統計が前年比 {d:+.0f}%",
    "lead_time": "{label}のリードタイムが {d:+.0f}% 変化（長期化はプラス評価）",
    "patents": "{label}領域の特許出願が {d:+.0f}% 変化",
    "exec_commentary": "決算説明での{label}への言及頻度が {d:+.0f}% 変化",
    "price_index": "{label}のスポット価格指標が {d:+.0f}% 変化",
    "utilization": "{label}の稼働率が {d:+.0f}pt 変化",
}


class DemoEvidenceProvider:
    name = "demo"
    is_synthetic = True

    # ノードごとの「実需の強さ」の基調（0-1）。デモの世界観を決める骨。
    BASE = {
        "genai_capex": 0.93, "gpu_accel": 0.92, "hbm_memory": 0.90,
        "adv_packaging": 0.89, "semi_foundry": 0.85, "semi_equip": 0.80,
        "semi_materials": 0.70, "dc_build": 0.90, "server_oem": 0.84,
        "cooling": 0.86, "dc_power": 0.85, "ups_pdu": 0.82,
        "transformer": 0.84, "grid_td": 0.78, "power_gen": 0.76,
        "nuclear": 0.72, "renewables": 0.55, "power_semi": 0.52,
        "network_switch": 0.79, "optical_device": 0.83, "optical_fiber": 0.77,
        "epc_construction": 0.66, "edge_ai": 0.58, "software_ai": 0.68,
        "robotics": 0.62, "factory_auto": 0.55, "machine_tools": 0.48,
        "ev_supply": 0.40, "electrification": 0.55, "labor_shortage": 0.70,
        "geopolitics": 0.80, "defense_prime": 0.82, "defense_electronics": 0.74,
        "demographics": 0.70, "aging_health": 0.66, "pharma": 0.58,
        "macro_cycle": 0.50, "consumer_us": 0.48, "consumer_asia": 0.45,
        "consumer_lux": 0.34, "consumer_staples": 0.42, "rates_financials": 0.56,
        "commodities": 0.46, "mining_equipment": 0.50,
    }

    def evidence(self, node_ids: List[str], as_of: str) -> Dict[str, List[EvidenceItem]]:
        out: Dict[str, List[EvidenceItem]] = {}
        for nid in node_ids:
            node = NODE_MAP.get(nid)
            if node is None:
                continue
            base = self.BASE.get(nid, 0.5)
            items: List[EvidenceItem] = []
            for sig in node.signals:
                lvl = _clip(100.0 * base + 10.0 * _wave(nid + sig, as_of, 120, "ev")
                            + 3.0 * _n("ev", nid, sig, as_of), 2.0, 99.0)
                chg = _clip(18.0 * (base - 0.45) + 9.0 * _wave(nid + sig, as_of, 75, "evc")
                            + 2.5 * _n("evc", nid, sig, as_of), -40.0, 60.0)
                items.append(EvidenceItem(
                    node=nid, signal=sig, value=round(lvl, 1), change_3m=round(chg, 1),
                    headline=_HEADLINE_TMPL[sig].format(label=node.label, d=chg),
                    source="DEMO（合成値：実データではありません）",
                    source_url="", observed_at=as_of, is_synthetic=True,
                ))
            out[nid] = items
        return out


if __name__ == "__main__":
    p = DemoProvider()
    f = p.fundamentals(["NVDA", "1982.T", "5803.T"], "2026-08-29")
    for k, v in f.items():
        print(k, "px", v.price, "PER", v.per, "ROE", v.roe, "mom12", v.mom_12m)
