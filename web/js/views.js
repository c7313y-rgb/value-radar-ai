// 5画面（TODAY / DISCOVER / TRENDS / STOCK / PORTFOLIO）と、テーマ別ガイド。
import { el, fmt, stars, seqColor, gradeColor, bindTip, toJPY } from './util.js';
import { layerBars, rankBars, sparkline, chainDiagram, meter, LAYER_ORDER } from './charts.js';

let DB = null;
export function setDB(db) { DB = db; }
const go = (h) => { location.hash = h; };

// ---- 画面見出し ----
// 画像を敷くのは、その画像が説明の役に立つ場合だけ（需要連鎖の図解）。
// それ以外は文字だけの帯にする。自分の画面のスクリーンショットを
// 自分の画面の上に重ねても情報が増えないため。
const heroBand = (kicker, title, sub) =>
  el('div', { class: 'hero hero-band' },
    el('div', { class: 'hero-overlay' },
      el('div', { class: 'hero-kicker' }, kicker),
      el('div', { class: 'hero-title' }, title),
      sub ? el('div', { class: 'hero-sub' }, sub) : null));

const heroBanner = (img, kicker, title, sub, alt) =>
  el('figure', { class: 'hero hero-image', style: `background-image:url('${img}')`,
                 role: 'img', 'aria-label': alt || title },
    el('div', { class: 'hero-overlay' },
      el('div', { class: 'hero-kicker' }, kicker),
      el('div', { class: 'hero-title' }, title),
      sub ? el('div', { class: 'hero-sub' }, sub) : null));

const gradePill = (g, label) =>
  el('span', { class: `pill g-${g}`, title: label }, `${label} ${g}`);

// ---------------------------------------------------------------- 銘柄カード
function stockCard(r, { rank = true } = {}) {
  const rates = DB.meta.fx_rates_jpy;
  const minJpy = toJPY(r.min_investment, r.currency, rates);
  const card = el('div', { class: 'card stock-card', onclick: () => go(`#/stock/${encodeURIComponent(r.ticker)}`) });

  card.append(el('div', { class: 'stock-head' },
    el('div', { style: 'flex:1;min-width:0' },
      rank && el('div', { class: 'rank-badge' }, `#${r.rank}`),
      el('div', { class: 'stock-name' }, r.name),
      el('div', { class: 'stock-meta' },
        `${r.ticker}・${r.exchange}・${r.sector}／${r.industry}`)),
    el('div', {},
      el('div', { class: 'score-big', style: `color:${seqColor(r.final_score, 25, 75)}` },
        r.final_score.toFixed(1)),
      el('div', { class: 'score-cap' }, '最終推奨点'))));

  card.append(el('div', { style: 'display:flex;gap:6px;flex-wrap:wrap;margin:9px 0 10px;align-items:center' },
    gradePill(r.company_grade, '企業評価'),
    gradePill(r.price_grade, '価格評価'),
    el('span', { class: `verdict v-${r.verdict}` }, r.verdict_label),
    el('span', { class: 'stars', title: '初心者向けの総合しやすさ' }, stars(r.stars))));

  const kv = el('dl', { class: 'kv' });
  const add = (k, v, t) => {
    kv.append(el('dt', {}, k));
    const dd = el('dd', {}, v);
    if (t) bindTip(dd, t);
    kv.append(dd);
  };
  add('現在株価', `${fmt.price(r.price, r.currency)}（${fmt.pct(r.change_pct, 2)}）`);
  add('最低購入額', r.currency === 'JPY' ? fmt.man(minJpy)
      : `${fmt.man(minJpy)}（${r.lot}株単位）`, `${r.lot}株 × ${fmt.price(r.price, r.currency)}`);
  add('適正価値', fmt.price(r.fair_value, r.currency), '3手法（ピア相対PER／FCF利回り／成長織り込み）の加重平均');
  add('推定Upside', fmt.pct(r.upside_pct, 0));
  add('購入検討価格帯', `${fmt.n(r.entry_low, r.currency === 'JPY' ? 0 : 2)}〜${fmt.n(r.entry_high, r.currency === 'JPY' ? 0 : 2)}`,
      '適正価値からリスク相応の安全域を引いた水準');
  add('リスク減点', `−${r.risk_points.toFixed(1)}`, r.risk_items.map(i => `${i.name}: ${i.why}`).join('<br>'));
  add('確信度', `${(r.confidence * 100).toFixed(0)}%`,
      r.confidence_parts.map(p => `${p.name}: ${p.value}`).join('<br>'));
  card.append(kv);

  card.append(el('div', { style: 'margin-top:11px' }, layerBars(r.layers, r.layer_detail, true)));

  card.append(el('div', { class: 'reason' },
    el('div', { class: 'muted', style: 'font-size:11px;letter-spacing:.1em;margin-bottom:3px' },
      'なぜ今日この銘柄なのか'),
    el('ol', {}, r.reason.map(t => el('li', {}, t)))));

  if (r.committee.dissent) {
    card.append(el('div', { class: 'notice', style: 'margin:10px 0 0' },
      el('strong', {}, '反対意見あり　'), r.committee.dissent));
  }
  return card;
}

// ---------------------------------------------------------------- TODAY
export function viewToday() {
  const root = el('div', {});
  const rows = DB.rows;

  root.append(heroBand(
    'VALUE RADAR AI — AI INVESTMENT COMMITTEE',
    '毎朝、世界の企業価値を評価し直す。',
    '8レイヤーの再評価と需要連鎖の分析結果を、根拠となる数値とともに開示します。'
    + '売買を推奨するものではありません。'));
  root.append(el('h2', { class: 'section' }, `本日の投資候補 TOP10 — ${DB.meta.as_of}`));
  root.append(el('div', { class: 'sub', style: 'margin-bottom:12px' },
    `世界${DB.meta.universe_size}銘柄を8レイヤーで再評価し、需要連鎖の波及と価格の織り込み度で並べ替えた結果です。`
    + '「良い会社」と「良い株価」は分けて表示しています。'));

  const grid = el('div', { class: 'grid c2' });
  rows.slice(0, 10).forEach(r => grid.append(stockCard(r)));
  root.append(grid);

  // 良い会社・価格待ち
  const waiting = rows.filter(r => r.verdict === 'QUALITY_WAIT').slice(0, 6);
  if (waiting.length) {
    root.append(el('h2', { class: 'section' }, '良い会社・価格待ち（企業評価は高いが、いま買う価格ではない）'));
    root.append(el('div', { class: 'card' },
      el('div', { class: 'table-wrap' }, waitTable(waiting))));
  }

  // アラート
  root.append(el('h2', { class: 'section' }, `本日のアラート（前回比 ${DB.alerts.length}件）`));
  const ac = el('div', { class: 'card' });
  DB.alerts.slice(0, 12).forEach(a => {
    ac.append(el('div', { class: 'alert' },
      el('div', { class: `sev sev-${a.severity}` }),
      el('div', {},
        el('div', { class: 'title' }, a.title),
        el('div', { class: 'detail' }, a.detail || ''))));
  });
  if (!DB.alerts.length) ac.append(el('span', { class: 'muted' }, '変化なし'));
  root.append(ac);

  // 二次・三次波及
  root.append(el('h2', { class: 'section' }, '未織り込みギャップ上位（次に利益が流れ込む場所）'));
  const oc = el('div', { class: 'card' });
  oc.append(el('div', { class: 'sub', style: 'margin-bottom:10px' },
    '需要圧力が高いのに、そこに属する企業の株価がまだ織り込んでいない領域。'
    + 'NVIDIAが上がりきった後に、次に利益が流れ込む場所を探すための指標です。'));
  oc.append(rankBars(DB.opportunities.slice(0, 8).map(o => ({ ...o, value: o.unpriced_gap })), {
    max: Math.max(...DB.opportunities.map(o => o.unpriced_gap), 10),
    labelKey: 'label', valueKey: 'value',
    fmtVal: (v) => (v >= 0 ? '+' : '') + v.toFixed(0),
    tipOf: (o) => `<b>${o.label}</b>（${o.depth}次需要）<br>需要圧力 ${o.pressure}<br>`
      + `株価の織り込み度 ${o.priced_in}<br>該当企業 ${o.companies}社<br>`
      + `<span style="color:var(--text-3)">${o.paths[0] || ''}</span>`,
    onClick: (o) => go(`#/trends/${o.id}`),
  }));
  root.append(oc);
  return root;
}

