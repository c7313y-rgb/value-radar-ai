// チャート部品。すべて自前SVG／DOMで、外部ライブラリなし。
// 形の選択はデータの仕事に従っている:
//   レイヤー内訳 = 大きさの比較 → 横バー＋sequentialの単一色相
//   需要マップ   = 大きさの比較 → 横バー
//   需要連鎖     = 関係の表現   → ノードリンク図（深さでsequential）
//   スコア推移   = 時系列       → 単一系列のスパークライン
import { el, svg, fmt, seqColor, bindTip } from './util.js';

const LAYER_LABEL = {
  quality: '企業品質', value: '割安度', growth: '成長', health: '財務健全性',
  momentum: '株価・需給', diversification: '世界分散', governance: '経営・競争力',
  trend: '未来需要',
};
const LAYER_WEIGHT = {
  quality: 20, value: 20, growth: 15, health: 10,
  momentum: 10, diversification: 5, governance: 10, trend: 10,
};
export const LAYER_ORDER = ['quality', 'value', 'growth', 'health',
                            'momentum', 'diversification', 'governance', 'trend'];

/** 8レイヤーの横バー。値は必ず数値ラベルを添える（色だけに頼らない）。 */
export function layerBars(layers, detail = null, compact = false) {
  const wrap = el('div', { class: 'bars' });
  for (const k of LAYER_ORDER) {
    const v = layers[k] ?? 0;
    const fill = el('div', { class: 'bar-fill' });
    fill.style.width = `${Math.max(1.5, v)}%`;
    fill.style.background = seqColor(v);
    const track = el('div', { class: 'bar-track' }, fill);
    const row = el('div', { class: 'bar-row' },
      el('span', { class: 'lbl' }, compact ? LAYER_LABEL[k] : `${LAYER_LABEL[k]}`),
      track,
      el('span', { class: 'val' }, v.toFixed(0)));
    let tipHtml = `<b>${LAYER_LABEL[k]}</b>　配点 ${LAYER_WEIGHT[k]}点<br>スコア ${v.toFixed(1)} / 100`;
    if (detail && detail[k] && detail[k].length) {
      tipHtml += '<br><span style="color:var(--text-3)">内訳: '
        + detail[k].slice(0, 5).map(d => `${d.metric} ${d.score.toFixed(0)}`).join(' / ') + '</span>';
    }
    bindTip(row, tipHtml);
    wrap.append(row);
  }
  return wrap;
}

/** 汎用の横バーランキング。 */
export function rankBars(items, { max = 100, labelKey = 'label', valueKey = 'value',
                                  fmtVal = (v) => v.toFixed(0), onClick = null,
                                  tipOf = null, colorOf = null } = {}) {
  const wrap = el('div', { class: 'bars' });
  for (const it of items) {
    const v = it[valueKey] ?? 0;
    const fill = el('div', { class: 'bar-fill' });
    fill.style.width = `${Math.max(1.5, Math.min(100, (v / max) * 100))}%`;
    fill.style.background = colorOf ? colorOf(it) : seqColor(v, 0, max);
    const row = el('div', { class: 'bar-row' },
      el('span', { class: 'lbl' }, it[labelKey]),
      el('div', { class: 'bar-track' }, fill),
      el('span', { class: 'val' }, fmtVal(v)));
    if (tipOf) bindTip(row, tipOf(it));
    if (onClick) { row.style.cursor = 'pointer'; row.addEventListener('click', () => onClick(it)); }
    wrap.append(row);
  }
  return wrap;
}

/** 単一系列のスパークライン（スコア推移）。 */
export function sparkline(values, { w = 220, h = 44, color = 'var(--series-1)' } = {}) {
  if (!values || values.length < 2) return el('span', { class: 'muted' }, 'データ不足');
  const lo = Math.min(...values), hi = Math.max(...values);
  const span = (hi - lo) || 1;
  const pts = values.map((v, i) => [
    (i / (values.length - 1)) * (w - 4) + 2,
    h - 4 - ((v - lo) / span) * (h - 8),
  ]);
  const d = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
  const s = svg('svg', { width: w, height: h, viewBox: `0 0 ${w} ${h}`, role: 'img',
                         'aria-label': `推移 ${lo.toFixed(1)}〜${hi.toFixed(1)}` },
    svg('path', { d, fill: 'none', stroke: color, 'stroke-width': 2,
                  'stroke-linecap': 'round', 'stroke-linejoin': 'round' }),
    svg('circle', { cx: pts.at(-1)[0], cy: pts.at(-1)[1], r: 3.5, fill: color,
                    stroke: 'var(--surface-1)', 'stroke-width': 2 }));
  return s;
}

