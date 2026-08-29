// ルーターとデータ読み込み。ビルド不要のESM。
import { $, $$, el } from './util.js';
import * as V from './views.js';

const DATA_URL = new URL('../../data/latest.json', import.meta.url);
const SERIES_URL = new URL('../../data/series.json', import.meta.url);

async function boot() {
  // 単一ファイル版（scripts/build_single_file.py）はデータを埋め込んで渡す。
  let db = window.__VR_INLINE_DATA__ || null;
  try {
    if (!db) {
      const res = await fetch(DATA_URL, { cache: 'no-store' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      db = await res.json();
    }
  } catch (e) {
    $('#main').replaceChildren(el('div', { class: 'card' },
      el('div', { style: 'font-weight:700;margin-bottom:6px' }, 'データを読み込めませんでした'),
      el('div', { class: 'sub' },
        'data/latest.json が見つかりません。リポジトリのルートで次を実行してください：'),
      el('pre', { class: 'mono', style: 'background:var(--surface-2);padding:10px;border-radius:8px;overflow:auto' },
        'python3 -m engine.pipeline\npython3 -m http.server 8000'),
      el('div', { class: 'muted', style: 'font-size:11.5px' }, String(e))));
    return;
  }
  if (window.__VR_INLINE_SERIES__) {
    db.series = window.__VR_INLINE_SERIES__;
  } else {
    try {
      const s = await fetch(SERIES_URL, { cache: 'no-store' });
      if (s.ok) db.series = await s.json();
    } catch { /* 推移データは任意 */ }
  }

  V.setDB(db);
  window.__VR = db;

  const m = db.meta;
  $('#asof').textContent = `AS OF ${m.as_of}`;
  const dm = $('#datamode');
  dm.textContent = m.is_demo_data ? 'DEMO DATA（合成値）' : `LIVE: ${m.provider}`;
  dm.className = 'badge ' + (m.is_demo_data ? 'demo' : 'live');
  $('#disclaimer').textContent = m.disclaimer;

  if (m.is_demo_data) {
    const n = el('div', { class: 'notice' },
      el('strong', {}, 'これはデモデータです。'),
      ' 表示されている株価・財務数値・需要エビデンス・優待情報は、決定論的に生成された',
      el('strong', {}, '合成値（架空の数値）'),
      'であり、実際の市場データではありません。企業名・ティッカー・上場市場・売買単位・事業内容は実在の公開情報に基づきますが、'
      + 'それに紐づく数値は実在企業の実績ではなく、投資判断には使用できません。'
      + '実データへは VR_PROVIDER=yfinance（無料）または VR_PROVIDER=premium（有料データ）で切り替えられます。');
    $('#main').before(n);
  }
  route();
}

function route() {
  const hash = location.hash || '#/today';
  const [, page, arg] = hash.replace(/^#\//, '').split('/').reduce(
    (a, x, i) => (i === 0 ? [null, x, ''] : [a[0], a[1], x]), [null, 'today', '']);

  $$('#tabs a').forEach(a => a.classList.toggle('active', a.getAttribute('href') === `#/${page}`));

  let node;
  try {
    if (page === 'today') node = V.viewToday();
    else if (page === 'discover') node = V.viewDiscover();
    else if (page === 'trends') node = V.viewTrends(arg ? decodeURIComponent(arg) : null);
    else if (page === 'stock') node = V.viewStock(arg ? decodeURIComponent(arg) : null);
    else if (page === 'portfolio') node = V.viewPortfolio();
    else node = V.viewToday();
  } catch (e) {
    console.error(e);
    node = el('div', { class: 'card' }, `画面の描画でエラーが発生しました: ${e.message}`);
  }
  $('#main').replaceChildren(node);
  window.scrollTo({ top: 0 });
}

window.addEventListener('hashchange', route);

$('#themebtn').addEventListener('click', () => {
  // スタンプが無い状態（OS設定に従っている）から押されたら、
  // 「いま見えている側の逆」へ切り替える。
  const stamp = document.documentElement.getAttribute('data-theme');
  const effective = stamp
    || (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
  const next = effective === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  try { localStorage.setItem('value-radar-ai/theme', next); } catch { /* noop */ }
  if (window.__VR) route();   // チャートの配色はJS側で決めているため再描画する
});
try {
  const saved = localStorage.getItem('value-radar-ai/theme');
  if (saved) document.documentElement.setAttribute('data-theme', saved);
} catch { /* noop */ }

boot();