function waitTable(rows) {
  const t = el('table', { class: 'data' });
  t.append(el('thead', {}, el('tr', {},
    el('th', {}, '銘柄'), el('th', {}, '企業'), el('th', {}, '価格'),
    el('th', { class: 'num' }, 'PER'), el('th', { class: 'num' }, 'FCF利回り'),
    el('th', { class: 'num' }, '現在株価'), el('th', { class: 'num' }, '購入検討価格帯'),
    el('th', {}, '価格評価の上限理由'))));
  const tb = el('tbody', {});
  rows.forEach(r => {
    tb.append(el('tr', { onclick: () => go(`#/stock/${encodeURIComponent(r.ticker)}`) },
      el('td', {}, el('div', {}, r.name), el('div', { class: 'muted', style: 'font-size:11px' }, r.ticker)),
      el('td', {}, gradePill(r.company_grade, '企業')),
      el('td', {}, gradePill(r.price_grade, '価格')),
      el('td', { class: 'num' }, r.f.per.toFixed(0)),
      el('td', { class: 'num' }, `${r.f.fcf_yield.toFixed(1)}%`),
      el('td', { class: 'num' }, fmt.n(r.price, r.currency === 'JPY' ? 0 : 2)),
      el('td', { class: 'num' }, `${fmt.n(r.entry_low, r.currency === 'JPY' ? 0 : 2)}〜${fmt.n(r.entry_high, r.currency === 'JPY' ? 0 : 2)}`),
      el('td', { class: 'muted', style: 'font-size:11.5px' }, r.price_caps.join('・') || '—')));
  });
  t.append(tb);
  return t;
}

// ---------------------------------------------------------------- DISCOVER
const F = { q: '', region: '', sector: '', verdict: '', node: '', sort: 'final_score', maxJpy: 0 };

export function viewDiscover() {
  const root = el('div', {});
  root.append(heroBand(
    'DISCOVER — GLOBAL SCREENING',
    '世界の銘柄を、あなたの条件で絞り込む。',
    '地域・セクター・予算・需要テーマで絞り込み、「良い会社」と「良い株価」を分けて確認できます。'));
  root.append(el('h2', { class: 'section' }, `世界株スクリーニング（${DB.meta.universe_size}銘柄）`));

  const regions = [...new Set(DB.rows.map(r => r.region))].sort();
  const sectors = [...new Set(DB.rows.map(r => r.sector))].sort();
  const nodes = DB.nodes.filter(n => !n.is_driver);

  const bar = el('div', { class: 'filters' });
  const mk = (label, node) => el('span', {}, el('label', {}, label + ' '), node);
  const q = el('input', { type: 'search', placeholder: '銘柄名・ティッカー・事業内容', value: F.q, oninput: (e) => { F.q = e.target.value; render(); } });
  const sel = (opts, key, blank) => el('select', {
    onchange: (e) => { F[key] = e.target.value; render(); },
  }, el('option', { value: '' }, blank), opts.map(o =>
    el('option', { value: o.v ?? o, selected: F[key] === (o.v ?? o) }, o.t ?? o)));

  bar.append(mk('検索', q));
  bar.append(mk('地域', sel(regions, 'region', 'すべて')));
  bar.append(mk('セクター', sel(sectors, 'sector', 'すべて')));
  bar.append(mk('判定', sel([
    { v: 'STRONG_CANDIDATE', t: '本日の有力候補' }, { v: 'CANDIDATE', t: '検討候補' },
    { v: 'QUALITY_WAIT', t: '良い会社・価格待ち' }, { v: 'WATCH', t: '監視' }, { v: 'PASS', t: '見送り' },
  ], 'verdict', 'すべて')));
  bar.append(mk('需要テーマ', sel(nodes.map(n => ({ v: n.id, t: n.label })), 'node', 'すべて')));
  bar.append(mk('予算上限', sel([
    { v: '50000', t: '5万円' }, { v: '100000', t: '10万円' }, { v: '300000', t: '30万円' },
    { v: '500000', t: '50万円' }, { v: '1000000', t: '100万円' },
  ], 'maxJpy', '指定なし')));
  bar.append(mk('並び替え', sel([
    { v: 'final_score', t: '最終推奨点' }, { v: 'value_score', t: 'VALUE SCORE' },
    { v: 'upside_pct', t: '推定Upside' }, { v: 'layers.value', t: '割安度' },
    { v: 'layers.quality', t: '企業品質' }, { v: 'layers.trend', t: '未来需要' },
    { v: 'risk_points', t: 'リスクの小ささ' },
  ], 'sort', null)));
  root.append(bar);

  const holder = el('div', { class: 'card' });
  root.append(holder);

  function render() {
    const rates = DB.meta.fx_rates_jpy;
    let rows = DB.rows.filter(r => {
      if (F.region && r.region !== F.region) return false;
      if (F.sector && r.sector !== F.sector) return false;
      if (F.verdict && r.verdict !== F.verdict) return false;
      if (F.node && !(r.nodes[F.node] > 0)) return false;
      if (F.maxJpy && toJPY(r.min_investment, r.currency, rates) > Number(F.maxJpy)) return false;
      if (F.q) {
        const s = (r.name + r.name_en + r.ticker + r.biz + r.industry).toLowerCase();
        if (!s.includes(F.q.toLowerCase())) return false;
      }
      return true;
    });
    const key = F.sort;
    rows = rows.sort((a, b) => {
      const get = (o) => key.includes('.') ? key.split('.').reduce((x, k) => x[k], o) : o[key];
      return key === 'risk_points' ? get(a) - get(b) : get(b) - get(a);
    });

    holder.replaceChildren();
    holder.append(el('div', { class: 'sub', style: 'margin-bottom:8px' },
      `${rows.length}銘柄　${F.maxJpy ? `（最低購入額 ${fmt.man(Number(F.maxJpy))}以内）` : ''}`));
    const t = el('table', { class: 'data' });
    t.append(el('thead', {}, el('tr', {},
      el('th', {}, '銘柄'), el('th', {}, '地域'), el('th', { class: 'num' }, '最終点'),
      el('th', { class: 'num' }, 'VALUE'), el('th', {}, '企業/価格'),
      el('th', { class: 'num' }, '株価'), el('th', { class: 'num' }, '最低購入額'),
      el('th', { class: 'num' }, 'Upside'), el('th', { class: 'num' }, 'PER'),
      el('th', {}, '判定'), el('th', {}, '★'))));
    const tb = el('tbody', {});
    rows.slice(0, 200).forEach(r => {
      tb.append(el('tr', { onclick: () => go(`#/stock/${encodeURIComponent(r.ticker)}`) },
        el('td', {}, el('div', {}, r.name),
          el('div', { class: 'muted', style: 'font-size:11px' }, `${r.ticker}・${r.industry}`)),
        el('td', { class: 'muted' }, r.region),
        el('td', { class: 'num', style: `color:${seqColor(r.final_score, 25, 75)};font-weight:700` }, r.final_score.toFixed(1)),
        el('td', { class: 'num' }, r.value_score.toFixed(0)),
        el('td', { class: 'nowrap' }, gradePill(r.company_grade, '企'), ' ', gradePill(r.price_grade, '価')),
        el('td', { class: 'num' }, fmt.n(r.price, r.currency === 'JPY' ? 0 : 2)),
        el('td', { class: 'num' }, fmt.man(toJPY(r.min_investment, r.currency, rates))),
        el('td', { class: 'num' }, fmt.pct(r.upside_pct, 0)),
        el('td', { class: 'num' }, r.f.per.toFixed(0)),
        el('td', { class: `verdict v-${r.verdict}` }, r.verdict_label),
        el('td', { class: 'stars' }, stars(r.stars))));
    });
    t.append(tb);
    holder.append(el('div', { class: 'table-wrap' }, t));
  }
  render();
  return root;
}

