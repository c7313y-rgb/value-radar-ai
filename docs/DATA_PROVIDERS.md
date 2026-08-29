# データ層の差し替え

**評価エンジンとデータAPIは完全に分離されています。**
エンジンが知っているのは次の2つのデータ契約だけです（`engine/providers/base.py`）。

```python
class MarketDataProvider(Protocol):
    name: str
    is_synthetic: bool
    def fundamentals(self, tickers: list[str], as_of: str) -> dict[str, Fundamentals]: ...

class EvidenceProvider(Protocol):
    name: str
    is_synthetic: bool
    def evidence(self, node_ids: list[str], as_of: str) -> dict[str, list[EvidenceItem]]: ...
```

この形さえ返せば、データソースは何でも構いません。

## 1. 段階的な移行パス

| 段階 | プロバイダ | 必要なもの | 用途 |
|---|---|---|---|
| 0 | `demo` | なし（標準ライブラリのみ） | 体験デモ・CI・オフライン検証 |
| 1 | `yfinance` | `pip install -r requirements-live.txt` | 個人検証・プロトタイプ |
| 2 | 公的一次情報 | EDINET / SEC EDGAR / FRED / World Bank | 財務の一次確認、無償で堅い |
| 3 | `premium` | ベンダ契約 | 運用フェーズ。予想値・改定履歴・詳細セグメント |

## 2. 切り替え方

```bash
python3 -m engine.pipeline                                    # demo
VR_PROVIDER=yfinance python3 -m engine.pipeline               # 無料実データ
VR_PROVIDER=premium VR_PREMIUM_VENDOR=lseg \
  VR_PREMIUM_KEY=xxx VR_PREMIUM_ENDPOINT=https://... \
  python3 -m engine.pipeline                                  # 有料データ
```

`--fallback-demo` を付けると取得失敗時にデモへ退避します。
**本番運用では付けないでください**（黙って合成値に落ちるのを防ぐため）。

## 3. 有料層の実装手順

`engine/providers/premium_provider.py` の `_fetch()` を実装するだけです。
エンジン側の変更は不要です。

```python
class PremiumProvider:
    def _fetch(self, tickers, as_of):
        rows = your_vendor_client.get(tickers, fields=FIELD_MAP[self.vendor].values())
        out = {}
        for t, r in rows.items():
            out[t] = Fundamentals(
                ticker=t, as_of=as_of,
                price=r["PX_LAST"],
                roe=r[FIELD_MAP[self.vendor]["roe"]],
                ...
                data_coverage=filled / total,     # 埋まった割合を必ず入れる
                source=self.vendor, is_synthetic=False,
            )
        return out
```

### フィールド対応表（同ファイルに実装済み）

| エンジン側 | Bloomberg | LSEG (Refinitiv) | FactSet | S&P Capital IQ |
|---|---|---|---|---|
| `roe` | `RETURN_COM_EQY` | `TR.ROEPercent` | `FF_ROE` | `IQ_RETURN_EQUITY` |
| `roic` | `RETURN_ON_INV_CAPITAL` | `TR.ROICPercent` | `FF_ROIC` | `IQ_RETURN_CAPITAL` |
| `op_margin` | `OPER_MARGIN` | `TR.OperatingMargPct` | `FF_OPER_MGN` | `IQ_EBIT_MARGIN` |
| `per` | `PE_RATIO` | `TR.PE` | `FF_PE` | `IQ_PE_EXCL` |
| `forward_per` | `BEST_PE_RATIO` | `TR.FwdPE` | `FE_PE_MEAN` | `IQ_PE_EXCL_FWD` |
| `pbr` | `PX_TO_BOOK_RATIO` | `TR.PriceToBVPerShare` | `FF_PBK` | `IQ_PBV` |
| `ev_ebitda` | `CURRENT_EV_TO_T12M_EBITDA` | `TR.EVToEBITDA` | `FF_ENTRPR_VAL_EBITDA_OPER` | `IQ_TEV_EBITDA` |
| `fcf_yield` | `FREE_CASH_FLOW_YIELD` | `TR.FCFYield` | `FF_FREE_CF_YLD` | `IQ_FCF_YIELD` |
| `eps_revision_3m` | `BEST_EPS_3MO_CHG` | `TR.EPSMean(Period=FY1,WP=90D)` | `FE_EPS_REV_3M` | `IQ_EST_EPS_REV_3M` |
| `net_debt_ebitda` | `NET_DEBT_TO_EBITDA` | `TR.NetDebtToEBITDA` | `FF_NET_DEBT_EBITDA_OPER` | `IQ_NET_DEBT_EBITDA` |

> フィールド名はベンダのバージョンにより変わります。導入時に必ず自社の契約で確認してください。

### 有料層で初めて手に入るもの

- **アナリスト予想と改定履歴** … `eps_revision_3m` が本物になり、Growth レイヤーの精度が跳ね上がる
- **セグメント別売上** … 需要ノードへの露出度（現在は手動設定）を実データで自動推定できる
- **ポイントインタイム財務** … バックテストで先読みバイアスを排除できる
- **MSCI ACWI の構成銘柄・ウェイト** … 母集団を思想の模倣ではなく実データで構築できる

## 4. 定性データ（Governance レイヤー）の差し替え

現在 `moat_score` / `governance_score` / `capital_allocation` / `culture_engagement` /
`ir_dialogue` はデモ合成値です。実運用での置き換え候補：

| 項目 | 情報源 |
|---|---|
| moat | Morningstar Economic Moat Rating |
| ガバナンス | ISS QualityScore、コーポレートガバナンス報告書、独立取締役比率 |
| 資本配分 | 自社株買い・配当の履歴、ROIC の推移、M&A の減損実績 |
| 企業文化 | 従業員クチコミ（OpenWork / Glassdoor）、離職率、エンゲージメント調査 |
| IR対話 | 決算説明会の質疑応答の量と具体性、英文開示の有無、統合報告書 |

**LLM を使う場合の設計上の注意：** 数値の生成に LLM を使ってはいけません。
一次情報（有価証券報告書・統合報告書）から**抽出**し、抽出元を必ず併記する形にしてください。

## 5. 需要エビデンスの差し替え

`EvidenceProvider` を実装して `registry.get_evidence_provider()` に登録します。
`EvidenceItem` には `source` と `source_url` を必ず入れてください。
**出典のないエビデンスは、それ自体がリスクです。**

## 6. 為替

`engine/output/fx.py` の `get_rates()` を実装するだけです（1通貨あたりの円）。
最低投資額と予算配分は必ず円換算で出しています。