/**
 * 需要連鎖のノードリンク図。
 * 横軸＝ドライバーからの段数（1次/2次/3次…）、縦＝同段のノード。
 * 色は「未織り込みギャップ」ではなく段数（sequential）に割り当て、
 * ギャップは棒の長さと数値ラベルで示す（色に2つの意味を持たせない）。
 */
export function chainDiagram(nodes, edges, { focus = null, onClick = null } = {}) {
  const byDepth = new Map();
  for (const n of nodes) {
    if (!byDepth.has(n.depth)) byDepth.set(n.depth, []);
    byDepth.get(n.depth).push(n);
  }
  const depths = [...byDepth.keys()].sort((a, b) => a - b);
  const colW = 190, rowH = 34, padX = 12, padY = 26;
  const maxRows = Math.max(...depths.map(d => byDepth.get(d).length));
  const W = padX * 2 + colW * depths.length;
  const H = padY * 2 + rowH * maxRows;

  const pos = new Map();
  depths.forEach((d, di) => {
    const list = byDepth.get(d).sort((a, b) => b.pressure - a.pressure);
    list.forEach((n, ri) => {
      pos.set(n.id, { x: padX + di * colW, y: padY + ri * rowH + rowH / 2, node: n });
    });
  });

  const s = svg('svg', { viewBox: `0 0 ${W} ${H}`, width: '100%', height: H,
                         role: 'img', 'aria-label': '需要連鎖のノードリンク図' });

  // エッジ
  const gE = svg('g', {});
  for (const e of edges) {
    const a = pos.get(e.src), b = pos.get(e.dst);
    if (!a || !b) continue;
    const dim = focus && e.src !== focus && e.dst !== focus;
    const x1 = a.x + 150, y1 = a.y, x2 = b.x, y2 = b.y;
    const mx = (x1 + x2) / 2;
    gE.append(svg('path', {
      d: `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`,
      fill: 'none', stroke: dim ? 'var(--border-soft)' : 'var(--border)',
      'stroke-width': dim ? 1 : Math.max(1, e.elasticity * 2.4),
      opacity: dim ? 0.35 : 0.85,
    }));
  }
  s.append(gE);

  // ノード
  for (const [id, p] of pos) {
    const n = p.node;
    const g = svg('g', { style: 'cursor:pointer' });
    const active = !focus || focus === id;
    g.append(svg('rect', {
      x: p.x, y: p.y - 12, width: 150, height: 24, rx: 6,
      fill: 'var(--surface-2)',
      stroke: active ? seqColor(n.pressure, 40, 90) : 'var(--border-soft)',
      'stroke-width': focus === id ? 2 : 1,
      opacity: active ? 1 : 0.45,
    }));
    g.append(svg('rect', {
      x: p.x + 1, y: p.y + 8, width: Math.max(2, 148 * Math.min(1, n.pressure / 100)),
      height: 3, rx: 1.5, fill: seqColor(n.pressure, 40, 90), opacity: active ? 1 : 0.4,
    }));
    const t = svg('text', {
      x: p.x + 8, y: p.y + 2, 'font-size': 11, fill: 'var(--text-1)',
      opacity: active ? 1 : 0.5,
    }, n.label.length > 11 ? n.label.slice(0, 10) + '…' : n.label);
    g.append(t);
    g.append(svg('text', {
      x: p.x + 143, y: p.y + 2, 'font-size': 10, 'text-anchor': 'end',
      fill: 'var(--text-3)', opacity: active ? 1 : 0.5,
      style: 'font-variant-numeric:tabular-nums',
    }, n.pressure.toFixed(0)));
    bindTip(g, `<b>${n.label}</b>（${n.depth}次）<br>需要圧力 ${n.pressure}／100<br>`
      + `実需エビデンス ${n.evidence}・3ヶ月変化 ${n.momentum >= 0 ? '+' : ''}${n.momentum}<br>`
      + `上流からの流入 ${n.inflow >= 0 ? '+' : ''}${n.inflow}`);
    if (onClick) g.addEventListener('click', () => onClick(n));
    s.append(g);
  }

  const box = el('div', { style: 'overflow-x:auto' });
  const inner = el('div', { style: `min-width:${W}px` }, s);
  box.append(inner);
  return box;
}

/** メーター（1つの比率を上限に対して示す）。 */
export function meter(value, max, label, color = 'var(--series-1)') {
  const fill = el('div', { class: 'bar-fill' });
  fill.style.width = `${Math.max(1, Math.min(100, (value / max) * 100))}%`;
  fill.style.background = color;
  return el('div', {},
    el('div', { style: 'display:flex;justify-content:space-between;font-size:11.5px;color:var(--text-3)' },
      el('span', {}, label), el('span', { class: 'mono' }, `${value.toFixed(1)} / ${max}`)),
    el('div', { class: 'bar-track', style: 'margin-top:4px' }, fill));
}