// ---------------------------------------------------------------- TRENDS
export function viewTrends(nodeId) {
  const root = el('div', {});
  if (nodeId) return viewThemeGuide(nodeId);

  root.append(heroBanner('web/assets/demand-chain.jpg',
    'SECOND ORDER OPPORTUNITY ENGINE',
    '一次需要から三次・四次需要までを辿る。',
    '受注残・リードタイム・設備投資などの実需シグナルを Demand Evidence Score として数値化し、'
    + '需要がどこへ波及するかの仮説を、伝播係数と遅れ月数とともに提示します。',
    '生成AIから、GPU・データセンター・送配電網・発電設備・建設へと需要が波及する様子を示した概念図'));
  root.append(el('h2', { class: 'section' }, '需要マップ — 実需の連鎖と、まだ評価されていない場所'));
  root.append(el('div', { class: 'sub', style: 'margin-bottom:12px' },
    '「AIが流行っている」ではなく「DC建設増 → 電力設備発注増 → 変圧器リードタイム上昇 → 受注残増 → だが株価は未追随」まで辿ります。'
    + 'ノードをクリックするとテーマ別の投資ガイドが開きます。'));

  const card = el('div', { class: 'card' });
  card.append(el('div', { class: 'muted', style: 'font-size:11px;letter-spacing:.1em;margin-bottom:6px' },
    '需要連鎖グラフ（左＝一次需要 → 右＝三次・四次需要。棒＝需要圧力）'));
  card.append(chainDiagram(DB.nodes, DB.edges, { onClick: (n) => go(`#/trends/${n.id}`) }));
  root.append(card);

  root.append(el('h2', { class: 'section' }, '未織り込みギャップ ランキング'));
  const g = el('div', { class: 'grid c3' });
  DB.opportunities.slice(0, 9).forEach(o => {
    const c = el('div', { class: 'card node-card', onclick: () => go(`#/trends/${o.id}`) });
    c.append(el('div', { style: 'display:flex;justify-content:space-between;align-items:flex-start;gap:8px' },
      el('div', {},
        el('div', { style: 'font-weight:700' }, o.label),
        el('div', { class: 'muted', style: 'font-size:11px' }, `${o.depth}次需要・該当${o.companies}社`)),
      el('div', { style: 'text-align:right' },
        el('div', { class: `gap-num ${o.unpriced_gap >= 0 ? 'gap-pos' : 'gap-neg'}` },
          (o.unpriced_gap >= 0 ? '+' : '') + o.unpriced_gap.toFixed(0)),
        el('div', { class: 'score-cap' }, '未織り込み'))));
    c.append(el('div', { style: 'margin-top:9px' },
      meter(o.pressure, 100, '需要圧力', seqColor(o.pressure, 40, 90)),
      el('div', { style: 'height:6px' }),
      meter(o.priced_in, 100, '株価の織り込み度', 'var(--neutral)')));
    c.append(el('div', { class: 'chain', style: 'margin-top:9px' }, o.paths[0] || ''));
    g.append(c);
  });
  root.append(g);

  root.append(el('h2', { class: 'section' }, '全ノードの実需エビデンス'));
  const tc = el('div', { class: 'card' });
  tc.append(rankBars(DB.nodes.filter(n => !n.is_driver).slice(0, 24).map(n => ({ ...n, value: n.pressure })), {
    max: 100, labelKey: 'label', valueKey: 'value',
    fmtVal: (v) => v.toFixed(0),
    tipOf: (n) => `<b>${n.label}</b><br>${n.desc}<br>実需エビデンス ${n.evidence}／変化 ${n.momentum >= 0 ? '+' : ''}${n.momentum}`,
    onClick: (n) => go(`#/trends/${n.id}`),
  }));
  root.append(tc);
  return root;
}

