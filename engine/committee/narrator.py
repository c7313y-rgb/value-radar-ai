# -*- coding: utf-8 -*-
"""
「なぜ今日この銘柄なのか」を3行で説明する

既定はテンプレート生成。理由は3つ:
  - 数値から機械的に導けるので、幻覚（hallucination）が構造的に起きない
  - ネットワークもAPIキーも要らない
  - 毎日の差分が読みやすい

VR_LLM=anthropic / openai と APIキーを設定すると、同じ「事実の束」を
LLMに渡して自然な日本語に整形させる。事実そのものはエンジンが決めており、
LLMは表現だけを担当する（＝数値の捏造が起きない設計）。
"""

from __future__ import annotations
import json
import os
from typing import Dict, List, Optional


def build_facts(row: dict) -> Dict[str, object]:
    """LLMにもテンプレートにも同じものを渡す、事実の束。"""
    td = row.get("trend_detail") or []
    top = td[0] if td else {}
    return {
        "name": row["name"],
        "ticker": row["ticker"],
        "top_node": top.get("label", ""),
        "top_chain": row.get("top_chain", ""),
        "node_pressure": top.get("pressure", 0),
        "unpriced_gap": top.get("unpriced_gap", 0),
        "rev_cagr3": row["f"]["rev_cagr3"],
        "eps_cagr3": row["f"]["eps_cagr3"],
        "margin_trend": row["f"]["margin_trend"],
        "per": row["f"]["per"],
        "peer_median_per": row["peer_median_per"],
        "fcf_yield": row["f"]["fcf_yield"],
        "upside_pct": row["upside_pct"],
        "risk_top": (row["risk_items"][0]["name"] if row["risk_items"] else ""),
        "company_grade": row["company_grade"],
        "price_grade": row["price_grade"],
    }


def _pick_node(td):
    """説明に使うノードは「露出度 × 未織り込みギャップ」で選ぶ。
    最大露出が上流のドライバー（生成AI設備投資など）だと説明が平凡になるため。"""
    scored = sorted(td, key=lambda t: -(t["exposure"] * (1.0 + max(0.0, t["unpriced_gap"]) / 25.0)))
    return scored[0]


def template_reason(row: dict) -> List[str]:
    f = row["f"]
    td = row.get("trend_detail") or []
    lines: List[str] = []

    # 1行目：需要側の事実（人気ではなく実需）
    if td:
        t = _pick_node(td)
        chain = row.get("top_chain") or ""
        if chain and " → " in chain:
            head = f"{chain} という需要連鎖の下流に位置する。"
        else:
            head = f"需要テーマ「{t['label']}」の当事者。"
        gap = f"、未織り込みギャップ {t['unpriced_gap']:+.0f}" if t["unpriced_gap"] else ""
        lines.append(f"{head}「{t['label']}」の需要圧力は {t['pressure']:.0f}／100{gap}。")
    else:
        lines.append("特定の需要テーマへの接続は弱く、評価は企業固有の要因が中心。")

    # 2行目：企業側の事実
    seg = []
    if f["rev_cagr3"]:
        seg.append(f"売上3年CAGR {f['rev_cagr3']:+.0f}%")
    if f["eps_cagr3"]:
        seg.append(f"EPS {f['eps_cagr3']:+.0f}%")
    if f["roe"]:
        seg.append(f"ROE {f['roe']:.0f}%")
    if f["margin_trend"]:
        seg.append(f"営業利益率トレンド {f['margin_trend']:+.1f}pt")
    lines.append("、".join(seg) + "。" if seg else "財務指標の取得が限定的。")

    # 3行目：価格の相対評価（＝良い会社と良い株価を分ける行）
    pm = row["peer_median_per"]
    rel = "割安" if (f["per"] and pm and f["per"] < pm) else "割高"
    lines.append(f"同業ピア中央値PER {pm:.0f}倍に対し {f['per']:.0f}倍で相対的に{rel}、"
                 f"FCF利回り {f['fcf_yield']:.1f}%。適正価値に対する上値余地は {row['upside_pct']:+.0f}%"
                 f"（企業評価 {row['company_grade']}／価格評価 {row['price_grade']}）。")
    return lines


# ---------------------------------------------------------------------------
# LLM フック（任意）
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "あなたは機関投資家向けの投資委員会書記です。与えられた事実のみを使い、"
    "日本語で3行の要約を書いてください。新しい数値を作ってはいけません。"
    "断定的な売買推奨は避け、事実と相対評価を述べてください。1行は60字以内。"
)


def llm_reason(row: dict, timeout: float = 20.0) -> Optional[List[str]]:
    vendor = os.getenv("VR_LLM", "").lower()
    if vendor not in ("anthropic", "openai"):
        return None
    facts = build_facts(row)
    try:
        import urllib.request
        if vendor == "anthropic":
            key = os.getenv("ANTHROPIC_API_KEY", "")
            if not key:
                return None
            body = json.dumps({
                "model": os.getenv("VR_LLM_MODEL", "claude-sonnet-4-5"),
                "max_tokens": 400,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": json.dumps(facts, ensure_ascii=False)}],
            }).encode()
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages", data=body,
                headers={"content-type": "application/json", "x-api-key": key,
                         "anthropic-version": "2023-06-01"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read())
            text = "".join(b.get("text", "") for b in data.get("content", []))
        else:
            key = os.getenv("OPENAI_API_KEY", "")
            if not key:
                return None
            body = json.dumps({
                "model": os.getenv("VR_LLM_MODEL", "gpt-4o-mini"),
                "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                             {"role": "user", "content": json.dumps(facts, ensure_ascii=False)}],
            }).encode()
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions", data=body,
                headers={"content-type": "application/json", "authorization": f"Bearer {key}"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read())
            text = data["choices"][0]["message"]["content"]
        lines = [l.strip(" ・-　") for l in text.splitlines() if l.strip()]
        return lines[:3] if lines else None
    except Exception:
        return None


def reason(row: dict) -> List[str]:
    return llm_reason(row) or template_reason(row)
