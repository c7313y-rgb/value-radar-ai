#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
単一HTMLファイル版のビルド

CSS・JS・データをすべて1枚のHTMLに埋め込む。
サーバも依存パッケージも不要になるので、配布・共有・オフライン閲覧に使える。

    python3 scripts/build_single_file.py                 → dist/value-radar-ai.html
    python3 scripts/build_single_file.py --artifact      → dist/artifact.html
        （<!doctype>/<html>/<head>/<body> を持たない断片。
          外側のスケルトンを付与するホストへ貼る用）
"""
from __future__ import annotations
import argparse
import base64
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULES = ["util.js", "charts.js", "views.js", "app.js"]
VIEW_EXPORTS = ["setDB", "viewToday", "viewDiscover", "viewTrends",
                "viewThemeGuide", "viewStock", "viewPortfolio"]

IMPORT_RE = re.compile(r"^\s*import\s[^;]*?;\s*$", re.M | re.S)


def strip_module_syntax(src: str) -> str:
    src = IMPORT_RE.sub("", src)
    src = re.sub(r"^export\s+(?=(const|let|var|function|class|async))", "", src, flags=re.M)
    return src



ASSET_RE = re.compile(r"web/assets/[\w\-.]+")


def inline_assets(text: str) -> str:
    """web/assets/ への参照を data URI に置き換える（単一ファイル配布用）。"""
    def repl(m: re.Match) -> str:
        ap = ROOT / m.group(0)
        if not ap.exists():
            return m.group(0)
        mime = "image/jpeg" if ap.suffix.lower() in (".jpg", ".jpeg") else "image/png"
        return "data:" + mime + ";base64," + base64.b64encode(ap.read_bytes()).decode()
    return ASSET_RE.sub(repl, text)


def build(artifact: bool = False) -> Path:
    css = (ROOT / "web" / "style.css").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    data = json.loads((ROOT / "data" / "latest.json").read_text(encoding="utf-8"))
    series_path = ROOT / "data" / "series.json"
    series = json.loads(series_path.read_text(encoding="utf-8")) if series_path.exists() else {}

    parts = []
    for m in MODULES:
        src = strip_module_syntax((ROOT / "web" / "js" / m).read_text(encoding="utf-8"))
        if m == "app.js":
            # ESM の名前空間インポートを平坦な参照に置き換える
            src = "const V = { " + ", ".join(VIEW_EXPORTS) + " };\n" + src
            src = src.replace("new URL('../../data/latest.json', import.meta.url)", "''")
            src = src.replace("new URL('../../data/series.json', import.meta.url)", "''")
        parts.append(f"/* ---- {m} ---- */\n{src}")
    js = inline_assets("\n".join(parts))

    # index.html の <body> 内側だけを取り出す
    body = html.split("<body>", 1)[1].split("</body>", 1)[0]
    body = re.sub(r'<script type="module"[^>]*></script>', "", body)
    body = re.sub(r'<link rel="(preconnect|stylesheet)"[^>]*>', "", body)
    body = inline_assets(body)

    # アプリ本体が起動時に「デモデータ」バナーを出すので、ここでは重ねない。

    inline = (
        "<script>window.__VR_INLINE_DATA__="
        + json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        + ";window.__VR_INLINE_SERIES__="
        + json.dumps(series, ensure_ascii=False, separators=(",", ":"))
        + ";</script>"
    )

    font_link = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2'
        '?family=IBM+Plex+Mono:wght@400;500;600&display=swap">'
    )

    title = "VALUE RADAR AI"
    head_meta = (
        '<meta name="description" content="世界の企業価値と未来需要を毎日再評価するAI投資委員会（デモ）">'
    )

    out_dir = ROOT / "dist"
    out_dir.mkdir(exist_ok=True)

    if artifact:
        doc = (f"<title>{title}</title>\n{font_link}\n<style>\n{css}\n</style>\n"
               f"{body}\n{inline}\n<script>\n{js}\n</script>\n")
        out = out_dir / "artifact.html"
    else:
        doc = ("<!doctype html>\n<html lang=\"ja\">\n<head>\n"
               "<meta charset=\"utf-8\">\n"
               "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
               f"<title>{title}</title>\n{head_meta}\n{font_link}\n<style>\n{css}\n</style>\n"
               f"</head>\n<body>\n{body}\n{inline}\n<script>\n{js}\n</script>\n</body>\n</html>\n")
        out = out_dir / "value-radar-ai.html"

    out.write_text(doc, encoding="utf-8")
    print(f"{out}  ({out.stat().st_size / 1024:.0f} KB)")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", action="store_true")
    build(ap.parse_args().artifact)