// ------------------------------------------------- テーマ別 投資ガイド
export function viewThemeGuide(nodeId) {
  const guide = DB.guides.find(g => g.node === nodeId);
  const root = el('div', {});
  root.append(el('a', { href: '#/trends', class: 'muted', style: 'font-size:12px' }, '← 需要マップへ戻る'));
  if (!guide) return themeFallback(root, nodeId);
  const rates = DB.meta.fx_rates_jpy;

  root.append(el('div', { class: 'card', style: 'margin-top:10px' },
    el('div', { class: 'guide-head' },
      el('h3', {}, guide.title),
      el('div', { class: 'sub' }, `${guide.subtitle}　／　${guide.as_of} 時点`)),
    el('div', { class: 'grid c2', style: 'margin-top:14px' },
      el('div', {},
        el('div', { class: 'muted', style: 'font-size:11px;letter-spacing:.1em' }, 'なぜこのテーマが重要なのか'),
        el('ul', { class: 'why' }, guide.why.map(w => el('li', {}, w)))),
      el('div', {},
        el('div', { class: 'muted', style: 'font-size:11px;letter-spacing:.1em' }, '因果経路'),
        el('div', { class: 'chain', style: 'margin:4px 0 12px' }, guide.chains.map(c => el('div', {}, c))),
        el('div', { class: 'muted', style: 'font-size:11px;letter-spacing:.1em' }, '観測している実需シグナル'),
        el('div', { class: 'sites', style: 'margin-top:5px' },
          guide.signals.map(s => el('span', { class: 'site-chip' }, s)))))));

  if (guide.sites.length) {
    root.append(el('div', { class: 'card' },
      el('div', { class: 'muted', style: 'font-size:11px;letter-spacing:.1em;margin-bottom:6px' },
        '需要が発生している現場・拠点'),
      el('div', { class: 'sites' }, guide.sites.map(s => el('span', { class: 'site-chip' }, s)))));
  }

  // TOP5 比較表
  root.append(el('h2', { class: 'section' }, `購入候補 TOP${guide.table.length} 銘柄比較`));
  const t = el('table', { class: 'data' });
  t.append(el('thead', {}, el('tr', {},
    el('th', {}, '順位'), el('th', {}, '銘柄（コード）'), el('th', { class: 'num' }, '現在株価'),
    el('th', { class: 'num' }, '購入検討価格帯'), el('th', { class: 'num' }, '最低購入額'),
    el('th', {}, '配当・優待'), el('th', {}, '評価'), el('th', {}, 'コメント'))));
  const tb = el('tbody', {});
  guide.table.forEach(x => {
    tb.append(el('tr', { onclick: () => go(`#/stock/${encodeURIComponent(x.ticker)}`) },
      el('td', { class: 'mono' }, String(x.rank)),
      el('td', {}, el('div', { style: 'font-weight:600' }, x.name),
        el('div', { class: 'muted', style: 'font-size:11px' }, `${x.ticker}・${x.biz.slice(0, 26)}…`)),
      el('td', { class: 'num' }, fmt.price(x.price, x.currency)),
      el('td', { class: 'num nowrap' }, `${fmt.n(x.entry_low, x.currency === 'JPY' ? 0 : 2)}〜${fmt.n(x.entry_high, x.currency === 'JPY' ? 0 : 2)}`),
      el('td', { class: 'num nowrap' }, `${fmt.man(x.min_investment_jpy)}`,
        el('div', { class: 'muted', style: 'font-size:10.5px' }, `${x.lot}株単位`)),
      el('td', { style: 'font-size:11.5px' },
        el('div', {}, x.div_yield ? `配当利回り ${x.div_yield.toFixed(1)}%` : '配当情報なし'),
        x.yutai ? el('div', { class: 'muted' }, x.yutai) : el('div', { class: 'muted' }, '優待なし／要確認')),
      el('td', { class: 'nowrap' }, el('div', { class: 'stars' }, x.stars_text),
        el('div', { style: 'margin-top:3px' },
          gradePill(x.company_grade, '企業'), ' ', gradePill(x.price_grade, '価格'))),
      el('td', { style: 'font-size:11.5px;color:var(--text-2);max-width:280px' }, x.comment)));
  });
  t.append(tb);
  root.append(el('div', { class: 'card' }, el('div', { class: 'table-wrap' }, t)));

  // 予算別購入例
  root.append(el('h2', { class: 'section' }, '予算別の購入例（このテーマ内で分散した場合）'));
  const bg = el('div', { class: 'grid c4' });
  guide.budget_examples.forEach(b => {
    const box = el('div', { class: 'budget-box' });
    box.append(el('div', { class: 'amt' }, `${fmt.man(b.budget)}で始めるなら`));
    if (!b.positions.length) {
      box.append(el('div', { class: 'muted', style: 'font-size:12px' }, b.note));
    } else {
      box.append(el('ul', {}, b.positions.map(p =>
        el('li', {}, `${p.name} ${fmt.n(p.shares)}株（${fmt.man(p.cost_jpy)}）`))));
      box.append(el('div', { class: 'muted', style: 'font-size:11px;margin-top:5px' },
        `投資額 ${fmt.man(b.invested)}／現金 ${fmt.man(b.cash)}`));
    }
    bg.append(box);
  });
  root.append(bg);

  // 初心者ポイントと注意点
  root.append(el('div', { class: 'grid c2', style: 'margin-top:12px' },
    el('div', { class: 'card' },
      el('div', { class: 'muted', style: 'font-size:11px;letter-spacing:.1em;margin-bottom:4px' },
        '押さえておきたい3つのポイント'),
      el('ol', { class: 'points' }, guide.beginner_points.map(p => el('li', {}, p)))),
    el('div', { class: 'card caution' },
      el('div', { style: 'margin-bottom:4px' }, el('strong', {}, '注意点')),
      el('ul', { class: 'points' }, guide.cautions.map(p => el('li', {}, p))))));
  return root;
}

