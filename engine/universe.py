# -*- coding: utf-8 -*-
"""
VALUE RADAR AI — 企業マスター（ユニバース定義）

MSCI ACWI 的な「世界の投資可能株式市場を広くカバーする」という母集団思想を
デモ規模（日米欧アジア 80銘柄）に縮約したもの。

重要（正直な注記）:
  ticker / 企業名 / 上場市場 / 売買単位 / 事業内容 は実在の公開情報に基づく。
  price_anchor と profile_* は「デモ用の合成パラメータ」であり実際の株価・
  財務数値ではない。実データは providers/yfinance_provider.py 等に切り替える。
  優待(yutai)・配当利回り(div_yield)もデモ既定ではプレースホルダである。

profile_* の意味（0.0〜1.0の相対位置、デモデータ生成の種）:
  q   : 事業品質（ROE/ROIC/利益率/FCF安定性の高さ）
  g   : 成長期待（売上・EPS・FCFの伸び）
  v   : バリュエーションの「高さ」（1.0に近いほど割高＝PERが高い）
  lev : レバレッジ（1.0に近いほど負債が重い）
  vol : 年率ボラティリティ（実数、0.15〜0.65程度）
  mom : 株価モメンタム（1.0に近いほど直近の上昇が強い）
  gov : ガバナンス・経営品質の定性評価（0.0〜1.0）
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional


@dataclass
class Company:
    ticker: str
    name: str
    name_en: str
    region: str          # JP / US / EU / ASIA
    country: str
    currency: str
    exchange: str
    sector: str
    industry: str
    lot: int             # 売買単位（日本株は通常100、米欧は1）
    price_anchor: float  # デモ用の基準株価（実株価ではない）
    mcap_musd: float     # デモ用の時価総額（百万USD）
    biz: str             # 事業内容の一行要約
    nodes: Dict[str, float] = field(default_factory=dict)  # 需要ノードへの感応度
    sites: List[str] = field(default_factory=list)         # 需要が発生している拠点・現場
    yutai: Optional[str] = None                            # 株主優待（日本株）
    div_yield: float = 0.0
    q: float = 0.5
    g: float = 0.5
    v: float = 0.5
    lev: float = 0.4
    vol: float = 0.30
    mom: float = 0.5
    gov: float = 0.5

    def to_dict(self) -> dict:
        return asdict(self)


def C(*args, **kwargs) -> Company:
    return Company(*args, **kwargs)


# ---------------------------------------------------------------------------
# 日本株（東証）
# ---------------------------------------------------------------------------
JP: List[Company] = [
    C("6501.T", "日立製作所", "Hitachi", "JP", "日本", "JPY", "TSE Prime",
      "資本財", "重電・社会インフラ", 100, 4820.0, 148000,
      "送配電・鉄道・エネルギーとITを束ねる社会インフラ大手。Lumadaでデジタル化収益を拡大",
      {"grid_td": 0.30, "power_gen": 0.12, "dc_build": 0.10, "factory_auto": 0.10},
      ["茨城県日立市（電力機器）", "山口県下松市（鉄道車両）"],
      None, 1.4, q=0.74, g=0.62, v=0.58, lev=0.42, vol=0.27, mom=0.72, gov=0.72),

    C("6503.T", "三菱電機", "Mitsubishi Electric", "JP", "日本", "JPY", "TSE Prime",
      "資本財", "重電・FA", 100, 3180.0, 44000,
      "FA機器・パワー半導体・受変電設備・空調を持つ総合電機",
      {"factory_auto": 0.28, "grid_td": 0.18, "power_semi": 0.15, "cooling": 0.08},
      ["兵庫県尼崎市（受変電）", "福岡県福岡市（パワー半導体）"],
      None, 2.4, q=0.62, g=0.48, v=0.42, lev=0.32, vol=0.26, mom=0.55, gov=0.55),

    C("6504.T", "富士電機", "Fuji Electric", "JP", "日本", "JPY", "TSE Prime",
      "資本財", "パワー半導体・受変電", 100, 8900.0, 9500,
      "パワー半導体とUPS・受変電設備。データセンター電源で受注拡大",
      {"power_semi": 0.30, "ups_pdu": 0.25, "grid_td": 0.15, "dc_power": 0.12},
      ["長野県松本市（パワー半導体）", "三重県四日市市（受変電）"],
      None, 1.9, q=0.66, g=0.60, v=0.46, lev=0.34, vol=0.30, mom=0.66, gov=0.58),

    C("6506.T", "安川電機", "Yaskawa Electric", "JP", "日本", "JPY", "TSE Prime",
      "資本財", "サーボ・産業用ロボット", 100, 3950.0, 7000,
      "ACサーボ・インバータ世界大手。産業用ロボットで省人化需要を取り込む",
      {"robotics": 0.34, "factory_auto": 0.28, "power_semi": 0.06},
      ["福岡県北九州市（ロボット村）"],
      None, 1.5, q=0.68, g=0.52, v=0.60, lev=0.20, vol=0.33, mom=0.42, gov=0.60),

    C("6954.T", "ファナック", "FANUC", "JP", "日本", "JPY", "TSE Prime",
      "資本財", "CNC・産業用ロボット", 100, 4450.0, 28000,
      "工作機械用CNCで世界シェア首位級。無借金経営と高収益体質",
      {"factory_auto": 0.36, "robotics": 0.26, "machine_tools": 0.18},
      ["山梨県忍野村（本社工場）"],
      None, 2.1, q=0.82, g=0.40, v=0.66, lev=0.05, vol=0.28, mom=0.38, gov=0.62),

    C("6857.T", "アドバンテスト", "Advantest", "JP", "日本", "JPY", "TSE Prime",
      "情報技術", "半導体テスタ", 100, 9800.0, 51000,
      "SoC/メモリテスタ世界首位級。HBMとAI向け先端ロジックの検査需要を独占的に享受",
      {"hbm_memory": 0.30, "semi_equip": 0.34, "gpu_accel": 0.16},
      ["群馬県邑楽郡（テスタ生産）"],
      None, 0.4, q=0.80, g=0.86, v=0.90, lev=0.12, vol=0.48, mom=0.90, gov=0.60),

    C("8035.T", "東京エレクトロン", "Tokyo Electron", "JP", "日本", "JPY", "TSE Prime",
      "情報技術", "半導体製造装置", 100, 27500.0, 86000,
      "コータ／デベロッパで世界独占的シェア。前工程装置の中核",
      {"semi_equip": 0.46, "adv_packaging": 0.14, "hbm_memory": 0.12},
      ["山梨県韮崎市", "岩手県奥州市"],
      None, 1.6, q=0.83, g=0.70, v=0.74, lev=0.08, vol=0.42, mom=0.74, gov=0.64),

    C("6146.T", "ディスコ", "Disco", "JP", "日本", "JPY", "TSE Prime",
      "情報技術", "ダイシング・グラインディング装置", 100, 42000.0, 30000,
      "半導体切断・研削装置で世界首位。HBM積層と先端パッケージの必需装置",
      {"adv_packaging": 0.40, "hbm_memory": 0.26, "semi_equip": 0.20},
      ["広島県呉市", "長野県茅野市"],
      None, 0.7, q=0.86, g=0.78, v=0.88, lev=0.06, vol=0.46, mom=0.80, gov=0.62),

    C("6920.T", "レーザーテック", "Lasertec", "JP", "日本", "JPY", "TSE Prime",
      "情報技術", "EUVマスク検査装置", 100, 18500.0, 11000,
      "EUVマスクブランクス欠陥検査装置を独占供給。極端に高い利益率と高いボラティリティ",
      {"semi_equip": 0.52, "adv_packaging": 0.10},
      ["神奈川県横浜市"],
      None, 0.9, q=0.74, g=0.66, v=0.92, lev=0.18, vol=0.58, mom=0.44, gov=0.40),

    C("4063.T", "信越化学工業", "Shin-Etsu Chemical", "JP", "日本", "JPY", "TSE Prime",
      "素材", "シリコンウェハ・塩ビ", 100, 5100.0, 68000,
      "300mmシリコンウェハとフォトレジストで世界首位級。圧倒的な財務健全性",
      {"semi_materials": 0.42, "semi_equip": 0.10, "epc_construction": 0.08},
      ["群馬県安中市", "福井県武生市"],
      None, 2.0, q=0.88, g=0.48, v=0.44, lev=0.04, vol=0.29, mom=0.46, gov=0.66),

    C("4004.T", "レゾナック・ホールディングス", "Resonac", "JP", "日本", "JPY", "TSE Prime",
      "素材", "半導体後工程材料", 100, 3900.0, 8200,
      "半導体後工程材料でトップシェア群。先端パッケージ材料の需要拡大局面",
      {"semi_materials": 0.40, "adv_packaging": 0.24},
      ["山形県山形市", "神奈川県川崎市"],
      None, 1.6, q=0.48, g=0.64, v=0.50, lev=0.66, vol=0.40, mom=0.62, gov=0.48),

    C("4062.T", "イビデン", "Ibiden", "JP", "日本", "JPY", "TSE Prime",
      "情報技術", "ICパッケージ基板", 100, 6400.0, 6300,
      "サーバCPU/GPU向けFC-BGA基板の中核サプライヤ",
      {"adv_packaging": 0.44, "gpu_accel": 0.20, "server_oem": 0.10},
      ["岐阜県大垣市"],
      None, 0.9, q=0.62, g=0.70, v=0.72, lev=0.36, vol=0.44, mom=0.68, gov=0.52),

    C("6981.T", "村田製作所", "Murata", "JP", "日本", "JPY", "TSE Prime",
      "情報技術", "電子部品（MLCC）", 100, 2450.0, 33000,
      "MLCC世界首位。AIサーバ・車載向けで数量と単価が同時に伸びる局面",
      {"server_oem": 0.20, "gpu_accel": 0.12, "power_semi": 0.10, "ev_supply": 0.14},
      ["福井県越前市", "島根県出雲市"],
      None, 1.7, q=0.72, g=0.50, v=0.54, lev=0.14, vol=0.30, mom=0.52, gov=0.62),

    C("6971.T", "京セラ", "Kyocera", "JP", "日本", "JPY", "TSE Prime",
      "情報技術", "セラミック部品・パッケージ", 100, 1780.0, 17000,
      "セラミックパッケージと電子部品。KDDI株の保有による資産バリュー",
      {"adv_packaging": 0.18, "server_oem": 0.10, "optical_device": 0.10},
      ["鹿児島県霧島市", "滋賀県野洲市"],
      None, 2.6, q=0.46, g=0.30, v=0.30, lev=0.16, vol=0.26, mom=0.34, gov=0.44),

    C("6594.T", "ニデック", "Nidec", "JP", "日本", "JPY", "TSE Prime",
      "資本財", "モーター・液冷CDU", 100, 2184.0, 17500,
      "精密小型モーター世界首位。データセンター液冷用CDUで先行",
      {"cooling": 0.30, "ev_supply": 0.20, "robotics": 0.10, "dc_power": 0.08},
      ["京都府京都市", "滋賀県（開発拠点）"],
      "QUOカード（保有期間条件あり・要IR確認）", 1.0,
      q=0.44, g=0.56, v=0.56, lev=0.58, vol=0.40, mom=0.36, gov=0.26),

    C("1982.T", "日比谷総合設備", "Hibiya Engineering", "JP", "日本", "JPY", "TSE Prime",
      "資本財", "空調・電気設備施工", 100, 2835.0, 1100,
      "空調・給排水・電気設備の設計施工。データセンター案件の実装力に強み",
      {"dc_build": 0.36, "cooling": 0.24, "epc_construction": 0.14},
      ["千葉県印西市周辺（DC集積地）"],
      "クオカード（長期保有で増額・要IR確認）", 2.8,
      q=0.60, g=0.58, v=0.26, lev=0.10, vol=0.28, mom=0.64, gov=0.52),

    C("1979.T", "大気社", "Taikisha", "JP", "日本", "JPY", "TSE Prime",
      "資本財", "産業空調・クリーンルーム", 100, 4900.0, 1600,
      "塗装プラントとクリーンルーム空調。半導体・DC双方の空調需要に接続",
      {"cooling": 0.30, "dc_build": 0.18, "semi_equip": 0.10, "epc_construction": 0.12},
      ["神奈川県（技術研究所）"],
      None, 2.6, q=0.58, g=0.50, v=0.30, lev=0.12, vol=0.29, mom=0.56, gov=0.50),

    C("5801.T", "古河電気工業", "Furukawa Electric", "JP", "日本", "JPY", "TSE Prime",
      "素材", "光ファイバ・電力ケーブル", 100, 6900.0, 3600,
      "光ファイバ母材と電力ケーブル。DC間接続と送電網更新の両方に効く",
      {"optical_fiber": 0.34, "grid_td": 0.22, "optical_device": 0.12},
      ["千葉県市原市", "三重県亀山市"],
      None, 1.1, q=0.44, g=0.68, v=0.62, lev=0.62, vol=0.46, mom=0.78, gov=0.44),

    C("5802.T", "住友電気工業", "Sumitomo Electric", "JP", "日本", "JPY", "TSE Prime",
      "素材", "電線・光ファイバ・自動車部品", 100, 3450.0, 18000,
      "海底ケーブル・送電線・光ファイバ。系統増強の直接受益",
      {"grid_td": 0.30, "optical_fiber": 0.22, "ev_supply": 0.14},
      ["大阪府大阪市", "兵庫県伊丹市"],
      None, 2.0, q=0.52, g=0.58, v=0.40, lev=0.44, vol=0.32, mom=0.62, gov=0.52),

    C("5803.T", "フジクラ", "Fujikura", "JP", "日本", "JPY", "TSE Prime",
      "素材", "光ファイバ・DC配線", 100, 9800.0, 15000,
      "細径光ケーブルと融着接続機。北米DC投資の直接的受益で株価が急騰した銘柄",
      {"optical_fiber": 0.40, "dc_build": 0.16, "optical_device": 0.14},
      ["千葉県佐倉市", "茨城県土浦市"],
      None, 0.8, q=0.60, g=0.86, v=0.86, lev=0.40, vol=0.60, mom=0.94, gov=0.46),

    C("7011.T", "三菱重工業", "Mitsubishi Heavy Industries", "JP", "日本", "JPY", "TSE Prime",
      "資本財", "ガスタービン・原子力・防衛", 100, 3300.0, 76000,
      "ガスタービンで世界首位級。原子力・防衛・DC向け電源の三重の追い風",
      {"power_gen": 0.34, "nuclear": 0.16, "defense_prime": 0.24, "dc_power": 0.08},
      ["兵庫県高砂市（ガスタービン）", "長崎県（原子力）"],
      None, 0.8, q=0.56, g=0.74, v=0.80, lev=0.48, vol=0.38, mom=0.86, gov=0.54),

    C("6areas.T", "PLACEHOLDER", "placeholder", "JP", "日本", "JPY", "TSE Prime",
      "資本財", "placeholder", 100, 1000.0, 100, "placeholder", {}, [], None, 0.0),

    C("1801.T", "大成建設", "Taisei", "JP", "日本", "JPY", "TSE Prime",
      "資本財", "総合建設", 100, 7300.0, 5200,
      "大型建築・土木。データセンター建設と再開発の受注残が積み上がる",
      {"dc_build": 0.24, "epc_construction": 0.34},
      ["千葉県印西市", "東京都（再開発）"],
      None, 2.7, q=0.42, g=0.46, v=0.28, lev=0.30, vol=0.28, mom=0.50, gov=0.40),

    C("1802.T", "大林組", "Obayashi", "JP", "日本", "JPY", "TSE Prime",
      "資本財", "総合建設", 100, 2350.0, 11000,
      "建築・土木に加え再エネ発電事業を保有。DC・半導体工場建設の受け皿",
      {"dc_build": 0.22, "epc_construction": 0.32, "renewables": 0.10},
      ["熊本県菊陽町（半導体工場周辺）"],
      None, 2.9, q=0.46, g=0.44, v=0.30, lev=0.28, vol=0.26, mom=0.54, gov=0.46),

    C("9432.T", "日本電信電話", "NTT", "JP", "日本", "JPY", "TSE Prime",
      "通信", "総合通信・データセンター", 100, 157.8, 90000,
      "国内通信最大手。海外DC事業とIOWN構想で電力効率を軸に展開",
      {"dc_build": 0.20, "network_switch": 0.12, "optical_device": 0.14},
      ["東京都（IOWN）", "海外DC（複数）"],
      "dポイント進呈（保有期間条件あり・要IR確認）", 3.3,
      q=0.56, g=0.24, v=0.24, lev=0.68, vol=0.19, mom=0.32, gov=0.56),

    C("3774.T", "インターネットイニシアティブ", "IIJ", "JP", "日本", "JPY", "TSE Prime",
      "情報技術", "ネットワーク・DC運営", 100, 2529.5, 3900,
      "法人ネットワークとDC運営。水冷Ready設計のDCを増設中",
      {"dc_build": 0.26, "network_switch": 0.18, "cooling": 0.10},
      ["千葉県白井市（DC）", "島根県松江市"],
      "QUOカード（保有条件あり・要IR確認）", 0.8,
      q=0.58, g=0.60, v=0.66, lev=0.30, vol=0.34, mom=0.60, gov=0.54),

    C("3776.T", "ブロードバンドタワー", "Broadband Tower", "JP", "日本", "JPY", "TSE Standard",
      "情報技術", "データセンター運営", 100, 227.0, 90,
      "高集積データセンターの運営とクラウド。小型株で流動性は低い",
      {"dc_build": 0.34, "cooling": 0.10},
      ["東京都（DC）"],
      None, 0.0, q=0.24, g=0.44, v=0.58, lev=0.52, vol=0.62, mom=0.58, gov=0.30),

    C("6areas2.T", "PLACEHOLDER2", "placeholder", "JP", "日本", "JPY", "TSE Prime",
      "資本財", "placeholder", 100, 1000.0, 100, "placeholder", {}, [], None, 0.0),

    C("6301.T", "小松製作所", "Komatsu", "JP", "日本", "JPY", "TSE Prime",
      "資本財", "建設機械", 100, 4700.0, 30000,
      "建機世界2位。DC・半導体工場・鉱山の建設需要に接続",
      {"epc_construction": 0.24, "mining_equipment": 0.20},
      ["石川県小松市", "栃木県小山市"],
      None, 3.2, q=0.62, g=0.40, v=0.34, lev=0.36, vol=0.28, mom=0.48, gov=0.58),

    C("4568.T", "第一三共", "Daiichi Sankyo", "JP", "日本", "JPY", "TSE Prime",
      "ヘルスケア", "医薬品", 100, 3400.0, 44000,
      "ADC（抗体薬物複合体）を軸としたがん領域のグローバル展開",
      {"pharma": 0.44, "aging_health": 0.20},
      ["静岡県（生産）"],
      None, 1.2, q=0.64, g=0.62, v=0.78, lev=0.20, vol=0.31, mom=0.40, gov=0.62),

    C("4519.T", "中外製薬", "Chugai", "JP", "日本", "JPY", "TSE Prime",
      "ヘルスケア", "医薬品", 100, 7300.0, 40000,
      "ロシュ傘下で独自の抗体技術。高収益・高ROEの創薬企業",
      {"pharma": 0.46, "aging_health": 0.16},
      ["静岡県御殿場市", "神奈川県横浜市"],
      None, 2.0, q=0.84, g=0.44, v=0.70, lev=0.04, vol=0.30, mom=0.50, gov=0.64),

    C("9983.T", "ファーストリテイリング", "Fast Retailing", "JP", "日本", "JPY", "TSE Prime",
      "一般消費財", "アパレル小売", 100, 48000.0, 100000,
      "ユニクロのグローバル展開。アジア新興国の中間層拡大に連動",
      {"consumer_asia": 0.40},
      ["山口県山口市", "東京都有明"],
      None, 0.9, q=0.76, g=0.54, v=0.84, lev=0.24, vol=0.30, mom=0.44, gov=0.50),

    C("8306.T", "三菱UFJフィナンシャル・グループ", "MUFG", "JP", "日本", "JPY", "TSE Prime",
      "金融", "銀行", 100, 2050.0, 160000,
      "国内最大の金融グループ。金利上昇局面での収益改善と資本還元",
      {"rates_financials": 0.44},
      ["東京都千代田区"],
      None, 3.0, q=0.50, g=0.42, v=0.30, lev=0.80, vol=0.28, mom=0.66, gov=0.52),

    C("8058.T", "三菱商事", "Mitsubishi Corp", "JP", "日本", "JPY", "TSE Prime",
      "資本財", "総合商社", 100, 2900.0, 78000,
      "資源・機械・食品の分散ポートフォリオ。資本効率改善と大型自社株買い",
      {"commodities": 0.30, "renewables": 0.10, "rates_financials": 0.08},
      ["東京都千代田区"],
      None, 3.6, q=0.56, g=0.30, v=0.26, lev=0.54, vol=0.27, mom=0.52, gov=0.56),
]

# プレースホルダを除去
JP = [c for c in JP if not c.name.startswith("PLACEHOLDER")]


# ---------------------------------------------------------------------------
# 米国株（NYSE / NASDAQ）— 1株単位
# ---------------------------------------------------------------------------
US: List[Company] = [
    C("NVDA", "エヌビディア", "NVIDIA", "US", "米国", "USD", "NASDAQ",
      "情報技術", "GPU・AIアクセラレータ", 1, 178.0, 4300000,
      "AI学習・推論用GPUとCUDAエコシステム。需要連鎖の起点にして最大の受益者",
      {"gpu_accel": 0.60, "hbm_memory": 0.12, "network_switch": 0.10},
      ["米国サンタクララ"], None, 0.03,
      q=0.94, g=0.92, v=0.86, lev=0.08, vol=0.48, mom=0.84, gov=0.68),

    C("AMD", "アドバンスト・マイクロ・デバイセズ", "AMD", "US", "米国", "USD", "NASDAQ",
      "情報技術", "CPU・GPU", 1, 168.0, 272000,
      "サーバCPUでシェア拡大、AIアクセラレータで二番手ポジションを確立中",
      {"gpu_accel": 0.42, "server_oem": 0.14, "adv_packaging": 0.10},
      ["米国サンタクララ"], None, 0.0,
      q=0.62, g=0.78, v=0.88, lev=0.10, vol=0.50, mom=0.62, gov=0.60),

    C("AVGO", "ブロードコム", "Broadcom", "US", "米国", "USD", "NASDAQ",
      "情報技術", "カスタムASIC・ネットワークチップ", 1, 335.0, 1560000,
      "ハイパースケーラ向けカスタムAI ASICとイーサネットスイッチチップの二枚看板",
      {"gpu_accel": 0.30, "network_switch": 0.28, "optical_device": 0.10},
      ["米国パロアルト"], None, 0.8,
      q=0.86, g=0.80, v=0.82, lev=0.52, vol=0.40, mom=0.82, gov=0.62),

    C("MU", "マイクロン・テクノロジー", "Micron", "US", "米国", "USD", "NASDAQ",
      "情報技術", "DRAM・HBM", 1, 185.0, 205000,
      "HBM3E/HBM4でAIメモリ需給の中核。シクリカルだが構造的な需要変化の渦中",
      {"hbm_memory": 0.52, "server_oem": 0.12, "semi_materials": 0.06},
      ["米国ボイシ", "日本広島（DRAM）"], None, 0.3,
      q=0.54, g=0.88, v=0.44, lev=0.30, vol=0.52, mom=0.88, gov=0.56),

    C("AMAT", "アプライド・マテリアルズ", "Applied Materials", "US", "米国", "USD", "NASDAQ",
      "情報技術", "半導体製造装置", 1, 215.0, 172000,
      "成膜・エッチングを中心とする総合装置。先端ロジックとHBM双方に露出",
      {"semi_equip": 0.48, "adv_packaging": 0.12, "hbm_memory": 0.10},
      ["米国サンタクララ"], None, 0.8,
      q=0.78, g=0.58, v=0.52, lev=0.28, vol=0.38, mom=0.62, gov=0.62),

    C("LRCX", "ラムリサーチ", "Lam Research", "US", "米国", "USD", "NASDAQ",
      "情報技術", "エッチング・成膜装置", 1, 105.0, 133000,
      "メモリ向けエッチングに強い。HBM積層とNAND高層化の直接受益",
      {"semi_equip": 0.46, "hbm_memory": 0.20},
      ["米国フリーモント"], None, 0.9,
      q=0.80, g=0.66, v=0.60, lev=0.26, vol=0.42, mom=0.72, gov=0.60),

    C("KLAC", "KLA", "KLA Corporation", "US", "米国", "USD", "NASDAQ",
      "情報技術", "検査・計測装置", 1, 1050.0, 138000,
      "プロセス制御・欠陥検査で圧倒的シェア。歩留まり改善需要の独占的受け皿",
      {"semi_equip": 0.50, "adv_packaging": 0.12},
      ["米国ミルピタス"], None, 0.6,
      q=0.88, g=0.62, v=0.64, lev=0.40, vol=0.38, mom=0.70, gov=0.64),

    C("ARM", "アーム・ホールディングス", "Arm Holdings", "US", "英国", "USD", "NASDAQ",
      "情報技術", "半導体IP", 1, 145.0, 152000,
      "CPU命令セットIPのライセンス。データセンターCPUへの浸透が次の成長軸",
      {"gpu_accel": 0.16, "server_oem": 0.18, "edge_ai": 0.20},
      ["英国ケンブリッジ"], None, 0.0,
      q=0.70, g=0.74, v=0.96, lev=0.06, vol=0.52, mom=0.48, gov=0.44),

    C("VRT", "バーティブ・ホールディングス", "Vertiv", "US", "米国", "USD", "NYSE",
      "資本財", "DC電源・液冷", 1, 155.0, 58000,
      "データセンターの電源・熱管理の専業。液冷とUPSでAI DCの必需インフラ",
      {"cooling": 0.38, "ups_pdu": 0.30, "dc_power": 0.18},
      ["米国オハイオ州コロンバス"], None, 0.1,
      q=0.66, g=0.86, v=0.80, lev=0.44, vol=0.52, mom=0.84, gov=0.52),

    C("ETN", "イートン", "Eaton", "US", "アイルランド", "USD", "NYSE",
      "資本財", "電力管理・配電", 1, 365.0, 143000,
      "配電盤・スイッチギア・UPS。DC電力インフラのバックログが長期化",
      {"ups_pdu": 0.32, "dc_power": 0.22, "grid_td": 0.18, "ev_supply": 0.08},
      ["アイルランド・ダブリン", "米国クリーブランド"], None, 1.0,
      q=0.78, g=0.68, v=0.72, lev=0.30, vol=0.32, mom=0.70, gov=0.64),

    C("PWR", "クアンタ・サービシズ", "Quanta Services", "US", "米国", "USD", "NYSE",
      "資本財", "送配電EPC", 1, 400.0, 59000,
      "送配電網の建設・保守の最大手。系統増強と再エネ接続の実行部隊",
      {"grid_td": 0.44, "renewables": 0.18, "epc_construction": 0.16},
      ["米国ヒューストン"], None, 0.1,
      q=0.64, g=0.76, v=0.78, lev=0.34, vol=0.40, mom=0.76, gov=0.56),

    C("GEV", "GEベルノバ", "GE Vernova", "US", "米国", "USD", "NYSE",
      "資本財", "発電設備・送電機器", 1, 560.0, 153000,
      "ガスタービン・送電機器・風力。電力不足に対する最短の供給側解",
      {"power_gen": 0.38, "grid_td": 0.26, "renewables": 0.14, "nuclear": 0.06},
      ["米国ケンブリッジ", "米国グリーンビル（タービン）"], None, 0.2,
      q=0.60, g=0.82, v=0.88, lev=0.18, vol=0.46, mom=0.80, gov=0.54),

    C("POWL", "パウエル・インダストリーズ", "Powell Industries", "US", "米国", "USD", "NASDAQ",
      "資本財", "配電盤・スイッチギア", 1, 280.0, 3400,
      "受変電設備の中堅。DC・LNG向けで受注残が急増した小型銘柄",
      {"ups_pdu": 0.30, "dc_power": 0.22, "grid_td": 0.22},
      ["米国ヒューストン"], None, 0.4,
      q=0.58, g=0.84, v=0.54, lev=0.06, vol=0.56, mom=0.72, gov=0.44),

    C("HUBB", "ハベル", "Hubbell", "US", "米国", "USD", "NYSE",
      "資本財", "変圧器・電力機器", 1, 420.0, 22000,
      "配電用変圧器で北米の主要供給者。リードタイム長期化＝価格決定力",
      {"transformer": 0.40, "grid_td": 0.26, "dc_power": 0.10},
      ["米国シェルトン"], None, 1.2,
      q=0.72, g=0.56, v=0.60, lev=0.34, vol=0.30, mom=0.58, gov=0.58),

    C("CEG", "コンステレーション・エナジー", "Constellation Energy", "US", "米国", "USD", "NASDAQ",
      "公益", "原子力発電", 1, 320.0, 100000,
      "米国最大の原子力発電事業者。DC向け長期電力契約が価値の源泉",
      {"nuclear": 0.44, "power_gen": 0.26, "dc_power": 0.16},
      ["米国ボルチモア", "ペンシルベニア州（原子力）"], None, 0.5,
      q=0.60, g=0.72, v=0.82, lev=0.46, vol=0.44, mom=0.74, gov=0.52),

    C("VST", "ビストラ", "Vistra", "US", "米国", "USD", "NYSE",
      "公益", "独立系発電", 1, 175.0, 59000,
      "テキサス中心の独立系発電。電力価格上昇と原子力資産の再評価",
      {"power_gen": 0.42, "nuclear": 0.20, "dc_power": 0.14},
      ["米国アービング"], None, 0.6,
      q=0.54, g=0.76, v=0.66, lev=0.66, vol=0.50, mom=0.78, gov=0.44),

    C("NEE", "ネクステラ・エナジー", "NextEra Energy", "US", "米国", "USD", "NYSE",
      "公益", "電力・再生可能エネルギー", 1, 78.0, 160000,
      "規制電力（FPL）と世界最大級の再エネ開発。金利感応度が高い",
      {"renewables": 0.38, "power_gen": 0.22, "grid_td": 0.14},
      ["米国フロリダ州ジュノビーチ"], None, 2.9,
      q=0.60, g=0.46, v=0.56, lev=0.72, vol=0.30, mom=0.42, gov=0.56),

    C("ANET", "アリスタネットワークス", "Arista Networks", "US", "米国", "USD", "NYSE",
      "情報技術", "データセンタースイッチ", 1, 145.0, 182000,
      "高速イーサネットスイッチ。AIクラスタのバックエンド網でシェア拡大",
      {"network_switch": 0.48, "optical_device": 0.14, "dc_build": 0.08},
      ["米国サンタクララ"], None, 0.0,
      q=0.86, g=0.74, v=0.80, lev=0.02, vol=0.44, mom=0.72, gov=0.60),

    C("CIEN", "シエナ", "Ciena", "US", "米国", "USD", "NYSE",
      "情報技術", "光伝送システム", 1, 115.0, 16500,
      "コヒーレント光伝送。DC間接続（DCI）の帯域需要が業績を牽引",
      {"optical_device": 0.42, "optical_fiber": 0.18, "network_switch": 0.12},
      ["米国メリーランド州ハノーバー"], None, 0.0,
      q=0.48, g=0.70, v=0.72, lev=0.36, vol=0.48, mom=0.74, gov=0.50),

    C("COHR", "コヒレント", "Coherent", "US", "米国", "USD", "NYSE",
      "情報技術", "光デバイス・トランシーバ", 1, 118.0, 18500,
      "800G/1.6T光トランシーバとレーザ。AI DCの光配線需要に直結",
      {"optical_device": 0.46, "optical_fiber": 0.14},
      ["米国ペンシルベニア州サクソンバーグ"], None, 0.0,
      q=0.40, g=0.80, v=0.70, lev=0.56, vol=0.58, mom=0.82, gov=0.42),

    C("DLR", "デジタル・リアルティ", "Digital Realty", "US", "米国", "USD", "NYSE",
      "不動産", "データセンターREIT", 1, 165.0, 56000,
      "グローバルDC REIT。稼働率と賃料改定が価値ドライバ、金利に敏感",
      {"dc_build": 0.44, "dc_power": 0.12},
      ["米国オースティン", "北バージニア（DC集積）"], None, 3.0,
      q=0.44, g=0.44, v=0.66, lev=0.74, vol=0.32, mom=0.38, gov=0.50),

    C("EQIX", "エクイニクス", "Equinix", "US", "米国", "USD", "NASDAQ",
      "不動産", "データセンターREIT", 1, 780.0, 76000,
      "相互接続に強いDC REIT。ネットワーク集積という参入障壁を持つ",
      {"dc_build": 0.40, "network_switch": 0.10, "dc_power": 0.10},
      ["米国レッドウッドシティ"], None, 2.3,
      q=0.60, g=0.48, v=0.72, lev=0.62, vol=0.30, mom=0.34, gov=0.54),

    C("MSFT", "マイクロソフト", "Microsoft", "US", "米国", "USD", "NASDAQ",
      "情報技術", "クラウド・ソフトウェア", 1, 505.0, 3750000,
      "AzureとCopilot。需要連鎖の最上流でDC投資を決定する側",
      {"genai_capex": 0.40, "dc_build": 0.16, "software_ai": 0.24},
      ["米国レドモンド"], None, 0.7,
      q=0.92, g=0.62, v=0.76, lev=0.20, vol=0.26, mom=0.52, gov=0.72),

    C("GOOGL", "アルファベット", "Alphabet", "US", "米国", "USD", "NASDAQ",
      "コミュニケーション", "検索・クラウド", 1, 255.0, 3080000,
      "検索・YouTube・GCPとTPU内製。AI投資の主体かつ最大の実装者",
      {"genai_capex": 0.38, "software_ai": 0.22, "dc_build": 0.14},
      ["米国マウンテンビュー"], None, 0.4,
      q=0.90, g=0.60, v=0.58, lev=0.14, vol=0.30, mom=0.68, gov=0.46),

    C("AMZN", "アマゾン・ドット・コム", "Amazon", "US", "米国", "USD", "NASDAQ",
      "一般消費財", "EC・クラウド", 1, 230.0, 2450000,
      "AWSと小売。Trainium内製とDC投資の規模で連鎖の起点を担う",
      {"genai_capex": 0.34, "dc_build": 0.16, "consumer_us": 0.16},
      ["米国シアトル"], None, 0.0,
      q=0.74, g=0.66, v=0.74, lev=0.34, vol=0.32, mom=0.50, gov=0.52),

    C("META", "メタ・プラットフォームズ", "Meta Platforms", "US", "米国", "USD", "NASDAQ",
      "コミュニケーション", "SNS・AI基盤", 1, 690.0, 1730000,
      "広告収益をAI基盤に再投資。DC建設と電力調達の巨大な需要主体",
      {"genai_capex": 0.40, "dc_build": 0.18, "software_ai": 0.14},
      ["米国メンローパーク"], None, 0.3,
      q=0.84, g=0.58, v=0.54, lev=0.22, vol=0.38, mom=0.46, gov=0.34),

    C("ORCL", "オラクル", "Oracle", "US", "米国", "USD", "NYSE",
      "情報技術", "クラウド・データベース", 1, 245.0, 690000,
      "OCIのAI学習向け大型契約。負債を伴う積極投資でリスクも大きい",
      {"genai_capex": 0.30, "dc_build": 0.22, "software_ai": 0.16},
      ["米国オースティン"], None, 0.9,
      q=0.52, g=0.72, v=0.90, lev=0.84, vol=0.46, mom=0.66, gov=0.40),

    C("PLTR", "パランティア・テクノロジーズ", "Palantir", "US", "米国", "USD", "NASDAQ",
      "情報技術", "データ分析ソフトウェア", 1, 165.0, 390000,
      "政府・商用向けAI実装プラットフォーム。極端に高いバリュエーション",
      {"software_ai": 0.44, "defense_electronics": 0.18},
      ["米国デンバー"], None, 0.0,
      q=0.70, g=0.88, v=0.99, lev=0.02, vol=0.66, mom=0.86, gov=0.40),

    C("LMT", "ロッキード・マーティン", "Lockheed Martin", "US", "米国", "USD", "NYSE",
      "資本財", "防衛", 1, 465.0, 108000,
      "F-35とミサイル防衛。各国の防衛費増加が長期のバックログを支える",
      {"defense_prime": 0.48, "defense_electronics": 0.16},
      ["米国ベセスダ"], None, 2.7,
      q=0.62, g=0.36, v=0.42, lev=0.72, vol=0.26, mom=0.44, gov=0.54),

    C("CAT", "キャタピラー", "Caterpillar", "US", "米国", "USD", "NYSE",
      "資本財", "建設機械・発電機", 1, 430.0, 205000,
      "建機に加えDC向け予備発電（ディーゼル・ガス）の供給者",
      {"epc_construction": 0.26, "power_gen": 0.18, "mining_equipment": 0.18},
      ["米国アービング"], None, 1.3,
      q=0.72, g=0.44, v=0.58, lev=0.58, vol=0.30, mom=0.62, gov=0.56),

    C("LLY", "イーライリリー", "Eli Lilly", "US", "米国", "USD", "NYSE",
      "ヘルスケア", "医薬品", 1, 790.0, 750000,
      "GLP-1（肥満・糖尿病）で圧倒的な成長。生産能力増強が制約かつ投資機会",
      {"pharma": 0.50, "aging_health": 0.18},
      ["米国インディアナポリス"], None, 0.7,
      q=0.82, g=0.84, v=0.92, lev=0.44, vol=0.34, mom=0.56, gov=0.60),

    C("UNH", "ユナイテッドヘルス", "UnitedHealth", "US", "米国", "USD", "NYSE",
      "ヘルスケア", "医療保険・医療サービス", 1, 320.0, 290000,
      "医療保険とOptum。規制・医療費率の逆風で評価が大きく低下した局面",
      {"aging_health": 0.42, "pharma": 0.10},
      ["米国ミネトンカ"], None, 2.6,
      q=0.58, g=0.34, v=0.24, lev=0.52, vol=0.42, mom=0.18, gov=0.36),

    C("COST", "コストコ・ホールセール", "Costco", "US", "米国", "USD", "NASDAQ",
      "生活必需品", "会員制小売", 1, 920.0, 408000,
      "会員料収入モデルの小売。極めて安定だが株価評価は歴史的高水準",
      {"consumer_us": 0.44},
      ["米国イサクア"], None, 0.5,
      q=0.84, g=0.42, v=0.94, lev=0.24, vol=0.22, mom=0.40, gov=0.62),

    C("BRK.B", "バークシャー・ハサウェイ", "Berkshire Hathaway", "US", "米国", "USD", "NYSE",
      "金融", "コングロマリット", 1, 495.0, 1070000,
      "保険・鉄道・電力・株式投資の複合体。巨額の現金と規律ある資本配分",
      {"rates_financials": 0.24, "power_gen": 0.10, "consumer_us": 0.12},
      ["米国オマハ"], None, 0.0,
      q=0.80, g=0.34, v=0.40, lev=0.30, vol=0.20, mom=0.48, gov=0.66),
]


# ---------------------------------------------------------------------------
# 欧州・アジア
# ---------------------------------------------------------------------------
EU_ASIA: List[Company] = [
    C("ASML.AS", "ASMLホールディング", "ASML", "EU", "オランダ", "EUR", "Euronext",
      "情報技術", "EUV露光装置", 1, 720.0, 290000,
      "EUV露光装置の独占供給者。先端半導体の物理的な律速点",
      {"semi_equip": 0.56, "adv_packaging": 0.08},
      ["オランダ・フェルトホーフェン"], None, 0.9,
      q=0.90, g=0.70, v=0.78, lev=0.20, vol=0.40, mom=0.72, gov=0.66),

    C("SIE.DE", "シーメンス", "Siemens", "EU", "ドイツ", "EUR", "XETRA",
      "資本財", "産業自動化・電力", 1, 235.0, 205000,
      "産業オートメーションとスマートインフラ。DC電気設備でも存在感",
      {"factory_auto": 0.28, "grid_td": 0.16, "dc_power": 0.12, "software_ai": 0.08},
      ["ドイツ・ミュンヘン", "ドイツ・エアランゲン"], None, 2.4,
      q=0.66, g=0.44, v=0.46, lev=0.44, vol=0.26, mom=0.58, gov=0.62),

    C("SU.PA", "シュナイダーエレクトリック", "Schneider Electric", "EU", "フランス", "EUR", "Euronext",
      "資本財", "電力管理・DC電源", 1, 230.0, 145000,
      "DC向け電源管理と配電。APCブランドとEcoStruxureで電力効率を握る",
      {"ups_pdu": 0.34, "dc_power": 0.24, "grid_td": 0.14, "cooling": 0.10},
      ["フランス・リュエイユマルメゾン"], None, 1.5,
      q=0.76, g=0.62, v=0.68, lev=0.32, vol=0.28, mom=0.62, gov=0.62),

    C("ABBN.SW", "ABB", "ABB", "EU", "スイス", "CHF", "SIX",
      "資本財", "電化・ロボット", 1, 54.0, 100000,
      "電化製品（スイッチギア）とロボット。DC電力と省人化の両輪",
      {"ups_pdu": 0.24, "grid_td": 0.20, "robotics": 0.18, "factory_auto": 0.14},
      ["スイス・チューリッヒ"], None, 2.0,
      q=0.74, g=0.56, v=0.62, lev=0.28, vol=0.26, mom=0.64, gov=0.60),

    C("RHM.DE", "ラインメタル", "Rheinmetall", "EU", "ドイツ", "EUR", "XETRA",
      "資本財", "防衛", 1, 1650.0, 74000,
      "欧州の弾薬・装甲車両。NATOの防衛費拡大を最も直接的に受ける",
      {"defense_prime": 0.52, "defense_electronics": 0.12},
      ["ドイツ・デュッセルドルフ"], None, 0.7,
      q=0.58, g=0.90, v=0.90, lev=0.40, vol=0.52, mom=0.88, gov=0.46),

    C("SAP.DE", "SAP", "SAP", "EU", "ドイツ", "EUR", "XETRA",
      "情報技術", "業務ソフトウェア", 1, 235.0, 285000,
      "ERPのクラウド移行が進行。欧州最大のソフトウェア企業",
      {"software_ai": 0.34, "factory_auto": 0.08},
      ["ドイツ・ヴァルドルフ"], None, 1.0,
      q=0.78, g=0.58, v=0.80, lev=0.18, vol=0.28, mom=0.44, gov=0.60),

    C("NOVN.SW", "ノバルティス", "Novartis", "EU", "スイス", "CHF", "SIX",
      "ヘルスケア", "医薬品", 1, 105.0, 215000,
      "特許切れを新薬で埋める局面。安定したFCFと株主還元",
      {"pharma": 0.44, "aging_health": 0.14},
      ["スイス・バーゼル"], None, 3.4,
      q=0.72, g=0.36, v=0.36, lev=0.34, vol=0.22, mom=0.50, gov=0.60),

    C("MC.PA", "LVMH", "LVMH", "EU", "フランス", "EUR", "Euronext",
      "一般消費財", "高級ブランド", 1, 590.0, 300000,
      "高級品の圧倒的ブランド群。中国需要の循環に左右される",
      {"consumer_lux": 0.48, "consumer_asia": 0.16},
      ["フランス・パリ"], None, 2.3,
      q=0.78, g=0.30, v=0.56, lev=0.36, vol=0.30, mom=0.30, gov=0.48),

    C("NESN.SW", "ネスレ", "Nestle", "EU", "スイス", "CHF", "SIX",
      "生活必需品", "食品", 1, 80.0, 215000,
      "世界最大の食品企業。ディフェンシブだが成長は鈍化",
      {"consumer_staples": 0.46},
      ["スイス・ヴェベー"], None, 3.8,
      q=0.68, g=0.20, v=0.40, lev=0.56, vol=0.18, mom=0.28, gov=0.54),

    C("TTE.PA", "トタルエナジーズ", "TotalEnergies", "EU", "フランス", "EUR", "Euronext",
      "エネルギー", "石油・ガス・電力", 1, 56.0, 128000,
      "LNGと再エネ発電への転換。エネルギー価格へのヘッジ機能",
      {"commodities": 0.34, "renewables": 0.16, "power_gen": 0.10},
      ["フランス・クールブボア"], None, 5.6,
      q=0.52, g=0.22, v=0.20, lev=0.48, vol=0.28, mom=0.40, gov=0.44),

    C("TSM", "台湾積体電路製造", "TSMC", "ASIA", "台湾", "USD", "NYSE(ADR)",
      "情報技術", "半導体ファウンドリ", 1, 285.0, 1470000,
      "先端ロジックの実質的独占ファウンドリ。CoWoS能力がAI供給の律速",
      {"semi_foundry": 0.50, "adv_packaging": 0.22, "gpu_accel": 0.12},
      ["台湾・新竹", "日本・熊本県菊陽町", "米国アリゾナ"], None, 1.0,
      q=0.92, g=0.82, v=0.60, lev=0.16, vol=0.38, mom=0.80, gov=0.64),

    C("005930.KS", "サムスン電子", "Samsung Electronics", "ASIA", "韓国", "KRW", "KRX",
      "情報技術", "メモリ・ファウンドリ・端末", 10, 92000.0, 470000,
      "DRAM/NANDとファウンドリ、端末の垂直統合。HBMで巻き返しを図る局面",
      {"hbm_memory": 0.30, "semi_foundry": 0.18, "server_oem": 0.10, "edge_ai": 0.10},
      ["韓国・平沢", "韓国・華城"], None, 1.6,
      q=0.60, g=0.62, v=0.34, lev=0.20, vol=0.36, mom=0.70, gov=0.38),

    C("000660.KS", "SKハイニックス", "SK Hynix", "ASIA", "韓国", "KRW", "KRX",
      "情報技術", "DRAM・HBM", 10, 420000.0, 220000,
      "HBMで先行しNVIDIAの主力サプライヤ。AIメモリ需要の最大受益",
      {"hbm_memory": 0.58, "server_oem": 0.08},
      ["韓国・利川", "韓国・清州"], None, 0.9,
      q=0.64, g=0.92, v=0.42, lev=0.42, vol=0.50, mom=0.90, gov=0.42),

    C("2317.TW", "鴻海精密工業", "Hon Hai (Foxconn)", "ASIA", "台湾", "TWD", "TWSE",
      "情報技術", "AIサーバEMS", 1000, 215.0, 96000,
      "AIサーバの受託製造で最大手。低マージンだが数量の伸びが極めて大きい",
      {"server_oem": 0.50, "cooling": 0.10, "dc_build": 0.08},
      ["台湾・新北", "メキシコ（AIサーバ工場）"], None, 3.4,
      q=0.44, g=0.72, v=0.28, lev=0.50, vol=0.40, mom=0.76, gov=0.40),

    C("2454.TW", "メディアテック", "MediaTek", "ASIA", "台湾", "TWD", "TWSE",
      "情報技術", "SoC・エッジAI", 1000, 1450.0, 74000,
      "スマホSoCとカスタムASIC。エッジAIとDC向けASICの二正面",
      {"edge_ai": 0.34, "gpu_accel": 0.14, "semi_foundry": 0.06},
      ["台湾・新竹"], None, 3.0,
      q=0.66, g=0.60, v=0.52, lev=0.14, vol=0.40, mom=0.58, gov=0.50),

    C("INFY", "インフォシス", "Infosys", "ASIA", "インド", "USD", "NYSE(ADR)",
      "情報技術", "ITサービス", 1, 19.5, 81000,
      "インドITサービス大手。生成AIによる案件単価下落と効率化の両面リスク",
      {"software_ai": 0.22, "consumer_asia": 0.08},
      ["インド・ベンガルール"], None, 2.6,
      q=0.72, g=0.28, v=0.48, lev=0.10, vol=0.28, mom=0.24, gov=0.58),
]


UNIVERSE: List[Company] = JP + US + EU_ASIA


def get_universe(regions: Optional[List[str]] = None) -> List[Company]:
    if not regions:
        return list(UNIVERSE)
    return [c for c in UNIVERSE if c.region in regions]


def by_ticker(ticker: str) -> Optional[Company]:
    for c in UNIVERSE:
        if c.ticker == ticker:
            return c
    return None


if __name__ == "__main__":
    from collections import Counter
    print("total:", len(UNIVERSE))
    print("region:", Counter(c.region for c in UNIVERSE))
    print("sector:", Counter(c.sector for c in UNIVERSE))
