# -*- coding: utf-8 -*-
import unittest
from dataclasses import fields

from engine.providers.base import Fundamentals, EvidenceItem
from engine.providers.demo_provider import DemoProvider, DemoEvidenceProvider
from engine.providers.registry import get_market_provider, get_evidence_provider
from engine.providers.premium_provider import FIELD_MAP, PremiumProvider
from engine.providers.base import ProviderError
from engine.universe import UNIVERSE
from engine.demand.graph import NODES


class TestDemoProvider(unittest.TestCase):
    def setUp(self):
        self.p = DemoProvider()
        self.tickers = [c.ticker for c in UNIVERSE]

    def test_deterministic(self):
        a = self.p.fundamentals(["NVDA", "6501.T"], "2026-08-29")
        b = self.p.fundamentals(["NVDA", "6501.T"], "2026-08-29")
        self.assertEqual(a["NVDA"].to_dict(), b["NVDA"].to_dict())

    def test_changes_between_days(self):
        a = self.p.fundamentals(["NVDA"], "2026-08-29")["NVDA"]
        b = self.p.fundamentals(["NVDA"], "2026-09-15")["NVDA"]
        self.assertNotEqual(a.price, b.price)

    def test_covers_whole_universe(self):
        f = self.p.fundamentals(self.tickers, "2026-08-29")
        self.assertEqual(len(f), len(self.tickers))

    def test_values_are_finite_and_plausible(self):
        f = self.p.fundamentals(self.tickers, "2026-08-29")
        for t, v in f.items():
            self.assertGreater(v.price, 0, t)
            self.assertTrue(2.0 <= v.per <= 200.0, f"{t} PER={v.per}")
            self.assertTrue(-20.0 <= v.roe <= 70.0, f"{t} ROE={v.roe}")
            self.assertTrue(0.0 < v.vol_ann < 1.0, f"{t} vol={v.vol_ann}")
            self.assertLessEqual(v.dist_52w_high, 0.0, t)
            self.assertTrue(0.0 < v.data_coverage <= 1.0, t)

    def test_marked_synthetic(self):
        v = self.p.fundamentals(["NVDA"], "2026-08-29")["NVDA"]
        self.assertTrue(v.is_synthetic, "デモデータは必ず合成値と明示されること")
        self.assertTrue(DemoProvider.is_synthetic)


class TestEvidence(unittest.TestCase):
    def test_all_nodes_have_evidence(self):
        ev = DemoEvidenceProvider().evidence([n.id for n in NODES], "2026-08-29")
        for n in NODES:
            self.assertIn(n.id, ev)
            self.assertTrue(ev[n.id])
            for it in ev[n.id]:
                self.assertTrue(0 <= it.value <= 100)
                self.assertTrue(it.is_synthetic)
                self.assertIn("DEMO", it.source)


class TestRegistry(unittest.TestCase):
    def test_demo_selection(self):
        self.assertEqual(get_market_provider("demo").name, "demo")
        self.assertEqual(get_evidence_provider("demo").name, "demo")

    def test_unknown_provider_raises(self):
        with self.assertRaises(Exception):
            get_market_provider("nonexistent")

    def test_unknown_provider_falls_back_when_asked(self):
        self.assertEqual(get_market_provider("nonexistent", fallback_demo=True).name, "demo")

    def test_premium_stub_is_explicit(self):
        """有料層は「未実装」と明示的に落ちること。黙ってデモを返さない。"""
        import os
        os.environ["VR_PREMIUM_VENDOR"] = "lseg"
        p = PremiumProvider()
        with self.assertRaises(ProviderError):
            p.fundamentals(["NVDA"], "2026-08-29")

    def test_premium_field_map_covers_core_metrics(self):
        core = {"roe", "per", "forward_per", "pbr", "ev_ebitda", "fcf_yield"}
        for vendor, m in FIELD_MAP.items():
            self.assertTrue(core <= set(m), f"{vendor} のフィールド対応表に不足")


class TestContract(unittest.TestCase):
    def test_fundamentals_contract_is_stable(self):
        """この契約が変わると全プロバイダの差し替え互換性が壊れる。"""
        names = {f.name for f in fields(Fundamentals)}
        required = {"ticker", "as_of", "price", "per", "roe", "fcf_yield",
                    "eps_cagr3", "net_debt_ebitda", "mom_12m", "vol_ann",
                    "data_coverage", "source", "is_synthetic"}
        self.assertTrue(required <= names)