/** ガイド生成の対象外（該当企業が少ない）ノード向けの簡易ビュー。行き止まりを作らない。 */
function themeFallback(root, nodeId) {
  const n = DB.nodes.find(x => x.id === nodeId);
  const o = DB.opportunities.find(x => x.id === nodeId);
  if (!n) {
    root.append(el('div', { class: 'card', style: 'margin-top:10px' }, '該当する需要テーマが見つかりません。'));
    return root;
  }
  const members = DB.rows.filter(r => r.nodes[nodeId] > 0)
    .sort((a, b) => b.nodes[nodeId] - a.nodes[nodeId]);

  root.append(el('div', { class: 'card', style: 'margin-top:10px' },
    el('div', { class: 'guide-head' },
      el('h3', {}, n.label),
      el('div', { class: 'sub' }, n.desc)),
    el('div', { class: 'grid c3', style: 'margin-top:14px' },
      meter(n.pressure, 100, '需要圧力', seqColor(n.pressure, 40, 90)),
      meter(n.evidence, 100, '実需エビデンス', 'var(--seq-400)'),
      o ? meter(Math.max(0, o.priced_in), 100, '株価の織り込み度', 'var(--neutral)')
        : el('div', { class: 'muted', style: 'font-size:12px' }, '織り込み度は算出対象外（該当企業が少数）')),
    el('div', { class: 'sub', style: 'margin-top:12px' },
      `3ヶ月変化 ${n.momentum >= 0 ? '+' : ''}${n.momentum}pt ／ 上流からの流入 ${n.inflow >= 0 ? '+' : ''}${n.inflow}`)));

  root.append(el('h2', { class: 'section' },
    members.length ? `このテーマに露出する銘柄（${members.length}社）`
                   : 'このテーマに露出する銘柄はユニバース内にありません'));
  if (members.length) {
    const t = el('table', { class: 'data' });
    t.append(el('thead', {}, el('tr', {},
      el('th', {}, '銘柄'), el('th', { class: 'num' }, '露出度'),
      el('th', { class: 'num' }, '最終点'), el('th', {}, '企業/価格'),
      el('th', { class: 'num' }, '最低購入額'), el('th', {}, '判定'))));
    const rates = DB.meta.fx_rates_jpy;
    const tb = el('tbody', {});
    members.forEach(r => tb.append(el('tr', { onclick: () => go(`#/stock/${encodeURIComponent(r.ticker)}`) },
      el('td', {}, el('div', {}, r.name), el('div', { class: 'muted', style: 'font-size:11px' }, `${r.ticker}・${r.industry}`)),
      el('td', { class: 'num' }, `${(r.nodes[nodeId] * 100).toFixed(0)}%`),
      el('td', { class: 'num' }, r.final_score.toFixed(1)),
      el('td', { class: 'nowrap' }, gradePill(r.company_grade, '企'), ' ', gradePill(r.price_grade, '価')),
      el('td', { class: 'num' }, fmt.man(toJPY(r.min_investment, r.currency, rates))),
      el('td', { class: `verdict v-${r.verdict}` }, r.verdict_label))));
    t.append(tb);
    root.append(el('div', { class: 'card' }, el('div', { class: 'table-wrap' }, t)));
    root.append(el('div', { class: 'notice' },
      el('strong', {}, '比較表は未生成　'),
      `このテーマに露出する銘柄がユニバース内に${members.length}社しかないため、TOP5比較表と予算別購入例は作成していません。`
      + '銘柄が2社未満の比較は分散の判断材料にならないためです。'));
  }
  return root;
}

