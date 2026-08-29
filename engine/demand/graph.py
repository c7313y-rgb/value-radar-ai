# -*- coding: utf-8 -*-
"""
需要連鎖グラフ（Demand Graph）

「AIが流行っている」ではなく
「DC建設増 → 電力設備発注増 → 変圧器リードタイム上昇 → 受注残増 → だが株価評価は未追随」
という因果の鎖を、有向グラフとして明示的に持つ。

各エッジは lag_months（需要が伝播するまでの月数）と elasticity（伝播係数）を持つ。
これにより「NVIDIAが上がりきった後、次に利益が流れ込むのはどこか」を
機械的に遡れる。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, deque


@dataclass
class Node:
    id: str
    label: str
    desc: str
    signals: List[str] = field(default_factory=list)   # Demand Evidence の観測項目
    is_driver: bool = False


@dataclass
class Edge:
    src: str
    dst: str
    lag_months: float
    elasticity: float     # 0-1。上流需要のうち下流へ流れる割合の目安
    note: str = ""


# --- 観測シグナルの語彙 -----------------------------------------------------
SIGNAL_LABELS = {
    "orders_backlog": "受注残・受注高",
    "capex_plan": "設備投資計画",
    "gov_budget": "政府予算・補助金",
    "job_postings": "求人数",
    "plant_construction": "工場・DC着工",
    "power_demand": "電力需要・系統接続申請",
    "shipment_stats": "出荷統計",
    "lead_time": "リードタイム",
    "patents": "特許出願",
    "exec_commentary": "経営者発言（決算説明）",
    "price_index": "価格・スポット指標",
    "utilization": "稼働率",
}


NODES: List[Node] = [
    # ---- ドライバー（一次需要の源泉） ----
    Node("genai_capex", "生成AI設備投資", "ハイパースケーラの AI 向け資本的支出そのもの",
         ["capex_plan", "exec_commentary", "orders_backlog"], is_driver=True),
    Node("electrification", "電化・EV転換", "輸送と産業の電化に伴う電力・部材需要",
         ["shipment_stats", "gov_budget", "capex_plan"], is_driver=True),
    Node("labor_shortage", "労働力不足・省人化", "人手不足を資本で置換する圧力",
         ["job_postings", "gov_budget", "capex_plan"], is_driver=True),
    Node("geopolitics", "地政学・防衛費", "安全保障環境の悪化に伴う恒常的な予算増",
         ["gov_budget", "orders_backlog"], is_driver=True),
    Node("demographics", "高齢化・人口動態", "医療・介護・年金に向かう構造的支出",
         ["gov_budget", "shipment_stats"], is_driver=True),
    Node("macro_cycle", "景気・金利サイクル", "金利と消費の循環（構造要因ではなく循環要因）",
         ["price_index", "shipment_stats"], is_driver=True),

    # ---- 半導体・計算基盤 ----
    Node("gpu_accel", "GPU・AIアクセラレータ", "学習/推論用の計算チップ",
         ["orders_backlog", "lead_time", "shipment_stats", "exec_commentary"]),
    Node("hbm_memory", "HBM・先端メモリ", "広帯域メモリ。AIチップの帯域制約を解く部材",
         ["capex_plan", "lead_time", "price_index", "utilization"]),
    Node("adv_packaging", "先端パッケージング", "CoWoS等の2.5D/3D実装。物理的な供給律速",
         ["capex_plan", "utilization", "lead_time"]),
    Node("semi_foundry", "半導体ファウンドリ", "先端ロジックの受託製造",
         ["utilization", "capex_plan", "price_index"]),
    Node("semi_equip", "半導体製造装置", "前工程・検査装置",
         ["orders_backlog", "capex_plan", "shipment_stats"]),
    Node("semi_materials", "半導体材料", "ウェハ・レジスト・後工程材料",
         ["shipment_stats", "price_index", "utilization"]),
    Node("edge_ai", "エッジAI・端末推論", "端末側での推論。生成AIから遅れて到来する二次市場",
         ["shipment_stats", "patents", "exec_commentary"]),
    Node("software_ai", "AIソフトウェア・実装", "AIを業務に落とす層。設備投資の回収側",
         ["job_postings", "exec_commentary", "patents"]),

    # ---- データセンター物理層 ----
    Node("dc_build", "データセンター建設", "用地取得から竣工までのDC投資",
         ["plant_construction", "capex_plan", "power_demand"]),
    Node("server_oem", "サーバ製造・ODM", "AIサーバのラック組立",
         ["shipment_stats", "orders_backlog", "utilization"]),
    Node("cooling", "冷却（液冷・空調）", "空冷の限界を超える熱密度への対応",
         ["orders_backlog", "patents", "lead_time", "plant_construction"]),
    Node("dc_power", "DC電力設備", "受変電・非常用電源を含むDC構内電源",
         ["orders_backlog", "power_demand", "lead_time"]),
    Node("ups_pdu", "UPS・配電盤", "無停電電源装置と配電",
         ["orders_backlog", "lead_time", "shipment_stats"]),
    Node("network_switch", "ネットワーク機器", "スケールアウト網のスイッチ",
         ["shipment_stats", "orders_backlog"]),
    Node("optical_device", "光デバイス・トランシーバ", "800G/1.6T の光モジュール",
         ["shipment_stats", "lead_time", "price_index"]),
    Node("optical_fiber", "光ファイバ・ケーブル", "DC内配線とDC間接続",
         ["shipment_stats", "price_index", "orders_backlog"]),

    # ---- 電力インフラ ----
    Node("transformer", "変圧器", "北米を中心にリードタイムが数年に伸びた供給制約財",
         ["lead_time", "orders_backlog", "price_index"]),
    Node("grid_td", "送配電網", "系統増強・更新投資",
         ["capex_plan", "gov_budget", "power_demand", "orders_backlog"]),
    Node("power_gen", "発電設備", "ガスタービン・タービン・発電機",
         ["orders_backlog", "lead_time", "power_demand"]),
    Node("nuclear", "原子力", "既存炉の再稼働・延命とSMR",
         ["gov_budget", "power_demand", "exec_commentary"]),
    Node("renewables", "再生可能エネルギー", "太陽光・風力と蓄電",
         ["gov_budget", "capex_plan", "price_index"]),
    Node("power_semi", "パワー半導体", "SiC/IGBT。電力変換の中核部材",
         ["shipment_stats", "capex_plan", "price_index"]),
    Node("epc_construction", "建設・EPC", "プラント・大型建築の実行",
         ["orders_backlog", "plant_construction", "job_postings"]),

    # ---- 省人化・産業 ----
    Node("robotics", "ロボティクス", "産業用・サービスロボット",
         ["shipment_stats", "job_postings", "patents"]),
    Node("factory_auto", "ファクトリーオートメーション", "FA機器・制御",
         ["shipment_stats", "orders_backlog", "utilization"]),
    Node("machine_tools", "工作機械", "受注が景気の先行指標になる",
         ["orders_backlog", "shipment_stats"]),
    Node("ev_supply", "EV・車載部品", "電動化サプライチェーン",
         ["shipment_stats", "price_index", "capex_plan"]),
    Node("mining_equipment", "鉱山機械・資源設備", "資源開発に伴う設備",
         ["capex_plan", "price_index"]),
    Node("commodities", "資源・エネルギー", "原油・LNG・非鉄",
         ["price_index", "shipment_stats"]),

    # ---- 防衛・医療・消費・金融 ----
    Node("defense_prime", "防衛プライム", "装備品の元請",
         ["gov_budget", "orders_backlog"]),
    Node("defense_electronics", "防衛エレクトロニクス", "センサー・通信・電子戦",
         ["gov_budget", "orders_backlog", "patents"]),
    Node("aging_health", "高齢化・医療サービス", "医療費と介護の構造的増加",
         ["gov_budget", "shipment_stats"]),
    Node("pharma", "医薬品", "新薬の上市と特許",
         ["patents", "shipment_stats", "gov_budget"]),
    Node("consumer_us", "米国消費", "米国の個人消費",
         ["shipment_stats", "price_index"]),
    Node("consumer_asia", "アジア消費", "アジア新興国の中間層消費",
         ["shipment_stats", "price_index"]),
    Node("consumer_lux", "高級消費", "ラグジュアリー需要",
         ["shipment_stats", "price_index"]),
    Node("consumer_staples", "生活必需品", "食品・日用品",
         ["shipment_stats", "price_index"]),
    Node("rates_financials", "金利・金融", "金利水準と与信サイクル",
         ["price_index", "gov_budget"]),
]

EDGES: List[Edge] = [
    Edge("genai_capex", "gpu_accel", 3, 0.90, "AI予算は最初に計算資源へ向かう"),
    Edge("genai_capex", "dc_build", 6, 0.85, "計算資源を置く箱の確保"),
    Edge("genai_capex", "software_ai", 9, 0.50, "投資回収は実装層で起きる"),
    Edge("gpu_accel", "hbm_memory", 3, 0.90, "GPU1枚あたりHBM搭載量が増える"),
    Edge("gpu_accel", "adv_packaging", 3, 0.85, "CoWoS等の実装能力が律速"),
    Edge("gpu_accel", "semi_foundry", 2, 0.80, "先端ノードの占有"),
    Edge("gpu_accel", "server_oem", 2, 0.80, "ラック組立へ"),
    Edge("gpu_accel", "edge_ai", 12, 0.40, "遅れて端末側推論へ波及"),
    Edge("hbm_memory", "semi_equip", 6, 0.75, "メモリ増産投資が装置発注に化ける"),
    Edge("adv_packaging", "semi_equip", 5, 0.80, "後工程装置の発注"),
    Edge("semi_foundry", "semi_equip", 6, 0.80, "ファウンドリ設備投資"),
    Edge("semi_equip", "semi_materials", 4, 0.70, "装置稼働は材料消費を生む"),
    Edge("dc_build", "dc_power", 4, 0.90, "受変電が着工直後に必要"),
    Edge("dc_build", "cooling", 5, 0.85, "熱密度の上昇で液冷が必須化"),
    Edge("dc_build", "network_switch", 3, 0.70, "内部網の構築"),
    Edge("dc_build", "epc_construction", 6, 0.60, "建屋そのものの施工"),
    Edge("server_oem", "cooling", 4, 0.60, "ラック単位の冷却要求"),
    Edge("network_switch", "optical_device", 3, 0.80, "スイッチ1台あたり光モジュール多数"),
    Edge("optical_device", "optical_fiber", 4, 0.70, "配線とDC間接続"),
    Edge("dc_power", "ups_pdu", 5, 0.85, "無停電化と配電"),
    Edge("ups_pdu", "transformer", 6, 0.80, "受電容量の増強"),
    Edge("ups_pdu", "power_semi", 6, 0.60, "電力変換素子の需要"),
    Edge("transformer", "grid_td", 7, 0.85, "系統側の増強が追随"),
    Edge("grid_td", "power_gen", 10, 0.70, "最終的に発電容量が必要"),
    Edge("power_gen", "nuclear", 14, 0.60, "ベースロード電源の再評価"),
    Edge("power_gen", "renewables", 10, 0.50, "並行して再エネ調達"),
    Edge("power_gen", "epc_construction", 10, 0.50, "発電所建設"),
    Edge("electrification", "power_semi", 6, 0.70, ""),
    Edge("electrification", "ev_supply", 6, 0.80, ""),
    Edge("electrification", "grid_td", 12, 0.60, "EV充電負荷が系統に効く"),
    Edge("labor_shortage", "robotics", 9, 0.80, ""),
    Edge("robotics", "factory_auto", 4, 0.80, ""),
    Edge("factory_auto", "machine_tools", 6, 0.70, ""),
    Edge("geopolitics", "defense_prime", 12, 0.85, "予算計上から発注まで時間差"),
    Edge("defense_prime", "defense_electronics", 6, 0.80, ""),
    Edge("demographics", "aging_health", 12, 0.70, ""),
    Edge("aging_health", "pharma", 12, 0.60, ""),
    Edge("macro_cycle", "rates_financials", 3, 0.60, ""),
    Edge("macro_cycle", "consumer_us", 6, 0.60, ""),
    Edge("macro_cycle", "consumer_asia", 9, 0.50, ""),
    Edge("macro_cycle", "consumer_lux", 9, 0.50, ""),
    Edge("macro_cycle", "consumer_staples", 6, 0.30, ""),
    Edge("macro_cycle", "commodities", 6, 0.50, ""),
    Edge("commodities", "mining_equipment", 12, 0.60, ""),
]


NODE_MAP: Dict[str, Node] = {n.id: n for n in NODES}
_CHILDREN: Dict[str, List[Edge]] = defaultdict(list)
_PARENTS: Dict[str, List[Edge]] = defaultdict(list)
for _e in EDGES:
    _CHILDREN[_e.src].append(_e)
    _PARENTS[_e.dst].append(_e)


def children(node_id: str) -> List[Edge]:
    return _CHILDREN.get(node_id, [])


def parents(node_id: str) -> List[Edge]:
    return _PARENTS.get(node_id, [])


def validate() -> None:
    """全エッジの端点が存在し、グラフが非巡回であることを保証する。"""
    for e in EDGES:
        assert e.src in NODE_MAP, f"unknown src node: {e.src}"
        assert e.dst in NODE_MAP, f"unknown dst node: {e.dst}"
        assert 0.0 < e.elasticity <= 1.0, f"bad elasticity: {e}"
        assert e.lag_months >= 0, f"bad lag: {e}"
    indeg = {n.id: 0 for n in NODES}
    for e in EDGES:
        indeg[e.dst] += 1
    q = deque([n for n, d in indeg.items() if d == 0])
    seen = 0
    while q:
        cur = q.popleft()
        seen += 1
        for e in children(cur):
            indeg[e.dst] -= 1
            if indeg[e.dst] == 0:
                q.append(e.dst)
    assert seen == len(NODES), "需要グラフに循環がある（波及計算が発散します）"


def topo_order() -> List[str]:
    indeg = {n.id: 0 for n in NODES}
    for e in EDGES:
        indeg[e.dst] += 1
    q = deque(sorted([n for n, d in indeg.items() if d == 0]))
    out: List[str] = []
    while q:
        cur = q.popleft()
        out.append(cur)
        for e in sorted(children(cur), key=lambda x: x.dst):
            indeg[e.dst] -= 1
            if indeg[e.dst] == 0:
                q.append(e.dst)
    return out


def depth_map() -> Dict[str, int]:
    """ドライバーからの最短波及段数（1次needs=1, 2次=2, 3次=3 ...）。"""
    depth: Dict[str, int] = {}
    for n in NODES:
        if n.is_driver:
            depth[n.id] = 0
    for nid in topo_order():
        if nid in depth:
            continue
        ps = parents(nid)
        depth[nid] = min((depth.get(p.src, 0) for p in ps), default=0) + 1
    return depth


def paths_to(node_id: str, max_depth: int = 8) -> List[List[str]]:
    """ドライバーから当該ノードに至る因果経路を列挙する（説明生成に使う）。"""
    results: List[List[str]] = []

    def walk(cur: str, acc: List[str]) -> None:
        if len(acc) > max_depth:
            return
        ps = parents(cur)
        if not ps:
            results.append(list(reversed(acc)))
            return
        for e in ps:
            walk(e.src, acc + [e.src])

    walk(node_id, [node_id])
    return results


def chain_label(path: List[str]) -> str:
    return " → ".join(NODE_MAP[p].label for p in path if p in NODE_MAP)


if __name__ == "__main__":
    validate()
    d = depth_map()
    print("nodes:", len(NODES), "edges:", len(EDGES))
    for nid in topo_order():
        print(f"  [{d[nid]}] {nid:20s} {NODE_MAP[nid].label}")
    print()
    for p in paths_to("transformer"):
        print("  path:", chain_label(p))
