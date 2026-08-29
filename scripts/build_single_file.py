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
    js = "\n".join(parts)

    # index.html の <body> 内側だけを取り出す
    body = html.split("<body>", 1)[1].split("</body>", 1)[0]
    body = re.sub(r'<script type="module"[^>]*></script>', "", body)
    body = body.replace('<link rel="stylesheet" href="web/style.css">', "")

    # アプリ本体が起動時に「デモデータ」バナーを出すので、ここでは重ねない。

    inline = (
        "<script>window.__VR_INLINE_DATA__="
        + json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        + ";window.__VR_INLINE_SERIES__="
        + json.dumps(series, ensure_ascii=False, separators=(",", ":"))
        + ";</script>"
    )

    title = "VALUE RADAR AI"
    head_meta = (
        '<meta name="description" content="世界の企業価値と未来需要を毎日再評価するAI投資委員会（デモ）">'
    )

    out_dir = ROOT / "dist"
    out_dir.mkdir(exist_ok=True)

    if artifact:
        doc = (f"<title>{title}</title>\n<style>\n{css}\n</style>\n"
               f"{body}\n{inline}\n<script>\n{js}\n</script>\n")
        out = out_dir / "artifact.html"
    else:
        doc = ("<!doctype html>\n<html lang=\"ja\" data-theme=\"dark\">\n<head>\n"
               "<meta charset=\"utf-8\">\n"
               "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
               f"<title>{title}</title>\n{head_meta}\n<style>\n{css}\n</style>\n"
               f"</head>\n<body>\n{body}\n{inline}\n<script>\n{js}\n</script>\n</body>\n</html>\n")
        out = out_dir / "value-radar-ai.html"

    out.write_text(doc, encoding="utf-8")
    print(f"{out}  ({out.stat().st_size / 1024:.0f} KB)")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifact", action="store_true")
    build(ap.parse_args().artifact)