// ---------------------------------------------------------------- STOCK
export function viewStock(ticker) {
  const root = el('div', {});
  if (!ticker) {
    root.append(heroBand(
      'STOCK — DEEP DIVE',
      '1銘柄を、6人のAIアナリストが別々の目的関数で評価。',
      '割安度・企業品質・需要連鎖上の位置と、反対意見までを含めて根拠を開示します。'));
    root.append(el('h2', { class: 'section' }, '銘柄を選択してください'));
    const g = el('div', { class: 'grid c3' });
    DB.rows.slice(0, 12).forEach(r => g.append(el('div', {
      class: 'card stock-card', onclick: () => go(`#/stock/${encodeURIComponent(r.ticker)}`),
    }, el('div', { style: 'font-weight:700' }, r.name),
       el('div', { class: 'muted', style: 'font-size:11.5px' }, `${r.ticker}・最終点 ${r.final_score}`))));
    root.append(g);
    return root;
  }
  const r = DB.rows.find(x => x.ticker === ticker);
  if (!r) { root.append(el('div', { class: 'card' }, '該当銘柄が見つかりません。')); return root; }
  const rates = DB.meta.fx_rates_jpy;

  root.append(el('a', { href: '#/today', class: 'muted', style: 'font-size:12px' }, '← TODAY へ戻る'));

  // ヘッダー
  const head = el('div', { class: 'card', style: 'margin-top:10px' });
  head.append(el('div', { class: 'stock-head' },
    el('div', { style: 'flex:1;min-width:0' },
      el('div', { class: 'stock-name', style: 'font-size:21px' }, r.name),
      el('div', { class: 'stock-meta' }, `${r.name_en}・${r.ticker}・${r.exchange}・${r.country}`),
      el('div', { class: 'sub', style: 'margin-top:7px' }, r.biz)),
    el('div', { style: 'text-align:right' },
      el('div', { class: 'score-big', style: `color:${seqColor(r.final_score, 25, 75)}` }, r.final_score.toFixed(1)),
      el('div', { class: 'score-cap' }, `最終推奨点　VALUE ${r.value_score.toFixed(0)}`))));
  head.append(el('div', { style: 'display:flex;gap:6px;flex-wrap:wrap;margin-top:10px;align-items:center' },
    gradePill(r.company_grade, '企業評価'), gradePill(r.price_grade, '価格評価'),
    el('span', { class: `verdict v-${r.verdict}` }, r.verdict_label),
    el('span', { class: 'stars' }, stars(r.stars)),
    el('span', { class: 'badge' }, `ピア: ${r.peer_group}`)));
  head.append(el('div', { class: 'reason', style: 'margin-top:12px' },
    el('ol', {}, r.reason.map(t => el('li', {}, t)))));
  root.append(head);

  // 計算式の分解
  root.append(el('h2', { class: 'section' }, '最終推奨点の分解'));
  root.append(el('div', { class: 'card' },
    el('div', { class: 'mono', style: 'font-size:13px;margin-bottom:10px' },
      `${r.value_score.toFixed(1)} （VALUE SCORE） × ${r.confidence.toFixed(3)} （確信度） `
      + `− ${r.risk_points.toFixed(1)} （リスク減点） `
      + `${r.committee.chair_adjustment >= 0 ? '+' : ''}${r.committee.chair_adjustment.toFixed(1)} （議長調整） `
      + `= ${r.final_score.toFixed(1)}`),
    el('div', { class: 'grid c2' },
      el('div', {}, el('div', { class: 'muted', style: 'font-size:11px;letter-spacing:.1em;margin-bottom:6px' }, '8レイヤー内訳'),
        layerBars(r.layers, r.layer_detail)),
      el('div', {},
        el('div', { class: 'muted', style: 'font-size:11px;letter-spacing:.1em;margin-bottom:6px' }, 'リスク減点の内訳'),
        r.risk_items.length
          ? el('div', { class: 'bars' }, r.risk_items.map(i =>
              el('div', { class: 'bar-row' },
                el('span', { class: 'lbl' }, i.name),
                el('div', { class: 'bar-track' }, (() => {
                  const f = el('div', { class: 'bar-fill' });
                  f.style.width = `${Math.min(100, i.points / 6 * 100)}%`;
                  f.style.background = 'var(--serious)';
                  return f;
                })()),
                el('span', { class: 'val' }, `−${i.points.toFixed(1)}`))))
          : el('span', { class: 'muted' }, '検出された減点なし'),
        el('div', { class: 'muted', style: 'font-size:11.5px;margin-top:8px' },
          r.risk_items.map(i => `${i.name}：${i.why}`).join(' ／ ')),
        el('div', { class: 'muted', style: 'font-size:11px;letter-spacing:.1em;margin:14px 0 6px' }, '確信度の内訳'),
        el('div', { class: 'bars' }, r.confidence_parts.map(p =>
          el('div', { class: 'bar-row' },
            el('span', { class: 'lbl' }, p.name),
            el('div', { class: 'bar-track' }, (() => {
              const f = el('div', { class: 'bar-fill' });
              f.style.width = `${p.value * 100}%`; f.style.background = 'var(--seq-400)';
              return f;
            })()),
            el('span', { class: 'val' }, p.value.toFixed(2)))))))));

  // 価格と適正価値
  root.append(el('h2', { class: 'section' }, '価格評価 — 良い会社と良い株価を分ける'));
  const pv = el('div', { class: 'card' });
  const kv = el('dl', { class: 'kv', style: 'max-width:520px' });
  const add = (k, v) => { kv.append(el('dt', {}, k)); kv.append(el('dd', {}, v)); };
  add('現在株価', `${fmt.price(r.price, r.currency)}（${fmt.pct(r.change_pct, 2)}）`);
  add('売買単位／最低購入額', `${r.lot}株 ／ ${fmt.man(toJPY(r.min_investment, r.currency, rates))}`);
  add('適正価値（3手法加重）', fmt.price(r.fair_value, r.currency));
  Object.entries(r.fair_methods).forEach(([k, v]) => add(
    { peer_per: '　ピア相対PER法', fcf_yield: '　FCF利回り法', peg: '　成長織り込み法' }[k] || k,
    fmt.price(v, r.currency)));
  add('推定Upside', fmt.pct(r.upside_pct, 0));
  add('購入検討価格帯', `${fmt.n(r.entry_low, r.currency === 'JPY' ? 0 : 2)}〜${fmt.n(r.entry_high, r.currency === 'JPY' ? 0 : 2)} ${r.currency}`);
  add('PER / 予想PER', `${r.f.per.toFixed(1)} / ${r.f.forward_per.toFixed(1)}倍`);
  add('ピア中央値PER', `${r.peer_median_per.toFixed(1)}倍`);
  add('PBR / EV・EBITDA', `${r.f.pbr.toFixed(2)}倍 / ${r.f.ev_ebitda.toFixed(1)}倍`);
  add('FCF利回り / PEG', `${r.f.fcf_yield.toFixed(2)}% / ${r.f.peg.toFixed(2)}`);
  add('配当利回り', r.div_yield ? `${r.div_yield.toFixed(2)}%` : '—');
  if (r.implied_years) add('株価が織り込む成長年数', `約${r.implied_years.toFixed(1)}年分`);
  pv.append(kv);
  if (r.price_caps.length) {
    pv.append(el('div', { class: 'notice', style: 'margin-top:12px' },
      el('strong', {}, '価格評価に上限　'),
      `次の条件に該当するため、企業評価が高くても価格評価は ${r.price_grade} を超えません：`
      + r.price_caps.join('／')));
  }
  root.append(pv);

  // AI投資委員会
  root.append(el('h2', { class: 'section' }, 'AI投資委員会（6エージェント）'));
  const cc = el('div', { class: 'card' });
  cc.append(el('div', { class: 'sub', style: 'margin-bottom:10px' },
    `一致度 ${(r.committee.agreement * 100).toFixed(0)}%　`
    + Object.entries(r.committee.vote).map(([k, v]) => `${k} ${v}`).join('・')));
  const cg = el('div', { class: 'grid c2' });
  r.committee.views.forEach(v => {
    const color = { STRONG_BUY: 'var(--good)', BUY: 'var(--series-1)', HOLD: 'var(--text-2)',
                    AVOID: 'var(--warning)', STRONG_AVOID: 'var(--critical)' }[v.stance];
    cg.append(el('div', { style: 'border-left:2px solid ' + color + ';padding-left:11px' },
      el('div', { style: 'display:flex;justify-content:space-between;gap:8px' },
        el('div', { style: 'font-weight:700;font-size:12.5px' }, `${v.agent}　`,
          el('span', { class: 'muted', style: 'font-weight:400' }, v.role)),
        el('div', { class: 'mono', style: `color:${color};font-size:12px;white-space:nowrap` },
          `${v.stance_label} ${(v.conviction * 100).toFixed(0)}%`)),
      el('div', { class: 'sub', style: 'margin-top:3px' }, v.comment)));
  });
  cc.append(cg);
  if (r.committee.dissent) {
    cc.append(el('div', { class: 'notice', style: 'margin-top:12px' },
      el('strong', {}, '議長の判断　'), r.committee.dissent));
  }
  root.append(cc);

  // 需要連鎖
  root.append(el('h2', { class: 'section' }, '需要連鎖上の位置'));
  const dc = el('div', { class: 'card' });
  if (r.top_chain) dc.append(el('div', { class: 'chain', style: 'margin-bottom:10px' }, r.top_chain));
  dc.append(rankBars(r.trend_detail.map(t => ({ ...t, value: t.pressure })), {
    max: 100, labelKey: 'label', valueKey: 'value',
    fmtVal: (v) => v.toFixed(0),
    tipOf: (t) => `<b>${t.label}</b>（${t.depth}次需要）<br>この銘柄の露出度 ${(t.exposure * 100).toFixed(0)}%<br>`
      + `需要圧力 ${t.pressure}／未織り込みギャップ ${t.unpriced_gap >= 0 ? '+' : ''}${t.unpriced_gap}`,
    onClick: (t) => go(`#/trends/${t.node}`),
  }));
  if (r.sites.length) {
    dc.append(el('div', { style: 'margin-top:12px' },
      el('div', { class: 'muted', style: 'font-size:11px;letter-spacing:.1em;margin-bottom:5px' }, '関連拠点・現場'),
      el('div', { class: 'sites' }, r.sites.map(s => el('span', { class: 'site-chip' }, s)))));
  }
  root.append(dc);

  // 推移
  const series = (DB.series && DB.series[r.ticker]) || null;
  if (series && series.length > 1) {
    root.append(el('h2', { class: 'section' }, '最終推奨点の推移'));
    root.append(el('div', { class: 'card' },
      sparkline(series.map(s => s.v), { w: 640, h: 70 }),
      el('div', { class: 'muted', style: 'font-size:11px' },
        `${series[0].d} 〜 ${series.at(-1).d}（${series.length}営業日）`)));
  }

  // 財務詳細
  root.append(el('h2', { class: 'section' }, '主要指標'));
  const M = [
    ['ROE', `${r.f.roe.toFixed(1)}%`], ['ROIC', `${r.f.roic.toFixed(1)}%`],
    ['営業利益率', `${r.f.op_margin.toFixed(1)}%`], ['FCFマージン', `${r.f.fcf_margin.toFixed(1)}%`],
    ['売上3年CAGR', fmt.pct(r.f.rev_cagr3, 1)], ['EPS 3年CAGR', fmt.pct(r.f.eps_cagr3, 1)],
    ['FCF 3年CAGR', fmt.pct(r.f.fcf_cagr3, 1)], ['利益率トレンド', `${r.f.margin_trend >= 0 ? '+' : ''}${r.f.margin_trend.toFixed(1)}pt`],
    ['D/Eレシオ', `${r.f.de_ratio.toFixed(2)}倍`], ['ネット負債/EBITDA', `${r.f.net_debt_ebitda.toFixed(1)}倍`],
    ['流動比率', `${r.f.current_ratio.toFixed(2)}倍`], ['利払カバレッジ', `${r.f.interest_coverage.toFixed(0)}倍`],
    ['1M / 3M', `${fmt.pct(r.f.mom_1m, 0)} / ${fmt.pct(r.f.mom_3m, 0)}`],
    ['6M / 12M', `${fmt.pct(r.f.mom_6m, 0)} / ${fmt.pct(r.f.mom_12m, 0)}`],
    ['年率ボラティリティ', `${(r.f.vol_ann * 100).toFixed(0)}%`],
    ['52週高値からの距離', `${r.f.dist_52w_high.toFixed(0)}%`],
    ['経済的な堀（moat）', `${r.f.moat_score.toFixed(0)}/100`],
    ['ガバナンス', `${r.f.governance_score.toFixed(0)}/100`],
    ['資本配分', `${r.f.capital_allocation.toFixed(0)}/100`],
    ['IR・対話姿勢', `${r.f.ir_dialogue.toFixed(0)}/100`],
  ];
  const mk2 = el('dl', { class: 'kv', style: 'columns:2;column-gap:36px' });
  M.forEach(([k, v]) => { mk2.append(el('dt', {}, k)); mk2.append(el('dd', {}, v)); });
  root.append(el('div', { class: 'card' }, mk2));
  return root;
}

