// 共通ユーティリティ（DOM生成・整形）
export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

export function el(tag, attrs = {}, ...children) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === 'class') n.className = v;
    else if (k === 'html') n.innerHTML = v;
    else if (k.startsWith('on') && typeof v === 'function') n.addEventListener(k.slice(2), v);
    else if (k === 'dataset') Object.assign(n.dataset, v);
    else n.setAttribute(k, v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    n.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return n;
}

export const fmt = {
  n(v, d = 0) {
    if (v === null || v === undefined || Number.isNaN(v)) return '—';
    return Number(v).toLocaleString('ja-JP', { minimumFractionDigits: d, maximumFractionDigits: d });
  },
  pct(v, d = 1) { return v === null || v === undefined ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(d)}%`; },
  price(v, cur) {
    const d = (cur === 'JPY' || cur === 'KRW' || cur === 'TWD') ? 0 : 2;
    return `${fmt.n(v, d)} ${cur}`;
  },
  jpy(v) { return `${fmt.n(Math.round(v))}円`; },
  man(v) {
    if (v >= 100000000) return `${(v / 100000000).toFixed(v % 100000000 ? 1 : 0)}億円`;
    if (v >= 10000) return `${fmt.n(Math.round(v / 10000))}万円`;
    return `${fmt.n(Math.round(v))}円`;
  },
};

export function toJPY(amount, currency, rates) {
  return amount * (rates[currency] ?? 1);
}

export function stars(n) { return '★'.repeat(n) + '☆'.repeat(5 - n); }

// 値の大きさを sequential blue ramp の1色に写す（順序尺度・大きいほど濃い）
const SEQ = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95'];
export function seqColor(v, lo = 0, hi = 100) {
  const t = Math.max(0, Math.min(1, (v - lo) / (hi - lo)));
  return SEQ[Math.min(SEQ.length - 1, Math.floor(t * SEQ.length))];
}

export function gradeColor(g) {
  return { S: 'var(--good)', A: 'var(--good)', B: 'var(--text-2)',
           C: 'var(--warning)', D: 'var(--critical)' }[g] || 'var(--text-2)';
}

// ツールチップ（全チャート共通の hover レイヤー）
const tip = () => document.getElementById('tip');
export function bindTip(node, html) {
  node.addEventListener('mouseenter', (e) => {
    const t = tip(); t.innerHTML = html; t.classList.add('on'); move(e);
  });
  node.addEventListener('mousemove', move);
  node.addEventListener('mouseleave', () => tip().classList.remove('on'));
  function move(e) {
    const t = tip();
    const x = Math.min(e.clientX + 14, window.innerWidth - t.offsetWidth - 10);
    const y = Math.max(8, e.clientY - t.offsetHeight - 12);
    t.style.left = `${x}px`; t.style.top = `${y}px`;
  }
}

export function svg(tag, attrs = {}, ...children) {
  const n = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    n.setAttribute(k, v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    n.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return n;
}
