# -*- coding: utf-8 -*-
import unittest

from engine.pipeline import run
from engine.scoring.layers import LAYER_WEIGHTS


class TestPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = run("2026-08-29", "demo", False, None, write=False)

    def test_shape(self):
        p = self.p
        for key in ("meta", "rows", "nodes", "edges", "opportunities",
                    "budgets", "guides", "alerts", "top10"):
            self.assertIn(key, p)
        self.assertEqual(len(p["top10"]), 10)
        self.assertGreater(len(p["rows"]), 50)

    def test_demo_flag_is_propagated(self):
        self.assertTrue(self.p["meta"]["is_demo_data"])
        self.assertIn("デモ", self.p["meta"]["disclaimer"])

    def test_ranking_is_sorted_and_consistent(self):
        rows = self.p["rows"]
        self.assertEqual([r["rank"] for r in rows], list(range(1, len(rows) + 1)))
        scores = [r["final_score"] for r in rows]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_final_score_formula_holds(self):
        for r in self.p["rows"]:
            expect = (r["value_score"] * r["confidence"] - r["risk_points"]
                      + r["committee"]["chair_adjustment"])
            expect = max(0.0, min(100.0, expect))
            self.assertLess(abs(expect - r["final_score"]), 0.15, r["ticker"])

    def test_value_score_is_weighted_sum_of_layers(self):
        for r in self.p["rows"][:20]:
            expect = sum(r["layers"][k] * w for k, w in LAYER_WEIGHTS.items()) / 100.0
            self.assertLess(abs(expect - r["value_score"]), 0.2, r["ticker"])

    def test_scores_in_range(self):
        for r in self.p["rows"]:
            self.assertTrue(0 <= r["final_score"] <= 100)
            self.assertTrue(0.5 <= r["confidence"] <= 1.0)
            self.assertTrue(0 <= r["risk_points"] <= 25)
            for k, v in r["layers"].items():
                self.assertTrue(0 <= v <= 100, f"{r['ticker']}.{k}={v}")

    def test_every_row_has_three_line_reason(self):
        for r in self.p["rows"]:
            self.assertEqual(len(r["reason"]), 3, r["ticker"])
            for line in r["reason"]:
                self.assertTrue(line.strip())

    def test_committee_has_six_agents_including_contrarian(self):
        for r in self.p["rows"][:10]:
            views = r["committee"]["views"]
            self.assertEqual(len(views), 6)
            self.assertIn("Contrarian Analyst", [v["agent"] for v in views])
            for v in views:
                self.assertTrue(v["comment"].strip(), "根拠のない意見は許容しない")

    def test_opportunities_are_downstream_not_drivers(self):
        driver_ids = {n["id"] for n in self.p["nodes"] if n["is_driver"]}
        for o in self.p["opportunities"]:
            self.assertNotIn(o["id"], driver_ids)
            self.assertGreaterEqual(o["pressure"], 55.0)

    def test_determinism(self):
        q = run("2026-08-29", "demo", False, None, write=False)
        self.assertEqual([r["ticker"] for r in q["rows"]],
                         [r["ticker"] for r in self.p["rows"]])
        self.assertEqual(q["rows"][0]["final_score"], self.p["rows"][0]["final_score"])

    def test_price_grade_caps_are_enforced(self):
        for r in self.p["rows"]:
            if r["f"]["per"] > 80:
                self.assertEqual(r["price_grade"], "D", r["ticker"])
            if r["f"]["per"] > 55:
                self.assertIn(r["price_grade"], ("C", "D"), r["ticker"])

    def test_guides_are_complete(self):
        self.assertTrue(self.p["guides"])
        for g in self.p["guides"]:
            self.assertTrue(g["table"])
            self.assertTrue(g["chains"])
            self.assertEqual(len(g["beginner_points"]), 3)
            self.assertTrue(g["cautions"])
            self.assertTrue(g["budget_examples"])
            for row in g["table"]:
                self.assertGreater(row["min_investment_jpy"], 0)
                self.assertLessEqual(row["entry_low"], row["entry_high"])

    def test_regional_subset_runs(self):
        p = run("2026-08-29", "demo", False, ["JP"], write=False)
        self.assertTrue(all(r["region"] == "JP" for r in p["rows"]))