// ---------------------------------------------------------------- PORTFOLIO
const HOLD_KEY = 'value-radar-ai/holdings';
function loadHoldings() {
  try { return JSON.parse(localStorage.getItem(HOLD_KEY) || '{}'); } catch { return {}; }
}
function saveHoldings(h) {
  try { localStorage.setItem(HOLD_KEY, JSON.stringify(h)); } catch { /* 保存不可でも動作は継続 */ }
}

export function viewPortfolio() {
  const root = el('div', {});
  const rates = DB.meta.fx_rates_jpy;

  root.append(heroBand(
    'PORTFOLIO — DIVERSIFICATION CHECK',
    '予算に応じた分散案を、機械的に組み立てる。',
    'スコアとリスクで加重した配分案と、保有株の集中度・地域偏り・テーマ偏りを可視化します。'));
  root.append(el('h2', { class: 'section' }, '予算別ポートフォリオ提案'));
  root.append(el('div', { class: 'sub', style: 'margin-bottom:12px' },
    '上位30銘柄から、スコアとリスクで加重して単元制約に合わせて割り付けた案です。'
    + '端数を使い切るための追加購入はしません（現金を残すのも判断のうち）。'));

  const sel = el('select', { onchange: (e) => renderBudget(Number(e.target.value)) },
    DB.budgets.map(b => el('option', { value: b.budget }, fmt.man(b.budget))));
  root.append(el('div', { class: 'filters' }, el('label', {}, '予算 '), sel));

  const bHolder = el('div', {});
  root.append(bHolder);

  function renderBudget(budget) {
    const b = DB.budgets.find(x => x.budget === budget) || DB.budgets[0];
    bHolder.replaceChildren();
    const card = el('div', { class: 'card' });
    card.append(el('div', { style: 'display:flex;gap:18px;flex-wrap:wrap;margin-bottom:10px' },
      stat('予算', fmt.man(b.budget)), stat('投資額', fmt.man(b.invested)),
      stat('現金', `${fmt.man(b.cash)}（${(b.cash_ratio * 100).toFixed(0)}%）`),
      stat('銘柄数', `${b.names}銘柄`)));
    if (!b.positions.length) {
      card.append(el('div', { class: 'muted' }, b.note));
    } else {
      const t = el('table', { class: 'data' });
      t.append(el('thead', {}, el('tr', {},
        el('th', {}, '銘柄'), el('th', {}, 'セクター'), el('th', { class: 'num' }, '株価'),
        el('th', { class: 'num' }, '株数'), el('th', { class: 'num' }, '金額'),
        el('th', { class: 'num' }, '比率'), el('th', { class: 'num' }, '最終点'), el('th', {}, '判定'))));
      const tb = el('tbody', {});
      b.positions.forEach(p => tb.append(el('tr', { onclick: () => go(`#/stock/${encodeURIComponent(p.ticker)}`) },
        el('td', {}, el('div', {}, p.name), el('div', { class: 'muted', style: 'font-size:11px' }, p.ticker)),
        el('td', { class: 'muted' }, p.sector),
        el('td', { class: 'num' }, fmt.price(p.price, p.currency)),
        el('td', { class: 'num' }, fmt.n(p.shares)),
        el('td', { class: 'num' }, fmt.man(p.cost_jpy)),
        el('td', { class: 'num' }, `${(p.weight * 100).toFixed(1)}%`),
        el('td', { class: 'num' }, p.final_score.toFixed(1)),
        el('td', { class: 'verdict' }, p.verdict_label))));
      t.append(tb);
      card.append(el('div', { class: 'table-wrap' }, t));
      card.append(riskPanel(b.positions.map(p => ({
        row: DB.rows.find(r => r.ticker === p.ticker), weight: p.weight,
      })).filter(x => x.row)));
    }
    card.append(el('div', { class: 'muted', style: 'font-size:11.5px;margin-top:8px' }, b.note));
    bHolder.append(card);
  }
  renderBudget(DB.budgets[0].budget);

  // ---- 保有株のリスク分析 ----
  root.append(el('h2', { class: 'section' }, '保有株・候補株のリスク分析'));
  const hold = loadHoldings();
  const hc = el('div', { class: 'card' });

  const addSel = el('select', {}, el('option', { value: '' }, '銘柄を選択…'),
    DB.rows.map(r => el('option', { value: r.ticker }, `${r.name}（${r.ticker}）`)));
  const addQty = el('input', { type: 'number', min: '0', step: '1', placeholder: '株数', style: 'width:110px' });
  const addBtn = el('button', { class: 'iconbtn', onclick: () => {
    const t = addSel.value; const q = Number(addQty.value);
    if (!t || !(q > 0)) return;
    hold[t] = (hold[t] || 0) + q; saveHoldings(hold); renderHold();
  } }, '追加');
  hc.append(el('div', { class: 'filters' }, addSel, addQty, addBtn,
    el('button', { class: 'iconbtn', onclick: () => { for (const k in hold) delete hold[k]; saveHoldings(hold); renderHold(); } }, 'クリア')));

  const hBody = el('div', {});
  hc.append(hBody);
  root.append(hc);

  function renderHold() {
    hBody.replaceChildren();
    const items = Object.entries(hold).map(([t, q]) => {
      const row = DB.rows.find(r => r.ticker === t);
      if (!row) return null;
      return { row, qty: q, jpy: toJPY(row.price * q, row.currency, rates) };
    }).filter(Boolean);
    if (!items.length) {
      hBody.append(el('div', { class: 'muted', style: 'font-size:12.5px' },
        '保有銘柄を追加すると、集中度・リスク・需要テーマの偏りを分析します（この端末のブラウザ内にのみ保存されます）。'));
      return;
    }
    const total = items.reduce((s, x) => s + x.jpy, 0);
    const t = el('table', { class: 'data' });
    t.append(el('thead', {}, el('tr', {},
      el('th', {}, '銘柄'), el('th', { class: 'num' }, '株数'), el('th', { class: 'num' }, '評価額'),
      el('th', { class: 'num' }, '比率'), el('th', { class: 'num' }, '最終点'),
      el('th', {}, '判定'), el('th', {}, ''))));
    const tb = el('tbody', {});
    items.forEach(x => tb.append(el('tr', {},
      el('td', { onclick: () => go(`#/stock/${encodeURIComponent(x.row.ticker)}`) }, x.row.name),
      el('td', { class: 'num' }, fmt.n(x.qty)),
      el('td', { class: 'num' }, fmt.man(x.jpy)),
      el('td', { class: 'num' }, `${(x.jpy / total * 100).toFixed(1)}%`),
      el('td', { class: 'num' }, x.row.final_score.toFixed(1)),
      el('td', { class: `verdict v-${x.row.verdict}` }, x.row.verdict_label),
      el('td', {}, el('button', {
        class: 'iconbtn', onclick: (e) => { e.stopPropagation(); delete hold[x.row.ticker]; saveHoldings(hold); renderHold(); },
      }, '削除')))));
    t.append(tb);
    hBody.append(el('div', { class: 'table-wrap' }, t));
    hBody.append(riskPanel(items.map(x => ({ row: x.row, weight: x.jpy / total }))));
  }
  renderHold();
  return root;
}

