# -*- coding: utf-8 -*-
import unittest

from engine.scoring.normalize import PeerNormalizer, logistic_score, weighted_layer
from engine.scoring.layers import LAYER_WEIGHTS
from engine.scoring.aggregate import to_grade, price_grade_of, verdict_of, stars_of
from engine.scoring.valuation import fair_value, implied_growth_years, entry_zone
from engine.providers.base import Fundamentals


def F(**kw):
    base = dict(ticker="X", as_of="2026-01-01", price=100.0, prev_close=100.0)
    base.update(kw)
    return Fundamentals(**base)


class TestNormalize(unittest.TestCase):
    def test_logistic_bounds(self):
        self.assertAlmostEqual(logistic_score(0.0), 50.0, places=6)
        self.assertGreater(logistic_score(2.5), 85.0)
        self.assertLess(logistic_score(-2.5), 15.0)
        self.assertLess(logistic_score(99), 100.0)

    def test_direction_inverts(self):
        rows = {f"t{i}": {"per": float(i * 5 + 5)} for i in range(12)}
        meta = {k: {"sector": "S", "region": "R"} for k in rows}
        n = PeerNormalizer(rows, meta)
        cheap = n.score("t0", "per", -1)
        rich = n.score("t11", "per", -1)
        self.assertGreater(cheap, rich, "PERは小さいほど高得点でなければならない")

    def test_missing_is_none_not_zero(self):
        rows = {"a": {"roe": None}, "b": {"roe": 10.0}}
        meta = {k: {"sector": "S", "region": "R"} for k in rows}
        n = PeerNormalizer(rows, meta)
        self.assertIsNone(n.score("a", "roe", 1))

    def test_weighted_layer_redistributes_missing_weight(self):
        s1, cov1, _ = weighted_layer([("a", 80.0, 0.5), ("b", 80.0, 0.5)])
        s2, cov2, _ = weighted_layer([("a", 80.0, 0.5), ("b", None, 0.5)])
        self.assertAlmostEqual(s1, s2, places=6, msg="欠損で点が下がってはいけない（下がるのは確信度）")
        self.assertEqual(cov1, 1.0)
        self.assertEqual(cov2, 0.5)

    def test_small_group_falls_back(self):
        rows = {f"t{i}": {"roe": float(i)} for i in range(12)}
        meta = {f"t{i}": {"sector": "S" if i else "LONELY", "region": "R"} for i in range(12)}
        n = PeerNormalizer(rows, meta)
        key, peers = n.group_for("t0")
        self.assertGreaterEqual(len(peers), 8, "ピアが少なすぎる場合は母集団を広げる")


class TestGrades(unittest.TestCase):
    def test_layer_weights_sum_to_100(self):
        self.assertEqual(sum(LAYER_WEIGHTS.values()), 100.0)

    def test_grade_bands(self):
        self.assertEqual(to_grade(90), "S")
        self.assertEqual(to_grade(70), "A")
        self.assertEqual(to_grade(60), "B")
        self.assertEqual(to_grade(50), "C")
        self.assertEqual(to_grade(10), "D")

    def test_expensive_quality_stock_is_capped(self):
        """Quality/Growth/Trend が最高でも、PER80倍・FCF利回り1%なら価格評価はC以下。"""
        g, caps = price_grade_of(95.0, F(per=85.0, peg=4.0, fcf_yield=0.9, ev_ebitda=50.0))
        self.assertEqual(g, "D")
        self.assertTrue(caps)

    def test_cheap_stock_keeps_grade(self):
        g, caps = price_grade_of(80.0, F(per=12.0, peg=0.9, fcf_yield=7.0, ev_ebitda=8.0))
        self.assertEqual(g, "S")
        self.assertFalse(caps)

    def test_verdict_separates_good_company_from_good_price(self):
        k, label = verdict_of(60.0, "S", "D")
        self.assertEqual(k, "QUALITY_WAIT")
        k2, _ = verdict_of(70.0, "A", "A")
        self.assertEqual(k2, "STRONG_CANDIDATE")

    def test_stars_penalise_illiquidity(self):
        from engine.universe import by_ticker
        big = by_ticker("NVDA")
        small = by_ticker("3776.T")
        f = F(vol_ann=0.30, adv_musd=500)
        f_small = F(vol_ann=0.60, adv_musd=3)
        self.assertGreater(stars_of(70, 3, f, big), stars_of(70, 3, f_small, small))


class TestValuation(unittest.TestCase):
    def test_fair_value_between_bounds(self):
        f = F(price=100.0, per=20.0, fcf_yield=5.0, eps_cagr3=15.0)
        fv, methods = fair_value(f, 25.0, 4.0, 60.0, 60.0)
        self.assertTrue(40.0 <= fv <= 200.0)
        self.assertTrue(methods)

    def test_no_data_returns_price(self):
        f = F(price=100.0)
        fv, methods = fair_value(f, 0.0, 0.0, 50.0, 50.0)
        self.assertEqual(fv, 100.0)
        self.assertEqual(methods, {})

    def test_implied_years_grows_with_per(self):
        a = implied_growth_years(F(per=40.0, eps_cagr3=20.0))
        b = implied_growth_years(F(per=80.0, eps_cagr3=20.0))
        self.assertLess(a, b)
        self.assertIsNone(implied_growth_years(F(per=12.0, eps_cagr3=20.0)))

    def test_entry_zone_below_fair_value(self):
        lo, hi = entry_zone(1000.0, 900.0, 10.0, "JPY")
        self.assertLess(hi, 1000.0)
        self.assertLess(lo, hi)

    def test_entry_zone_tracks_price_when_already_cheap(self):
        lo, hi = entry_zone(1000.0, 300.0, 5.0, "JPY")
        self.assertLess(lo, 300.0)
        self.assertGreater(hi, 300.0)

    def test_higher_risk_demands_bigger_discount(self):
        _, hi_low_risk = entry_zone(1000.0, 2000.0, 0.0, "JPY")
        _, hi_high_risk = entry_zone(1000.0, 2000.0, 25.0, "JPY")
        self.assertGreater(hi_low_risk, hi_high_risk)
