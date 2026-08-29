# -*- coding: utf-8 -*-
import unittest

from engine.demand.graph import (NODES, EDGES, NODE_MAP, validate, topo_order,
                                 depth_map, paths_to, SIGNAL_LABELS)
from engine.universe import UNIVERSE


class TestDemandGraph(unittest.TestCase):
    def test_graph_is_valid_and_acyclic(self):
        validate()
        self.assertEqual(len(topo_order()), len(NODES))

    def test_node_ids_unique(self):
        ids = [n.id for n in NODES]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_signal_is_known(self):
        for n in NODES:
            for s in n.signals:
                self.assertIn(s, SIGNAL_LABELS, f"{n.id} の未知シグナル {s}")

    def test_every_company_exposure_maps_to_a_node(self):
        """ユニバースの露出キーがグラフに存在しないと、需要が黙って消える。"""
        for c in UNIVERSE:
            for nid in c.nodes:
                self.assertIn(nid, NODE_MAP, f"{c.ticker} の露出ノード {nid} がグラフに無い")

    def test_exposure_weights_are_sane(self):
        for c in UNIVERSE:
            total = sum(c.nodes.values())
            self.assertLessEqual(total, 1.2, f"{c.ticker} の露出合計が大きすぎる: {total}")
            for w in c.nodes.values():
                self.assertGreater(w, 0)
                self.assertLessEqual(w, 1.0)

    def test_drivers_have_no_parents(self):
        dsts = {e.dst for e in EDGES}
        for n in NODES:
            if n.is_driver:
                self.assertNotIn(n.id, dsts, f"ドライバー {n.id} に上流がある")

    def test_depth_of_transformer_is_downstream(self):
        d = depth_map()
        self.assertGreaterEqual(d["transformer"], 3)
        chains = [" → ".join(p) for p in paths_to("transformer")]
        self.assertTrue(any("genai_capex" in c for c in chains),
                        "生成AI設備投資から変圧器への因果経路が存在しない")


class TestUniverse(unittest.TestCase):
    def test_tickers_unique(self):
        t = [c.ticker for c in UNIVERSE]
        self.assertEqual(len(t), len(set(t)))

    def test_lot_and_price_positive(self):
        for c in UNIVERSE:
            self.assertGreaterEqual(c.lot, 1)
            self.assertGreater(c.price_anchor, 0)
            self.assertGreater(c.mcap_musd, 0)

    def test_profile_params_in_range(self):
        for c in UNIVERSE:
            for k in ("q", "g", "v", "lev", "mom", "gov"):
                v = getattr(c, k)
                self.assertTrue(0.0 <= v <= 1.0, f"{c.ticker}.{k}={v}")
            self.assertTrue(0.05 <= c.vol <= 1.0, f"{c.ticker}.vol={c.vol}")

    def test_regions_covered(self):
        regions = {c.region for c in UNIVERSE}
        self.assertTrue({"JP", "US", "EU", "ASIA"} <= regions)