function stat(label, value) {
  return el('div', {},
    el('div', { class: 'muted', style: 'font-size:10.5px;letter-spacing:.1em' }, label),
    el('div', { class: 'mono', style: 'font-size:17px;font-weight:700' }, value));
}

/** 加重集中度とリスクのパネル（提案・保有の両方で使う）。 */
function riskPanel(rawItems) {
  // ウェイトは「投資した金額の中での比率」に正規化する（現金分を除く）
  const tw = rawItems.reduce((s, x) => s + x.weight, 0) || 1;
  const items = rawItems.map(x => ({ ...x, weight: x.weight / tw }));
  const agg = (key) => {
    const m = {};
    items.forEach(x => { const k = typeof key === 'function' ? key(x.row) : x.row[key]; m[k] = (m[k] || 0) + x.weight; });
    return Object.entries(m).map(([k, v]) => ({ label: k, value: v * 100 })).sort((a, b) => b.value - a.value);
  };
  const nodeAgg = {};
  items.forEach(x => {
    const tot = Object.values(x.row.nodes).reduce((s, v) => s + v, 0) || 1;
    Object.entries(x.row.nodes).forEach(([n, w]) => {
      const lbl = (DB.nodes.find(z => z.id === n) || {}).label || n;
      nodeAgg[lbl] = (nodeAgg[lbl] || 0) + x.weight * (w / tot);
    });
  });
  const nodeRows = Object.entries(nodeAgg).map(([k, v]) => ({ label: k, value: v * 100 }))
    .sort((a, b) => b.value - a.value).slice(0, 8);

  const wRisk = items.reduce((s, x) => s + x.weight * x.row.risk_points, 0);
  const wVol = items.reduce((s, x) => s + x.weight * x.row.f.vol_ann, 0);
  const wScore = items.reduce((s, x) => s + x.weight * x.row.final_score, 0);
  const hhi = items.reduce((s, x) => s + x.weight ** 2, 0);
  const topNode = nodeRows[0];

  const warn = [];
  if (hhi > 0.30) warn.push(`銘柄集中度（HHI ${hhi.toFixed(2)}）が高く、実質的に少数銘柄への賭けになっています。`);
  if (topNode && topNode.value > 35) warn.push(`需要テーマ「${topNode.label}」への実効エクスポージャーが ${topNode.value.toFixed(0)}% です。AI関連は同一ショックで同時に下落しやすい点に注意。`);
  const jp = agg('region').find(r => r.label === 'JP');
  if (jp && jp.value > 70) warn.push('日本株比率が70%を超えており、世界分散の観点では通貨・地域が偏っています。');
  if (wVol > 0.42) warn.push(`加重平均ボラティリティが年率 ${(wVol * 100).toFixed(0)}% と高めです。`);

  return el('div', { style: 'margin-top:16px' },
    el('div', { style: 'display:flex;gap:18px;flex-wrap:wrap;margin-bottom:12px' },
      stat('加重最終点', wScore.toFixed(1)),
      stat('加重リスク減点', `−${wRisk.toFixed(1)}`),
      stat('加重ボラティリティ', `${(wVol * 100).toFixed(0)}%`),
      stat('銘柄集中度 HHI', hhi.toFixed(2))),
    el('div', { class: 'grid c3' },
      el('div', {}, el('div', { class: 'muted', style: 'font-size:11px;letter-spacing:.1em;margin-bottom:5px' }, '地域配分'),
        rankBars(agg('region'), { max: 100, fmtVal: (v) => `${v.toFixed(0)}%` })),
      el('div', {}, el('div', { class: 'muted', style: 'font-size:11px;letter-spacing:.1em;margin-bottom:5px' }, 'セクター配分'),
        rankBars(agg('sector').slice(0, 8), { max: 100, fmtVal: (v) => `${v.toFixed(0)}%` })),
      el('div', {}, el('div', { class: 'muted', style: 'font-size:11px;letter-spacing:.1em;margin-bottom:5px' }, '需要テーマ実効配分'),
        rankBars(nodeRows, { max: 100, fmtVal: (v) => `${v.toFixed(0)}%` }))),
    warn.length ? el('div', { class: 'notice', style: 'margin-top:12px' },
      el('strong', {}, '集中リスクの指摘　'), el('ul', { style: 'margin:4px 0 0;padding-left:18px' },
        warn.map(w => el('li', {}, w)))) : null);
}
