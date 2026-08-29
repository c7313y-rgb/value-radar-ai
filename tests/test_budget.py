# -*- coding: utf-8 -*-
import unittest

from engine.output.budget import allocate, build_all, target_names, BUDGET_PRESETS
from engine.output.fx import get_rates, to_jpy
from engine.pipeline import run


class TestBudget(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = run("2026-08-29", "demo", False, None, write=False)
        cls.rows = cls.p["rows"]

    def test_never_exceeds_budget(self):
        for b in BUDGET_PRESETS:
            plan = allocate(self.rows[:60], b)
            self.assertLessEqual(plan["invested"], b, f"予算{b}を超過している")
            self.assertGreaterEqual(plan["cash"], 0)

    def test_lots_are_integral_and_respect_lot_size(self):
        for b in BUDGET_PRESETS:
            for pos in allocate(self.rows[:60], b)["positions"]:
                self.assertEqual(pos["shares"], pos["lots"] * pos["lot"])
                self.assertEqual(pos["shares"] % pos["lot"], 0)
                self.assertGreaterEqual(pos["lots"], 1)

    def test_cost_matches_price_times_shares(self):
        rates = get_rates()
        for pos in allocate(self.rows[:60], 3_000_000)["positions"]:
            expect = to_jpy(pos["price"] * pos["shares"], pos["currency"], rates)
            self.assertLess(abs(expect - pos["cost_jpy"]), 2.0)

    def test_bigger_budget_gets_more_names(self):
        small = allocate(self.rows[:60], 100_000)["names"]
        big = allocate(self.rows[:60], 10_000_000)["names"]
        self.assertGreater(big, small)

    def test_does_not_propose_stocks_it_told_you_to_wait_on(self):
        for b in BUDGET_PRESETS:
            for pos in allocate(self.rows[:60], b)["positions"]:
                row = next(r for r in self.rows if r["ticker"] == pos["ticker"])
                self.assertNotEqual(row["verdict"], "QUALITY_WAIT",
                                    "「価格待ち」の銘柄を購入プランに載せてはいけない")
                self.assertNotEqual(row["verdict"], "PASS")

    def test_tiny_budget_is_handled_gracefully(self):
        plan = allocate(self.rows[:60], 1000)
        self.assertEqual(plan["invested"], 0)
        self.assertIn("購入できる銘柄", plan["note"])

    def test_target_names_monotonic(self):
        prev = 0
        for b in BUDGET_PRESETS:
            n = target_names(b)
            self.assertGreaterEqual(n, prev)
            prev = n
