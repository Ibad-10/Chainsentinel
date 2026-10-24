// ChainSentinel frontend: plain JS + Cytoscape.js. Original code.
'use strict';
const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
const RM = matchMedia('(prefers-reduced-motion: reduce)');
const reduced = () => RM.matches;
const sleep = ms => new Promise(r => setTimeout(r, reduced() ? 0 : ms));

// ---------- icons (authored, 24px grid, 1.6 stroke) ----------
const IC = {
  mark: '<path d="M12 3l7.5 4.3v8.6L12 20.2 4.5 15.9V7.3z"/><path d="M12 8.2l3.3 1.9v3.8L12 15.8l-3.3-1.9v-3.8z"/>',
  grid: '<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="4" rx="1.5"/><rect x="13" y="10" width="7" height="10" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/>',
  search: '<circle cx="11" cy="11" r="6"/><path d="M20 20l-4.3-4.3"/>',
  layers: '<path d="M12 4l8 4-8 4-8-4z"/><path d="M4 12l8 4 8-4"/><path d="M4 16l8 4 8-4"/>',
  flask: '<path d="M10 4h4"/><path d="M10.5 4v5.2L5.6 17.6A1.6 1.6 0 007 20h10a1.6 1.6 0 001.4-2.4L13.5 9.2V4"/><path d="M7.8 14h8.4"/>',
  eye: '<path d="M2.8 12s3.4-6 9.2-6 9.2 6 9.2 6-3.4 6-9.2 6-9.2-6-9.2-6z"/><circle cx="12" cy="12" r="2.6"/>',
  book: '<path d="M5 5.5A1.5 1.5 0 016.5 4H19v13H6.5A1.5 1.5 0 005 18.5z"/><path d="M5 18.5A1.5 1.5 0 006.5 20H19"/><path d="M9 8h6"/>',
  arrow: '<path d="M5 12h14"/><path d="M13 6l6 6-6 6"/>',
  info: '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5"/><path d="M12 7.6v.2"/>',
  fit: '<path d="M4 9V5.5A1.5 1.5 0 015.5 4H9"/><path d="M15 4h3.5A1.5 1.5 0 0120 5.5V9"/><path d="M20 15v3.5a1.5 1.5 0 01-1.5 1.5H15"/><path d="M9 20H5.5A1.5 1.5 0 014 18.5V15"/>',
  expand: '<circle cx="12" cy="12" r="2.2"/><circle cx="5" cy="6" r="1.6"/><circle cx="19" cy="6" r="1.6"/><circle cx="5" cy="18" r="1.6"/><circle cx="19" cy="18" r="1.6"/><path d="M6.3 7l4 3.6M17.7 7l-4 3.6M6.3 17l4-3.6M17.7 17l-4-3.6"/>',
  tag: '<path d="M4 12.6V5.5A1.5 1.5 0 015.5 4h7.1L20 11.4a1.5 1.5 0 010 2.1l-6.5 6.5a1.5 1.5 0 01-2.1 0z"/><circle cx="8.5" cy="8.5" r="1.3"/>',
  flow: '<path d="M3 8h11"/><path d="M3 16h7"/><circle cx="18" cy="8" r="2"/><circle cx="14" cy="16" r="2"/>',
  clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
  play: '<path d="M8 5.5v13l10-6.5z"/>',
  lock: '<rect x="5" y="10.5" width="14" height="9.5" rx="2"/><path d="M8 10.5V8a4 4 0 018 0v2.5"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  refresh: '<path d="M19.5 12a7.5 7.5 0 01-13 5.1"/><path d="M4.5 12a7.5 7.5 0 0113-5.1"/><path d="M17.5 3.5v3.6h-3.6"/><path d="M6.5 20.5v-3.6h3.6"/>',
  x: '<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  chev: '<path d="M9.5 6l6 6-6 6"/>',
  ext: '<path d="M14 4h6v6"/><path d="M20 4l-9 9"/><path d="M18 14v4.5a1.5 1.5 0 01-1.5 1.5h-11A1.5 1.5 0 014 18.5v-11A1.5 1.5 0 015.5 6H10"/>',
  db: '<ellipse cx="12" cy="6" rx="7" ry="2.5"/><path d="M5 6v12c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5V6"/><path d="M5 12c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5"/>',
  graph: '<circle cx="6" cy="7" r="2"/><circle cx="18" cy="6" r="2"/><circle cx="12" cy="17" r="2.4"/><path d="M7.6 8.3l3.2 6.6M16.6 7.5l-3.4 7.4M8 7h8"/>',
  rules: '<path d="M9 6h11M9 12h11M9 18h11"/><path d="M4 6l1 1 2-2M4 12l1 1 2-2M4 18l1 1 2-2"/>',
  send: '<path d="M4 12l16-7-6.5 16-2.5-6.5z"/><path d="M11 14.5L20 5"/>',
  bars: '<path d="M5 20V11M10 20V5M15 20v-7M20 20v-4"/>',
  gavel: '<path d="M13.5 4.5l6 6"/><path d="M11 7l6 6"/><path d="M12.2 5.8l-4.6 4.6 6 6 4.6-4.6"/><path d="M10.6 13.4L4 20"/>',
  arrowr: '<path d="M5 12h14M14 7l5 5-5 5"/>',
};
const icon = (n, cls = 'i') => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${IC[n] || ''}</svg>`;
const hydrate = (root = document) => root.querySelectorAll('[data-i]').forEach(el => { el.outerHTML = icon(el.dataset.i); });

// ---------- helpers ----------
const COL = {self: '#7aa2ff', exploit: '#ef6461', ofac: '#e0457b', mixer: '#a08cf0', bridge: '#d9894a', exchange: '#cfccc3', dex: '#3fb5a6', unknown: '#5a5f68', cluster: '#2b2f36'};
const CATNAME = {self: 'Investigated', exploit: 'Exploit / hack', ofac: 'OFAC sanctioned', mixer: 'Mixer', bridge: 'Bridge / cross-chain', exchange: 'Exchange', dex: 'DEX', unknown: 'Unlabelled', cluster: 'Grouped wallets'};
const LBL = {violation: 'Violation', supported: 'Supported', insufficient_information: 'Insufficient info', inconsistent_context: 'Inconsistent'};
const LBLS = {violation: 'Violation', supported: 'Supported', insufficient_information: 'Insuff.', inconsistent_context: 'Incons.'};
const RULES = {R1: 'Sanctions exposure (OFAC)', R2: 'Mixer deposits', R3: 'Rapid pass-through', R4: 'Fan-out / splitting', R5: 'Peel chain', R6: 'Chain-hopping (bridge / swap)', R7: 'Round-trip / cycle', R8: 'Exploit proceeds'};
const short = a => a ? (a.length > 16 ? a.slice(0, 6) + '…' + a.slice(-4) : a) : '?';
const fmtT = ts => ts ? new Date(ts * 1000).toISOString().replace('T', ' ').slice(0, 16) : '';
const fmtN = (v, d = 2) => Number(v || 0).toLocaleString('en-GB', {maximumFractionDigits: d});
const pct = v => Math.round((v || 0) * 100) + '%';
const p2 = v => (v || 0).toFixed(2);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
async function api(path, opt) { const r = await fetch(path, opt); let j = {}; try { j = await r.json(); } catch (e) {} if (!r.ok) throw new Error(j.detail || r.statusText); return j; }
const kindTag = (synthetic, chain) => synthetic ? '<span class="tag syn">Synthetic</span>' : `<span class="tag real">Real ${esc((chain || '').toUpperCase())}</span>`;
const vpill = v => `<span class="vpill ${v}">${v}</span>`;
function miniBar(p) { return `<div class="mini">${['violation', 'insufficient_information', 'inconsistent_context', 'supported'].map(k => `<div class="f-${k}" style="width:${p[k] * 100}%"></div>`).join('')}</div>`; }
function showErr(el, msg) { el.innerHTML = icon('info') + `<span>${esc(msg)}</span>`; el.classList.add('show'); }
function hideErr(el) { el.classList.remove('show'); }
let SHOW = null, BATCH = null, WL = null, G = null, CUR = null, RUN = 0;

// ---------- routing ----------
function showTab(t) {
  $$('#nav button').forEach(b => b.classList.toggle('active', b.dataset.tab === t));
  $$('.view').forEach(s => s.classList.toggle('active', s.id === 'v-' + t));
  if (t === 'overview') loadOverview();
  if (t === 'batch' && !$('#col-FLAG').children.length) { if (BATCH) renderBatch(BATCH); else runBatch(); }
  if (t === 'lab' && !$('#labgrid').children.length) loadLab();
  if (t === 'watch') loadWatch();
  if (t === 'how' && !$('#howbody').children.length) loadHow();
  if (t === 'investigate' && G) requestAnimationFrame(() => G.cy.resize());
}
$$('#nav button').forEach(b => b.onclick = () => showTab(b.dataset.tab));
document.addEventListener('click', e => { const g = e.target.closest('[data-goto]'); if (g) showTab(g.dataset.goto); });

// ---------- graph ----------
function makeGraph(wrap, G0, opts = {}) {
  const cyEl = wrap.querySelector('.cy'), fx = wrap.querySelector('.fx'), tip = opts.tip;
  const unit = G0.unit || 'ETH';
  const maxV = Math.max(1e-9, ...G0.edges.map(e => e.native ? e.value : 0));
  const wOf = v => 1 + 7 * Math.sqrt(v / maxV);
  const nbr = {}; G0.edges.forEach(e => { (nbr[e.source] = nbr[e.source] || new Set()).add(e.target); (nbr[e.target] = nbr[e.target] || new Set()).add(e.source); });
  const nById = Object.fromEntries(G0.nodes.map(n => [n.id, n]));
  // key nodes get labels: the investigated wallet plus the top labelled counterparties
  const keyIds = new Set(G0.nodes.filter(n => n.is_self).map(n => n.id));
  G0.nodes.filter(n => !n.is_self && n.cat !== 'unknown').sort((a, b) => (b.score || 0) - (a.score || 0)).slice(0, opts.keyN || 8).forEach(n => keyIds.add(n.id));
  // collapse leaf wallets (unlabelled, one connection) that hang off the same hub in the same direction
  const groups = {};
  if (opts.cluster !== false) G0.nodes.forEach(n => {
    if (n.is_self || n.cat !== 'unknown' || keyIds.has(n.id) || !nbr[n.id] || nbr[n.id].size !== 1) return;
    const hub = [...nbr[n.id]][0]; const es = G0.edges.filter(e => e.source === n.id || e.target === n.id);
    const outV = es.filter(e => e.source === hub).length, dir = outV >= es.length - outV ? 'out' : 'in';
    const g = groups[hub + '|' + dir] = groups[hub + '|' + dir] || {hub, dir, members: [], edges: [], value: 0, count: 0, asset: unit};
    g.members.push(n.id); es.forEach(e => { g.edges.push(e.id); g.value += e.native ? e.value : 0; g.count += e.count; if (!e.native) g.asset = e.asset; });
  });
  const clusters = Object.values(groups).filter(g => g.members.length >= 4);
  const memberOf = {}; clusters.forEach((g, i) => { g.id = 'cl' + i; g.members.forEach(m => memberOf[m] = g.id); });
  const els = [];
  G0.nodes.forEach(n => {
    const cat = n.is_self ? 'self' : n.cat;
    const size = n.is_self ? 30 : (n.cat === 'unknown' ? 11 : 18);
    els.push({data: {id: n.id, lbl: n.label ? n.label.split(' [')[0].slice(0, 30) : short(n.id), cat, size, cl: memberOf[n.id] || ''}, classes: [keyIds.has(n.id) ? 'key' : '', memberOf[n.id] ? 'hid' : ''].join(' ')});
  });
  const edgeLbl = e => e.native ? `${fmtN(e.value)} ${e.asset}` : `${e.count}× ${e.asset}`;
  G0.edges.forEach(e => {
    const hid = memberOf[e.source] || memberOf[e.target];
    els.push({data: {id: e.id, source: e.source, target: e.target, w: e.native ? wOf(e.value) : 1, native: e.native ? 1 : 0, v: e.native ? e.value : 0, elbl: edgeLbl(e)}, classes: hid ? 'hid' : ''});
  });
  clusters.forEach(g => {
    els.push({data: {id: g.id, lbl: `${g.members.length} wallets`, cat: 'cluster', size: 26, members: g.members}, classes: 'key cluster'});
    const s = g.dir === 'out' ? g.hub : g.id, t = g.dir === 'out' ? g.id : g.hub;
    els.push({data: {id: g.id + 'e', source: s, target: t, w: g.value ? wOf(g.value) : 1.5, native: g.value ? 1 : 0, v: g.value, elbl: g.value ? `${fmtN(g.value)} ${unit} · ${g.members.length} flows` : `${g.count}× ${g.asset}`}, classes: 'cledge'});
  });
  const cy = cytoscape({container: cyEl, elements: els, minZoom: 0.15, maxZoom: 3.5, boxSelectionEnabled: false,
    style: [
      {selector: 'node', style: {'background-color': n => COL[n.data('cat')] || COL.unknown, width: 'data(size)', height: 'data(size)', label: '', 'border-width': 0,
        'font-family': 'Geist, sans-serif', 'font-size': 10.5, 'font-weight': 500, color: '#dedcd6', 'text-valign': 'bottom', 'text-margin-y': 6,
        'text-background-color': '#0c0d0f', 'text-background-opacity': 0.82, 'text-background-padding': 3, 'text-background-shape': 'roundrectangle', 'min-zoomed-font-size': 7,
        'transition-property': 'opacity, border-width', 'transition-duration': '0.25s'}},
      {selector: 'node.key, node.hover, node.hl, node.showlbl', style: {label: 'data(lbl)'}},
      {selector: 'node[cat="self"]', style: {'border-width': 2, 'border-color': '#edebe6', 'underlay-color': '#7aa2ff', 'underlay-opacity': 0.14, 'underlay-padding': 10, 'underlay-shape': 'ellipse', 'font-size': 12, 'font-weight': 600, color: '#fff'}},
      {selector: 'node.cluster', style: {shape: 'round-rectangle', width: n => 16 + n.data('lbl').length * 6.4, height: 20, 'text-valign': 'center', 'text-margin-y': 0, 'border-width': 1, 'border-color': '#454a53', color: '#bdbbb5', 'font-size': 10, 'text-background-opacity': 0, 'font-family': 'Geist Mono, monospace'}},
      {selector: 'edge', style: {width: 'data(w)', 'line-color': '#3a3e46', 'target-arrow-color': '#3a3e46', 'target-arrow-shape': 'triangle', 'arrow-scale': 0.6, 'curve-style': 'bezier', opacity: 0.6,
        'line-style': e => e.data('native') ? 'solid' : 'dashed', 'line-dash-pattern': [4, 4], 'font-family': 'Geist Mono, monospace', 'transition-property': 'opacity, line-color', 'transition-duration': '0.25s'}},
      {selector: 'edge.cledge', style: {'line-style': 'dashed', 'line-dash-pattern': [2, 3]}},
      {selector: 'edge.hl, edge.hover', style: {'line-color': '#7aa2ff', 'target-arrow-color': '#7aa2ff', opacity: 1, label: 'data(elbl)', 'font-size': 9.5, color: '#c3d4ff', 'text-background-color': '#0c0d0f', 'text-background-opacity': 0.9, 'text-background-padding': 2, 'z-index': 99, 'text-rotation': 'autorotate'}},
      {selector: 'node.hl', style: {'border-width': 2, 'border-color': '#7aa2ff'}},
      {selector: 'node.faded', style: {opacity: 0.16, 'text-opacity': 0}},
      {selector: 'edge.faded', style: {opacity: 0.06}},
      {selector: '.hid', style: {display: 'none'}},
    ].concat(opts.quiet ? [{selector: 'node.hl', style: {label: ''}}, {selector: 'edge.hl', style: {label: ''}}, {selector: 'node.key, node.hover', style: {label: 'data(lbl)'}}, {selector: 'edge.hover', style: {label: 'data(elbl)'}}] : [])});
  const api_ = {cy, clusters, flow: opts.flow !== false, ready: false, expanded: false};
  // layout, then grow every node out of the investigated wallet
  const vis = cy.elements().not('.hid');
  const nVis = vis.nodes().length;
  vis.layout(nVis > 34 ? {name: 'concentric', concentric: n => n.data('cat') === 'self' ? 10 : (n.hasClass('key') ? 6 : (n.hasClass('cluster') ? 5 : 1)), levelWidth: () => 1, minNodeSpacing: 22, spacingFactor: 1.05, animate: false}
                       : {name: 'cose', animate: false, randomize: false, nodeRepulsion: 140000, idealEdgeLength: 80, nodeOverlap: 24, gravity: 0.5, numIter: 2500, padding: 30}).run();
  cy.fit(vis, opts.pad || 50); if (cy.zoom() > (opts.maxFit || 1.5)) { cy.zoom(opts.maxFit || 1.5); cy.center(vis); }
  const self = cy.nodes('[cat="self"]');
  if (reduced() || opts.instant) { api_.ready = true; }
  else {
    const c = self.length ? {...self.position()} : {x: 0, y: 0};
    const nodes = vis.nodes().toArray().map(n => ({n, p: {...n.position()}})).sort((a, b) => Math.hypot(a.p.x - c.x, a.p.y - c.y) - Math.hypot(b.p.x - c.x, b.p.y - c.y));
    vis.edges().style('opacity', 0);
    nodes.forEach(({n}) => { n.position({x: c.x + (Math.random() - .5) * 8, y: c.y + (Math.random() - .5) * 8}); n.style('opacity', 0); });
    const step = Math.min(22, 900 / Math.max(1, nodes.length));
    nodes.forEach(({n, p}, i) => setTimeout(() => n.animate({position: p, style: {opacity: 1}}, {duration: 700, easing: 'ease-out-cubic', complete: () => n.removeStyle('opacity')}), i * step));
    setTimeout(() => { vis.edges().animate({style: {opacity: 0.6}}, {duration: 500, complete: () => { vis.edges().removeStyle('opacity'); api_.ready = true; }}); }, nodes.length * step + 300);
  }
  // hover + tooltip
  const showTip = (ev, html) => { if (!tip) return; const p = ev.renderedPosition; tip.innerHTML = html; tip.style.left = Math.min(p.x + 14, wrap.clientWidth - 310) + 'px'; tip.style.top = (p.y + 14) + 'px'; tip.classList.add('show'); };
  const hideTip = () => tip && tip.classList.remove('show');
  cy.on('mouseover', 'node', ev => { const n = ev.target; n.addClass('hover'); wrap.style.cursor = 'pointer';
    if (n.hasClass('cluster')) return showTip(ev, `<b>${n.data('members').length} grouped wallets</b><div class="muted small">Unlabelled leaf wallets with a single connection. Click to expand.</div>`);
    const d = nById[n.id()] || {}; showTip(ev, `<b>${esc(d.label || 'Unlabelled address')}</b><div class="small" style="color:${COL[n.data('cat')]}">${esc(CATNAME[n.data('cat')] || '')}</div><div class="mono">${esc(n.id())}</div>`); });
  cy.on('mouseout', 'node', ev => { ev.target.removeClass('hover'); wrap.style.cursor = ''; hideTip(); });
  cy.on('mouseover', 'edge', ev => { ev.target.addClass('hover'); showTip(ev, `<b>${esc(ev.target.data('elbl'))}</b><div class="mono">${esc(short(ev.target.data('source')))} → ${esc(short(ev.target.data('target')))}</div>`); });
  cy.on('mouseout', 'edge', ev => { ev.target.removeClass('hover'); hideTip(); });
  cy.on('tap', 'node.cluster', ev => api_.expand(ev.target.id()));
  if (opts.onNode) cy.on('tap', 'node', ev => { if (!ev.target.hasClass('cluster')) opts.onNode(ev.target.id()); });
  if (opts.onEdge) cy.on('tap', 'edge', ev => opts.onEdge(ev.target.id()));
  cy.on('tap', ev => { if (ev.target === cy) { api_.highlight([]); opts.onBlank && opts.onBlank(); } });

  api_.expand = (cid, quiet) => {
    const cn = cy.getElementById(cid); if (!cn.length || cn.hasClass('hid')) return;
    const ms = cy.collection(cn.data('members').map(m => cy.getElementById(m)));
    const p = cn.position(), R = 34 + ms.length * 2.6;
    const hub = cy.getElementById(clusters.find(g => g.id === cid).hub).position();
    const base = Math.atan2(p.y - hub.y, p.x - hub.x);
    ms.forEach((m, i) => { const a = base + (i - (ms.length - 1) / 2) * Math.min(0.35, 4.2 / ms.length); const tp = {x: p.x + Math.cos(a) * R, y: p.y + Math.sin(a) * R};
      m.removeClass('hid'); if (reduced() || quiet) m.position(tp); else { m.position(p); m.animate({position: tp}, {duration: 500, easing: 'ease-out-cubic'}); } });
    ms.connectedEdges().removeClass('hid'); cn.addClass('hid'); cn.connectedEdges().addClass('hid');
  };
  api_.collapse = () => { clusters.forEach(g => { g.members.forEach(m => { const n = cy.getElementById(m); n.addClass('hid'); n.connectedEdges().addClass('hid'); }); const cn = cy.getElementById(g.id); cn.removeClass('hid'); cn.connectedEdges().removeClass('hid'); }); };
  api_.toggleGroups = () => { api_.expanded = !api_.expanded; if (api_.expanded) clusters.forEach(g => api_.expand(g.id)); else api_.collapse(); setTimeout(() => api_.fit(), reduced() ? 0 : 520); return api_.expanded; };
  api_.fit = (eles) => {
    const bb = (eles || cy.elements().not('.hid')).boundingBox(), pad = opts.pad || 50, W = cy.width(), H = cy.height();
    if (!isFinite(bb.w) || !bb.w && !bb.h) return;
    const z = Math.min((W - 2 * pad) / Math.max(bb.w, 1), (H - 2 * pad) / Math.max(bb.h, 1), opts.maxFit || 1.5);
    const pan = {x: W / 2 - z * (bb.x1 + bb.w / 2), y: H / 2 - z * (bb.y1 + bb.h / 2)};
    cy.stop(); cy.animate({zoom: z, pan}, {duration: reduced() ? 0 : 450, easing: 'ease-out-cubic'});
  };
  api_.highlight = (edgeIds, nodeIds = [], fit = true, expand = true) => {
    cy.elements().removeClass('hl faded');
    if (!edgeIds || (!edgeIds.length && !nodeIds.length)) return;
    const need = new Set(); let es = cy.collection();
    edgeIds.forEach(id => { const e = cy.getElementById(id); if (e.length) { es.merge(e); [e.data('source'), e.data('target')].forEach(x => memberOf[x] && need.add(memberOf[x])); } });
    nodeIds.forEach(id => memberOf[id] && need.add(memberOf[id]));
    let ns = cy.collection();
    if (expand) need.forEach(cid => api_.expand(cid, true));
    else need.forEach(cid => { const cn = cy.getElementById(cid); if (!cn.hasClass('hid')) { ns.merge(cn); es.merge(cy.getElementById(cid + 'e')); } });
    es = es.filter(e => !e.hasClass('hid'));
    ns.merge(es.connectedNodes()); nodeIds.forEach(id => { const n = cy.getElementById(id); if (n.length && !n.hasClass('hid')) ns.merge(n); });
    cy.elements().not('.hid').addClass('faded'); es.removeClass('faded').addClass('hl'); ns.removeClass('faded').addClass('hl');
    if (fit && (es.length || ns.length)) api_.fit(es.union(ns));
  };
  api_.setLabels = on => cy.nodes().toggleClass('showlbl', on);
  // money-flow particles on a canvas overlay, count and size by value
  const ctx = fx.getContext('2d'); let raf = 0, alive = true; const seeds = {};
  const frame = now => {
    if (!alive) return; raf = requestAnimationFrame(frame);
    const w = wrap.clientWidth, h = wrap.clientHeight, dpr = devicePixelRatio || 1;
    if (fx.width !== Math.round(w * dpr) || fx.height !== Math.round(h * dpr)) { fx.width = Math.round(w * dpr); fx.height = Math.round(h * dpr); fx.style.width = w + 'px'; fx.style.height = h + 'px'; }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, w, h);
    if (!api_.flow || !api_.ready || reduced() || !wrap.offsetParent) return;
    const z = cy.zoom(), pan = cy.pan(), R = (p) => ({x: p.x * z + pan.x, y: p.y * z + pan.y});
    const anyHl = cy.$('edge.hl').length > 0;
    cy.edges().forEach(e => {
      if (e.hasClass('hid') || e.hasClass('faded') || (anyHl && !e.hasClass('hl')) || (opts.onlyHl && !e.hasClass('hl'))) return;
      const id = e.id(); const s = seeds[id] ?? (seeds[id] = Math.random());
      const a = R(e.sourceEndpoint()), b = R(e.targetEndpoint()); const cps = e.controlPoints(); const c = cps && cps.length ? R(cps[0]) : null;
      const len = Math.hypot(b.x - a.x, b.y - a.y); if (len < 6) return;
      const native = e.data('native'), rel = native ? Math.sqrt((e.data('v') || 0) / maxV) : 0;
      const n = native ? 1 + Math.round(3 * rel) : 1; const rad = (native ? 1.3 + 2.4 * rel : 1.1) * Math.max(0.7, Math.min(1.3, z));
      const period = Math.max(1100, Math.min(4200, len / (native ? 0.1 : 0.05)));
      const hl = e.hasClass('hl') || e.hasClass('hover');
      for (let i = 0; i < n; i++) {
        for (let k = 0; k < 3; k++) {
          const t = ((now / period) + s + i / n - k * 0.018 + 10) % 1; const u = 1 - t;
          const x = c ? u * u * a.x + 2 * u * t * c.x + t * t * b.x : a.x + (b.x - a.x) * t;
          const y = c ? u * u * a.y + 2 * u * t * c.y + t * t * b.y : a.y + (b.y - a.y) * t;
          const fade = Math.min(1, t * 6, (1 - t) * 6);
          ctx.globalAlpha = fade * (k === 0 ? (hl ? 0.95 : 0.7) : (hl ? 0.4 : 0.22) / k);
          ctx.fillStyle = hl ? '#a9c2ff' : (native ? '#edebe6' : '#8f9094');
          ctx.beginPath(); ctx.arc(x, y, rad * (k === 0 ? 1 : 0.75), 0, 6.283); ctx.fill();
        }
      }
    });
    ctx.globalAlpha = 1;
  };
  raf = requestAnimationFrame(frame);
  api_.destroy = () => { alive = false; cancelAnimationFrame(raf); ctx.clearRect(0, 0, fx.width, fx.height); cy.destroy(); };
  return api_;
}

// ---------- investigate: stepper ----------
const STEPS = [
  {t: 'Fetch transactions', i: 'db'}, {t: 'Build the graph', i: 'graph'}, {t: 'Rules fire', i: 'rules'},
  {t: 'Ask Sapling', i: 'send'}, {t: 'Probabilities', i: 'bars'}, {t: 'Apply cut-offs', i: 'gavel'}];
$('#steps').innerHTML = STEPS.map((s, i) => `<button class="step" data-k="${i}"><span class="n">${i + 1}</span><span class="t">${s.t}</span><span class="v">&nbsp;</span></button>`).join('');
const stepEl = i => $(`#steps .step[data-k="${i}"]`);
function stepState(i, st, val) { const el = stepEl(i); el.classList.remove('active', 'done'); if (st) el.classList.add(st); if (val !== undefined) el.querySelector('.v').innerHTML = val; }
function resetSteps() { STEPS.forEach((_, i) => { stepState(i, null, '&nbsp;'); stepEl(i).classList.remove('sel', 'vstep-FLAG', 'vstep-REVIEW', 'vstep-CLEAR'); }); }
function note(html, ic = 'info') { $('#stepnote').innerHTML = icon(ic) + `<span>${html}</span>`; }
function srcName(r) { return r.synthetic ? 'the synthetic generator' : (r.chain === 'btc' ? 'mempool.space' : 'Blockscout'); }
function cutExplain(r) {
  const p = r.sapling_full.probabilities, c = r.cutoffs;
  if (r.verdict === 'FLAG') return `P(violation) <b>${p2(p.violation)}</b> ≥ ${c.flag_violation}, so the verdict is <b class="c-FLAG">FLAG</b>.`;
  if (r.verdict === 'CLEAR') return `P(supported) <b>${p2(p.supported)}</b> ≥ ${c.clear_supported} and P(violation) <b>${p2(p.violation)}</b> &lt; ${c.clear_max_violation}, so the verdict is <b class="c-CLEAR">CLEAR</b>.`;
  return `P(violation) <b>${p2(p.violation)}</b> is below ${c.flag_violation} and ${p.supported >= c.clear_supported ? `P(violation) is not below ${c.clear_max_violation}` : `P(supported) <b>${p2(p.supported)}</b> is below ${c.clear_supported}`}, so neither threshold is met: <b class="c-REVIEW">REVIEW</b> by a human.`;
}
function stepNote(i, r) {
  const p = r.sapling_full.probabilities, nCl = G ? G.clusters.length : 0;
  return [
    `Pulled <b>${fmtN(r.n_tx, 0)}</b> value transfers from ${srcName(r)}${r.synthetic ? ' (random addresses, clearly labelled SYNTHETIC)' : (r.chain === 'eth' ? ': native, internal and token transfers, plus a second hop for the top recipients' : ', following the outputs hop by hop')}. Newest ones are in the timeline below.`,
    `Aggregated into <b>${r.graph.nodes.length}</b> addresses and <b>${r.graph.edges.length}</b> flows (hop 1–2, capped at 60 addresses). Edge thickness and particle size follow value${nCl ? `; <b>${nCl}</b> groups of single-link leaf wallets are collapsed` : ''}.`,
    r.rules.length ? `<b>${r.rules.length}</b> of 8 deterministic rules fired: ${r.rules.map(x => `<b>${x.id}</b> ${esc(x.name)}`).join(', ')}. Each cites the flows behind it, now highlighted.` : `No laundering rule fired.${r.lookalikes.length ? ` <b>${r.lookalikes.length}</b> look-alike guard${r.lookalikes.length > 1 ? 's' : ''} add mitigating context.` : ''}`,
    `Sent three texts to Banyan Sapling: the written AML <b>policy</b>, the <b>evidence</b> (on-chain facts plus the rule findings) and the <b>claim</b> “this wallet's activity is legitimate”. A second call sends the facts alone, for the counterfactual.`,
    `Sapling returned a probability for each of 4 labels: violation <b>${p2(p.violation)}</b>, supported <b>${p2(p.supported)}</b>, insufficient information <b>${p2(p.insufficient_information)}</b>, inconsistent context <b>${p2(p.inconsistent_context)}</b>${r.sapling_full.timing_ms ? `, in ${fmtN((r.sapling_full.timing_ms || {}).model || 0, 0)} ms` : ''}.`,
    cutExplain(r)][i];
}
function selectStep(i) {
  if (!CUR) return; const r = CUR;
  $$('#steps .step').forEach(s => s.classList.toggle('sel', +s.dataset.k === i));
  note(stepNote(i, r), STEPS[i].i);
  const flash = el => { if (!el) return; el.scrollIntoView({behavior: reduced() ? 'auto' : 'smooth', block: 'nearest'}); el.classList.remove('flash'); void el.offsetWidth; el.classList.add('flash'); setTimeout(() => el.classList.remove('flash'), 1400); };
  $$('.rule').forEach(x => x.classList.remove('on'));
  if (i === 0) { G.highlight([]); $('#timeline').scrollTop = 0; flash($('#tl')); flash($('#c-ent')); }
  if (i === 1) { G.highlight([]); G.fit(); const s = G.cy.nodes('[cat="self"]'); s.flashClass && s.flashClass('hl', 1200); }
  if (i === 2) { G.highlight(r.rules.flatMap(x => x.edges_in_graph), r.rules.flatMap(x => x.nodes), true, false); flash($('#c-rules')); }
  if (i === 3) { const d = $('#c-req details[data-k="ev"]'); if (d) d.open = true; flash($('#c-req')); }
  if (i === 4) { flash($('#c-verdict')); animateBars($('#c-verdict .bars'), r.sapling_full.probabilities, true); }
  if (i === 5) { flash($('#c-verdict')); const b = $('#c-verdict .bars'); b.classList.add('cutsflash'); setTimeout(() => b.classList.remove('cutsflash'), 1600); flash($('#c-verdict .rulebox')); }
}
$$('#steps .step').forEach(s => s.onclick = () => selectStep(+s.dataset.k));

// ---------- investigate: panel ----------
function barsHTML(p, cuts) {
  return `<div class="bars">${Object.keys(LBL).map(k => {
    let marks = '';
    if (cuts && k === 'violation') marks = `<i class="cut" style="left:${cuts.flag_violation * 100}%" data-l="FLAG ≥${cuts.flag_violation}"></i><i class="cut" style="left:${cuts.clear_max_violation * 100}%" data-l="&lt;${cuts.clear_max_violation}"></i>`;
    if (cuts && k === 'supported') marks = `<i class="cut" style="left:${cuts.clear_supported * 100}%" data-l="CLEAR ≥${cuts.clear_supported}"></i>`;
    return `<div class="bar" data-k="${k}"><span>${(cuts ? LBL : LBLS)[k]}</span><div class="t"><div class="f f-${k}" data-w="${(p[k] * 100).toFixed(1)}"></div>${marks}</div><span class="pct num">${pct(p[k])}</span></div>`;
  }).join('')}</div>`;
}
function animateBars(root, p, replay) {
  if (!root) return; const fs = root.querySelectorAll('.f');
  if (replay && !reduced()) { fs.forEach(f => { f.style.transition = 'none'; f.style.width = '0'; }); void root.offsetWidth; fs.forEach(f => f.style.transition = ''); }
  fs.forEach((f, i) => setTimeout(() => f.style.width = f.dataset.w + '%', reduced() ? 0 : 60 + i * 90));
}
function panelHTML(r) {
  const pf = r.sapling_full.probabilities, pp = r.sapling_facts.probabilities, c = r.cutoffs, req = r.sapling_full.request, st = r.stats;
  const lab = r.label && r.label.name ? `<span class="tag real" style="color:${COL[r.label.cat] || '#bdbbb5'}">${esc(CATNAME[r.label.cat] || r.label.cat)}</span><span>${esc(r.label.name)}</span><span class="muted small">${esc(r.label.src)}</span>` : '<span class="muted">No public label</span>';
  const raw = {status: r.sapling_full.status, raw_label: r.sapling_full.raw_label, prediction_set: r.sapling_full.prediction_set, probabilities: pf, timing_ms: r.sapling_full.timing_ms};
  const dv = pf.violation - pp.violation;
  return `
  <div class="card ent rise" id="c-ent"><h4>${kindTag(r.synthetic, r.chain)}<span class="r">${r.meta && r.meta.title ? esc(r.meta.title) : 'Entity'}</span></h4>
    <div class="addr">${esc(r.address)}</div><div class="lbl">${lab}</div>
    <div class="io"><div><span>Received · ${fmtN(st.n_in, 0)} tx</span><b>${fmtN(st.tin)} ${r.graph.unit}</b></div><div><span>Sent · ${fmtN(st.n_out, 0)} tx</span><b>${fmtN(st.tout)} ${r.graph.unit}</b></div></div></div>
  <div class="card rise" id="c-verdict"><h4>Verdict<span class="r">${r.meta && r.meta.expected ? 'expected: ' + esc(r.meta.expected) : ''}</span></h4>
    <div class="verdict"><div class="word c-${r.verdict}">${[...r.verdict].map((ch, i) => `<span style="transition-delay:${i * 45}ms">${ch}</span>`).join('')}</div>
      <div class="sub">Sapling status <b>${esc(r.sapling_full.status)}</b><br>top label <b>${esc(r.sapling_full.raw_label)}</b> · ${(r.sapling_full.prediction_set || []).length}-label conformal set${r.sapling_full.timing_ms ? ` · ${fmtN((r.sapling_full.timing_ms || {}).model || 0, 0)} ms` : ''}</div></div>
    <div style="height:8px"></div>${barsHTML(pf, c)}
    <div class="rulebox"><div class="${r.verdict === 'FLAG' ? 'hit c-FLAG' : ''}">FLAG if P(violation) ≥ ${c.flag_violation}</div><div class="${r.verdict === 'CLEAR' ? 'hit c-CLEAR' : ''}">CLEAR if P(supported) ≥ ${c.clear_supported} and P(violation) &lt; ${c.clear_max_violation}</div><div class="${r.verdict === 'REVIEW' ? 'hit c-REVIEW' : ''}">otherwise REVIEW</div></div></div>
  <div class="card rise" id="c-why"><h4>Why</h4><div class="why">${esc(r.why)}</div></div>
  <div class="card rise" id="c-rules"><h4>Rules fired<span class="r">${r.rules.length} of 8 · click to trace</span></h4>
    ${r.rules.map((x, i) => `<div class="rule" data-r="${i}"><span class="code">${x.id}</span><span class="nm">${esc(x.name)}</span><span class="dt">${esc(x.detail)}</span><span class="ev">${icon('graph')}${x.edges_in_graph.length} flow${x.edges_in_graph.length === 1 ? '' : 's'} on the graph${x.edges.length > x.edges_in_graph.length ? ` · ${x.edges.length - x.edges_in_graph.length} more outside the capped view` : ''}</span></div>`).join('') || '<div class="muted small" style="padding:4px 0 8px">No laundering rule fired.</div>'}
    ${r.lookalikes.map(l => `<div class="rule look"><span class="code">LA</span><span class="nm">Look-alike guard</span><span class="dt">${esc(l)}</span></div>`).join('')}</div>
  <div class="card rise" id="c-cf"><h4>Counterfactual<span class="r">what do the rules add?</span></h4>
    <div class="cf"><div><div class="hd"><span>Facts only</span>${vpill(r.verdict_facts)}</div>${barsHTML(pp)}</div><div><div class="hd"><span>Facts + findings</span>${vpill(r.verdict)}</div>${barsHTML(pf)}</div></div>
    <div class="arrow">${icon('arrowr')}<span>Same policy, claim and on-chain facts. Adding the rule findings moved P(violation) from <b>${p2(pp.violation)}</b> to <b>${p2(pf.violation)}</b>${Math.abs(dv) < 0.05 ? ' (little change)' : ''}.</span></div></div>
  <div class="card rise" id="c-req"><h4>Exactly what Sapling saw<span class="r">one call, no chat</span></h4>
    <details data-k="claim"><summary>${icon('chev')}Claim<span class="r">${req.claim.length} chars</span></summary><pre>${esc(req.claim)}</pre></details>
    <details data-k="ev"><summary>${icon('chev')}Evidence: facts + findings<span class="r">${req.evidence.length} chars</span></summary><pre>${esc(req.evidence)}</pre></details>
    <details data-k="evf"><summary>${icon('chev')}Evidence: facts only<span class="r">${r.sapling_facts.request.evidence.length} chars</span></summary><pre>${esc(r.sapling_facts.request.evidence)}</pre></details>
    <details data-k="pol"><summary>${icon('chev')}Policy<span class="r">${req.policy.length} chars</span></summary><pre>${esc(req.policy)}</pre></details>
    <details data-k="raw"><summary>${icon('chev')}Raw Sapling response<span class="r">JSON</span></summary><pre>${esc(JSON.stringify(raw, null, 1))}</pre></details></div>
  <div class="card nodeinfo rise" id="nodeinfo"><h4>Selected address</h4><div class="muted small">Click a node on the graph, or a grouped-wallets pill to expand it.</div></div>`;
}
const rise = sel => { const el = typeof sel === 'string' ? $(sel) : sel; if (el) requestAnimationFrame(() => el.classList.add('in')); };

async function investigate(addr, synthetic, o = {}) {
  showTab('investigate'); hideErr($('#ierr'));
  const run = ++RUN; CUR = null;
  if (G) { G.destroy(); G = null; }
  resetSteps(); stepState(0, 'active', synthetic ? 'Generating…' : 'Fetching…');
  note(synthetic ? 'Generating the synthetic transactions…' : `Fetching transactions for <span class="mono">${esc(short(addr))}</span> from ${addr && !addr.startsWith('0x') ? 'mempool.space' : 'Blockscout'} (cached when available)…`, 'db');
  $('#gwrap').classList.add('loading'); $('#gempty').hidden = false; $('#gempty h3').textContent = 'Running the pipeline'; $('#gempty p').textContent = 'Fetching transactions, building the flow graph, running the rules and asking Sapling.';
  ['#ghdr', '#gtools', '#legend'].forEach(s => $(s).hidden = true);
  $('#panel').innerHTML = ['92px', '260px', '120px', '180px'].map(h => `<div class="skel" style="height:${h}"></div>`).join('');
  $('#timeline').innerHTML = ''; $('#tlcount').textContent = '';
  if (!synthetic) $('#addr').value = addr;
  let r;
  try { r = synthetic ? await api('/api/synthetic/' + synthetic) : await api('/api/analyze?address=' + encodeURIComponent(addr) + ($('#refresh').checked ? '&refresh=true' : '')); }
  catch (e) {
    if (run !== RUN) return;
    resetSteps(); $('#gwrap').classList.remove('loading'); $('#gempty h3').textContent = 'Could not investigate this input'; $('#gempty p').textContent = e.message;
    $('#panel').innerHTML = ''; showErr($('#ierr'), e.message); note('Nothing was sent anywhere. Fix the input and try again.', 'info'); return;
  }
  if (run !== RUN) return;
  history.replaceState(null, '', synthetic ? `?s=${synthetic}` : `?a=${encodeURIComponent(addr)}`);
  await pipeline(r, run, o);
}
async function pipeline(r, run, o) {
  CUR = r; const live = () => run === RUN;
  $('#panel').innerHTML = panelHTML(r);
  $$('#panel .rule[data-r]').forEach(el => el.onclick = () => { $$('.rule').forEach(x => x.classList.remove('on')); el.classList.add('on'); const x = r.rules[+el.dataset.r]; G.highlight(x.edges_in_graph, x.nodes); note(`<b>${x.id} ${esc(x.name)}</b>: ${esc(x.detail)}`, 'rules'); });
  // 1 fetch
  stepState(0, 'done', `${fmtN(r.n_tx, 0)} transfers · ${srcName(r).replace('the synthetic generator', 'generator')}`); note(stepNote(0, r), 'db');
  renderTimeline(r); rise('#c-ent');
  await sleep(380); if (!live()) return;
  // 2 graph
  stepState(1, 'active', 'Laying out…');
  $('#gwrap').classList.remove('loading'); $('#gempty').hidden = true;
  G = makeGraph($('#gwrap'), r.graph, {tip: $('#tip'), onEdge: id => G.highlight([id]), onNode: id => nodeInfo(id)});
  graphChrome(r);
  await sleep(650); if (!live()) return;
  stepState(1, 'done', `${r.graph.nodes.length} addresses · ${r.graph.edges.length} flows`); note(stepNote(1, r), 'graph');
  await sleep(600); if (!live()) return;
  // 3 rules
  stepState(2, 'active', 'Running R1–R8…'); await sleep(320); if (!live()) return;
  stepState(2, 'done', r.rules.length ? `${r.rules.length} fired · ${r.rules.map(x => x.id).join(' ')}` : (r.lookalikes.length ? `none · ${r.lookalikes.length} look-alike` : 'none fired'));
  note(stepNote(2, r), 'rules'); rise('#c-rules');
  if (r.rules.length && !reduced()) { setTimeout(() => live() && G && G.highlight(r.rules.flatMap(x => x.edges_in_graph), r.rules.flatMap(x => x.nodes), false, false), 700); }
  await sleep(900); if (!live()) return;
  // 4 sapling
  stepState(3, 'active', 'policy · evidence · claim'); rise('#c-req'); note(stepNote(3, r), 'send');
  await sleep(700); if (!live()) return;
  stepState(3, 'done', '2 calls · facts / + findings');
  // 5 probabilities
  stepState(4, 'active'); rise('#c-verdict'); animateBars($('#c-verdict .bars'), r.sapling_full.probabilities);
  await sleep(500); if (!live()) return;
  stepState(4, 'done', `P(violation) ${p2(r.sapling_full.probabilities.violation)}`); note(stepNote(4, r), 'bars');
  await sleep(650); if (!live()) return;
  // 6 verdict
  stepState(5, 'done', r.verdict); stepEl(5).classList.add('vstep-' + r.verdict);
  $('#c-verdict .verdict').classList.add('in'); note(stepNote(5, r), 'gavel');
  for (const id of ['#c-why', '#c-cf', '#nodeinfo']) { rise(id); await sleep(90); }
  $$('#c-cf .bars').forEach((b, i) => animateBars(b, i ? r.sapling_full.probabilities : r.sapling_facts.probabilities));
  if (!live()) return;
  if (o.rule !== undefined) { setTimeout(() => { const el = typeof o.rule === 'number' ? $(`#panel .rule[data-r="${o.rule}"]`) : $$('#panel .rule[data-r]').find(e => e.querySelector('.code').textContent === o.rule); if (el) el.click(); }, reduced() ? 0 : 500); }
  else if (r.rules.length) setTimeout(() => live() && G && !$('.rule.on') && G.highlight([]), 1400);
}
function graphChrome(r) {
  $('#ghdr').hidden = false; $('#gtools').hidden = false; $('#legend').hidden = false;
  $('#ghdr').innerHTML = `${kindTag(r.synthetic, r.chain)}<span>${fmtN(r.n_tx, 0)} transfers · ${r.graph.nodes.length} addresses · ${r.graph.edges.length} flows · hop 1–2</span>`;
  const cats = new Set(r.graph.nodes.map(n => n.is_self ? 'self' : n.cat)); if (G.clusters.length) cats.add('cluster');
  $('#legend').innerHTML = Object.keys(COL).filter(k => cats.has(k)).map(k => `<span><i style="background:${COL[k]};${k === 'cluster' ? 'border-radius:3px;border:1px solid #454a53' : ''}"></i>${CATNAME[k]}</span>`).join('') + '<span class="muted">· edge width = value</span>';
  $('#t-exp').hidden = !G.clusters.length; $('#t-exp span:last-child').textContent = 'Expand groups';
  $('#t-lbl').classList.remove('on'); $('#t-flow').classList.toggle('on', G.flow);
}
$('#t-fit').onclick = () => G && G.fit();
$('#t-exp').onclick = () => { if (!G) return; const on = G.toggleGroups(); $('#t-exp span:last-child').textContent = on ? 'Collapse groups' : 'Expand groups'; };
$('#t-lbl').onclick = () => { if (!G) return; const on = !$('#t-lbl').classList.contains('on'); $('#t-lbl').classList.toggle('on', on); G.setLabels(on); };
$('#t-flow').onclick = () => { if (!G) return; G.flow = !G.flow; $('#t-flow').classList.toggle('on', G.flow); };
function renderTimeline(r) {
  const tl = r.timeline.slice().reverse().slice(0, 300), w = r.address;
  $('#tlcount').textContent = `${r.timeline.length} most recent value transfers · click a row to find it on the graph`;
  const nb = Object.fromEntries(r.graph.nodes.map(n => [n.id, n]));
  $('#timeline').innerHTML = tl.map((t, i) => {
    const dir = t.hop === 2 ? 'h2' : (t.frm === w ? 'out' : 'in'); const cp = dir === 'in' ? t.frm : t.to; const n = nb[cp];
    return `<div class="tr" data-i="${i}"><span class="muted num">${fmtT(t.ts)}</span><span class="d ${dir}">${dir === 'h2' ? 'HOP 2' : dir.toUpperCase()}</span><span class="amt">${fmtN(t.value, 4)} ${esc(t.asset)}</span><span class="cp">${esc(n && n.label ? n.label : short(cp))}</span><span class="mono muted">${esc(String(t.hash).slice(0, 10))}</span></div>`;
  }).join('') || '<div class="empty">No value transfers.</div>';
  $$('#timeline .tr').forEach(el => el.onclick = () => { if (!G) return; const t = tl[+el.dataset.i]; const k = t.asset === 'ETH' || t.asset === 'BTC' ? 'native' : t.asset; G.highlight([`${t.frm}->${t.to}:${k}`], [t.frm, t.to]); });
}
function nodeInfo(id) {
  const n = CUR.graph.nodes.find(x => x.id === id); if (!n) return;
  const es = CUR.graph.edges.filter(e => e.source === id || e.target === id);
  G.highlight(es.map(e => e.id), [id]);
  const cat = n.is_self ? 'self' : n.cat;
  const ex = CUR.chain === 'btc' ? `https://mempool.space/address/${id}` : `https://eth.blockscout.com/address/${id}`;
  $('#nodeinfo').innerHTML = `<h4>Selected address<span class="r" style="color:${COL[cat]}">${CATNAME[cat]}</span></h4><div class="addr mono small" style="word-break:break-all">${esc(id)}</div>
   <div style="margin:6px 0 8px;font-size:13px">${esc(n.label || 'No public label')} <span class="muted small">${esc(n.src || '')}</span></div>
   ${es.slice(0, 12).map(e => `<div class="rowx"><span>${e.source === id ? 'to ' + esc(short(e.target)) : 'from ' + esc(short(e.source))}</span><span class="num">${fmtN(e.value, 3)} ${esc(e.asset)} · ${e.count} tx · ${fmtT(e.first).slice(0, 10)}</span></div>`).join('')}
   ${es.length > 12 ? `<div class="muted small">+${es.length - 12} more flows</div>` : ''}
   <div class="links">${CUR.synthetic ? '<span class="tag syn">Synthetic address</span>' : `<a class="btn sm" href="${ex}" target="_blank" rel="noopener">${icon('ext')}Explorer</a> ${n.is_self ? '' : `<button class="btn sm" data-inv="${esc(id)}">${icon('search')}Investigate this address</button>`}`}</div>`;
  const b = $('#nodeinfo [data-inv]'); if (b) b.onclick = () => investigate(b.dataset.inv);
  $('#nodeinfo').scrollIntoView({behavior: reduced() ? 'auto' : 'smooth', block: 'nearest'});
}
$('#go').onclick = () => { const a = $('#addr').value.trim(); if (!a) { showErr($('#ierr'), 'Paste a public Ethereum (0x…) or Bitcoin address first.'); return; } investigate(a); };
$('#addr').onkeydown = e => { if (e.key === 'Enter') $('#go').click(); };

// ---------- batch ----------
async function getBatch() { if (!BATCH) { const t0 = performance.now(); BATCH = await api('/api/batch'); BATCH.secs = (performance.now() - t0) / 1000; } return BATCH; }
const okExp = it => (it.expected === 'violation' && it.verdict === 'FLAG') || (it.expected === 'supported' && it.verdict === 'CLEAR');
async function runBatch() {
  const btn = $('#runbatch'); btn.disabled = true; $('#batchinfo').textContent = 'Running real and synthetic cases through the rules and Sapling…';
  ['FLAG', 'REVIEW', 'CLEAR'].forEach(k => { $('#col-' + k).innerHTML = '<div class="skel" style="height:120px;margin-bottom:10px"></div><div class="skel" style="height:120px"></div>'; $('#n-' + k).textContent = ''; });
  try { BATCH = null; renderBatch(await getBatch()); } catch (e) { $('#batchinfo').textContent = 'Batch failed: ' + e.message; }
  btn.disabled = false;
}
function renderBatch(b) {
  ['FLAG', 'REVIEW', 'CLEAR'].forEach(k => $('#col-' + k).innerHTML = '');
  b.items.forEach((it, i) => {
    const d = document.createElement('div'); d.className = 'bcard rise';
    d.innerHTML = `<div class="top">${kindTag(it.kind === 'SYNTHETIC', it.chain)}<span class="ok ${okExp(it) ? 'y' : ''}">${okExp(it) ? icon('check') + 'as expected' : 'expected ' + esc(it.expected)}</span></div>
      <div class="nm">${esc(it.title)}</div><div class="ad">${esc(it.kind === 'SYNTHETIC' ? 'synthetic · ' + short(it.address) : short(it.address))}</div>
      <div class="rl">${(it.rules || []).map(x => `<span class="rc" title="${esc(RULES[x] || '')}">${x}</span>`).join('') || '<span class="muted small">no rules fired</span>'}</div>
      ${it.p ? miniBar(it.p) + `<div class="pp"><span>P(violation) ${pct(it.p.violation)}</span><span>P(supported) ${pct(it.p.supported)}</span><span>facts only: ${it.verdict_facts}</span></div>` : `<div class="c-FLAG small">${esc(it.error)}</div>`}`;
    d.onclick = () => it.kind === 'REAL' ? investigate(it.address) : investigate(null, it.case);
    $('#col-' + it.verdict).appendChild(d); setTimeout(() => rise(d), reduced() ? 0 : i * 45);
  });
  const n = k => b.items.filter(i => i.verdict === k).length;
  ['FLAG', 'REVIEW', 'CLEAR'].forEach(k => $('#n-' + k).textContent = n(k));
  const real = b.items.filter(i => i.kind === 'REAL').length;
  $('#batchinfo').innerHTML = `<span>${b.items.length} wallets · ${real} real, ${b.items.length - real} synthetic · ${b.secs ? (b.secs < 0.1 ? 'under 0.1 s (cached)' : b.secs.toFixed(1) + ' s') : ''}</span>`;
}
$('#runbatch').onclick = runBatch;

// ---------- overview ----------
async function loadOverview() {
  let b; try { b = await getBatch(); } catch (e) { $('#ov-screened').innerHTML = `<div class="empty">Could not load the batch: ${esc(e.message)}</div>`; return; }
  const w = WL || await api('/api/watchlist').catch(() => ({items: [], alerts: []})); WL = w;
  const seen = new Set(b.items.map(i => (i.address || '').toLowerCase()));
  const extra = w.items.filter(i => !seen.has(i.address.toLowerCase()));
  const all = b.items.map(i => i.verdict).concat(extra.map(i => i.last_verdict).filter(Boolean));
  const cnt = k => all.filter(v => v === k).length, N = all.length;
  const real = b.items.filter(i => i.kind === 'REAL').length, ok = b.items.filter(okExp).length;
  $('#ov-screened').innerHTML = `<div class="big"><b class="num">${N}</b><span>wallets screened</span></div>
    <div class="seg">${['FLAG', 'REVIEW', 'CLEAR'].map((k, i) => cnt(k) ? `<i class="${k}" style="flex:${cnt(k)};animation-delay:${i * 120}ms"></i>` : '').join('')}</div>
    <div class="segleg">${[['FLAG', 'Flagged', 'P(violation) ≥ 0.60'], ['REVIEW', 'Needs review', 'model will not commit'], ['CLEAR', 'Cleared', 'supported, low violation']].map(([k, t, s]) => `<div><b class="num c-${k}">${cnt(k)}</b><span>${t}</span><span class="muted small">${s}</span></div>`).join('')}</div>
    <div class="foot"><span><b>${real}</b> real wallets (ETH + BTC)</span><span><b>${b.items.length - real}</b> synthetic shapes</span><span><b>${extra.length}</b> extra on the watchlist</span><span><b>${ok}</b> of ${b.items.length} match the expected outcome</span></div>`;
  // typology breakdown
  const tc = Object.keys(RULES).map(id => ({id, r: b.items.filter(i => i.kind === 'REAL' && (i.rules || []).includes(id)).length, s: b.items.filter(i => i.kind === 'SYNTHETIC' && (i.rules || []).includes(id)).length}));
  const mx = Math.max(1, ...tc.map(t => t.r + t.s));
  $('#ov-typo').innerHTML = `<div class="tlegend"><span><i style="background:var(--acc)"></i>real</span><span><i style="background:repeating-linear-gradient(135deg,#b9a6ffaa 0 3px,#b9a6ff44 3px 6px)"></i>synthetic</span></div>` +
    tc.map((t, i) => `<div class="trow" data-rule="${t.id}" title="Open a wallet where ${t.id} fired"><span class="rc">${t.id}</span><span class="tname">${RULES[t.id]}</span><div class="tb">${t.r ? `<i class="r" style="width:${t.r / mx * 100}%;animation-delay:${i * 50}ms"></i>` : ''}${t.s ? `<i class="s" style="width:${t.s / mx * 100}%;animation-delay:${i * 50 + 80}ms"></i>` : ''}</div><b>${t.r + t.s}</b></div>`).join('');
  $$('#ov-typo .trow').forEach(el => el.onclick = () => { const id = el.dataset.rule; const it = b.items.find(i => i.kind === 'REAL' && (i.rules || []).includes(id)) || b.items.find(i => (i.rules || []).includes(id)); if (it) it.kind === 'REAL' ? investigate(it.address, null, {rule: id}) : investigate(null, it.case, {rule: id}); });
  // examples
  const row = (it) => `<div class="exrow" ${it.kind === 'REAL' ? `data-a="${esc(it.address)}"` : `data-s="${esc(it.case)}"`}>${kindTag(it.kind === 'SYNTHETIC', it.chain)}<span class="tt">${esc(it.title)}<small>${esc(it.kind === 'SYNTHETIC' ? 'generated · random addresses' : short(it.address))}</small></span><span class="rules">${(it.rules || []).map(x => `<span class="rc">${x}</span>`).join('')}</span>${vpill(it.verdict)}${icon('chev', 'i go')}</div>`;
  $('#ov-ex').innerHTML = `<div class="exgroup"><h4>Real wallets · live public chain data</h4>${b.items.filter(i => i.kind === 'REAL').map(row).join('')}</div><div class="exgroup"><h4>Synthetic shapes · generated, no real wallets</h4>${b.items.filter(i => i.kind === 'SYNTHETIC').map(row).join('')}</div>`;
  $$('#ov-ex .exrow').forEach(el => el.onclick = () => el.dataset.a ? investigate(el.dataset.a) : investigate(null, el.dataset.s));
  renderAlerts($('#ov-alerts'), w.alerts.slice(0, 5));
  $('#ov-wn').textContent = `${w.items.length} watched`;
}
function renderAlerts(el, alerts) {
  el.innerHTML = alerts.map(a => `<div class="arow"><span class="trn">${vpill(a.frm || '…')}${icon('arrowr')}${vpill(a.to)}${a.simulated ? '<span class="tag sim">Simulated</span>' : ''}</span><span class="meta num">${fmtT(a.ts)}</span><span class="mono small muted" style="grid-column:1/-1">${esc(a.chain.toUpperCase())} · ${esc(short(a.address))}</span><p>${esc(a.text)}</p></div>`).join('') || '<div class="empty">No alerts yet. On the Watchlist, try “Simulate suspicious tx” on a watched Ethereum wallet.</div>';
}

// ---------- pattern lab ----------
async function loadLab() {
  for (const s of SHOW.synthetic) {
    const d = document.createElement('div'); d.className = 'panel lab rise';
    d.innerHTML = `<header><span class="tag syn">Synthetic</span><h3>${esc(s.title)}</h3><span class="muted small" style="margin-left:auto">expected: ${esc(s.expected)}</span></header>
      <div class="gwrap"><div class="cy"></div><canvas class="fx"></canvas></div><div class="res"><div class="skel" style="height:70px"></div></div>`;
    $('#labgrid').appendChild(d); rise(d);
    api('/api/synthetic/' + s.case).then(r => {
      const g = makeGraph(d.querySelector('.gwrap'), r.graph, {cluster: false, pad: 22, keyN: 3, instant: false, quiet: true});
      const all = r.rules.flatMap(x => x.edges_in_graph); setTimeout(() => g.highlight(all, [], false), reduced() ? 0 : 1400);
      const pf = r.sapling_full.probabilities, pp = r.sapling_facts.probabilities;
      d.querySelector('.res').innerHTML = `<div class="row">${vpill(r.verdict)}${r.rules.map(x => `<span class="rc" title="${esc(x.detail)}">${x.id} · ${esc(x.name)}</span>`).join('') || '<span class="muted small">no rules fired</span>'}</div>
        ${miniBar(pf)}<p>P(violation) <b>${pct(pf.violation)}</b> with findings vs <b>${pct(pp.violation)}</b> on facts only (${r.verdict_facts}) · P(supported) ${pct(pf.supported)}</p>
        <button class="btn sm open">Open full investigation${icon('arrow')}</button>`;
      d.querySelector('.open').onclick = () => investigate(null, s.case);
    }).catch(e => d.querySelector('.res').textContent = e.message);
  }
}

// ---------- watchlist ----------
function renderWatch(w) {
  WL = w; $('#wcount').textContent = w.items.length || '';
  $('#wtable').innerHTML = `<tr><th>Address</th><th>Verdict</th><th>Rules</th><th>Last check</th><th></th></tr>` + (w.items.map(it => `<tr>
    <td><span class="tag real">${esc(it.chain.toUpperCase())}</span> <span class="mono">${esc(short(it.address))}</span>${it.injected ? ' <span class="tag sim">Simulated tx injected</span>' : ''}<div class="muted small" style="margin-top:4px">${esc(it.label || 'No public label')}</div></td>
    <td>${it.last_verdict ? vpill(it.last_verdict) : '…'}${it.p ? `<div class="muted small num" style="margin-top:4px">P(v) ${pct(it.p.violation)}</div>` : ''}</td>
    <td class="nowrap">${(it.rules || []).map(x => `<span class="rc">${x}</span>`).join('') || '<span class="muted small">none</span>'}</td>
    <td class="muted small num nowrap">${fmtT(it.last_check).slice(5)}</td>
    <td><div class="acts"><button class="btn sm" data-act="open" data-a="${esc(it.address)}">Open</button>${it.chain === 'eth' ? `<button class="btn sm" data-act="sim" data-a="${esc(it.address)}" title="Demo mode: inject a SYNTHETIC Tornado Cash deposit">Simulate suspicious tx</button>` : ''}${it.injected ? `<button class="btn sm" data-act="reset" data-a="${esc(it.address)}">Reset</button>` : ''}<button class="btn sm ghost" data-act="del" data-a="${esc(it.address)}" title="Stop watching" aria-label="Stop watching">${icon('x')}</button></div></td></tr>`).join('') || '<tr><td colspan="5" class="empty">Nothing watched yet. Add a public address above.</td></tr>');
  renderAlerts($('#alerts'), w.alerts);
}
$('#wtable').onclick = async e => {
  const b = e.target.closest('[data-act]'); if (!b) return; const a = b.dataset.a; hideErr($('#werr'));
  try {
    if (b.dataset.act === 'open') return investigate(a);
    b.disabled = true;
    if (b.dataset.act === 'sim') renderWatch(await api('/api/watchlist/simulate/' + encodeURIComponent(a), {method: 'POST'}));
    if (b.dataset.act === 'reset') renderWatch(await api('/api/watchlist/reset/' + encodeURIComponent(a), {method: 'POST'}));
    if (b.dataset.act === 'del') renderWatch(await api('/api/watchlist/' + encodeURIComponent(a), {method: 'DELETE'}));
  } catch (err) { showErr($('#werr'), err.message); b.disabled = false; }
};
async function loadWatch() { try { renderWatch(await api('/api/watchlist')); } catch (e) { showErr($('#werr'), e.message); } }
$('#wadd').onclick = async () => {
  const v = $('#waddr').value.trim(); hideErr($('#werr')); if (!v) return showErr($('#werr'), 'Paste a public Ethereum (0x…) or Bitcoin address.');
  $('#wadd').disabled = true;
  try { renderWatch(await api('/api/watchlist', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({address: v})})); $('#waddr').value = ''; }
  catch (e) { showErr($('#werr'), e.message); if (/seed phrase|private key/i.test(e.message)) $('#waddr').value = ''; }
  $('#wadd').disabled = false;
};
$('#waddr').onkeydown = e => { if (e.key === 'Enter') $('#wadd').click(); };
$('#wcheck').onclick = async () => { const b = $('#wcheck'); b.disabled = true; b.querySelector('span:last-child').textContent = 'Checking…'; try { renderWatch(await api('/api/watchlist/check', {method: 'POST'})); } catch (e) { showErr($('#werr'), e.message); } b.disabled = false; b.querySelector('span:last-child').textContent = 'Check now'; };
setInterval(() => { if ($('#v-watch').classList.contains('active')) loadWatch(); }, 15000);

// ---------- how it works ----------
async function loadHow() {
  const c = SHOW.cutoffs;
  const flow = [
    ['db', 'Fetch transactions', 'Blockscout · mempool.space', 'Pull the address\'s public transfers: native, internal and token transfers on Ethereum (plus a second hop for the biggest recipients), or the inputs and outputs on Bitcoin. Nothing private is needed, ever.'],
    ['graph', 'Build the money-flow graph', 'ChainSentinel', 'Merge transfers into flows between addresses, keep the 60 most important counterparties, and tag each with public labels: OFAC sanctions list, exchanges, bridges, mixers, DEXes, known exploiters.'],
    ['rules', 'Rules fire, each with its evidence', 'ChainSentinel · 8 detectors', 'Deterministic detectors look for laundering shapes: sanctions exposure, mixer deposits, rapid pass-through, fan-out, peel chains, chain-hopping, round trips and exploit proceeds. Each finding cites the exact flows behind it. Look-alike guards add context for exchanges, payroll and deposit sweepers.'],
    ['send', 'Send policy, evidence and claim to Sapling', 'Banyan Sapling by Mubit', 'One request with three texts: a written AML policy, the evidence (facts plus findings) and the claim “this wallet\'s activity is legitimate”. No prompt engineering, no chat.'],
    ['bars', 'Get probabilities', 'Banyan Sapling', 'Sapling returns a probability for each of four labels: supported, violation, insufficient information and inconsistent context.'],
    ['gavel', 'Apply the cut-offs', 'ChainSentinel', `Fixed, visible thresholds turn probabilities into FLAG, REVIEW or CLEAR. The analyst sees the numbers, the thresholds and the evidence, so every verdict can be checked.`]];
  $('#howbody').innerHTML = `<h1>How ChainSentinel decides</h1>
  <p class="lede"><b style="color:var(--fg)">Rules detect, Sapling decides.</b> Deterministic detectors find laundering patterns and point at the exact transactions. Banyan Sapling, Mubit's verification model, reads that evidence against a written AML policy and judges whether “this wallet is legitimate” holds up.</p>
  <h2>The pipeline</h2><p>The same six steps run for every investigation, and the stepper on the Investigate screen replays them. Click any step there to see that part on the graph.</p>
  <div class="flow">${flow.map(([i, t, who, d]) => `<div class="fs"><div class="ic">${icon(i)}</div><div><h3>${t}<span class="who">${who}</span></h3><p>${d}</p></div></div>`).join('')}</div>
  <h2>Why split the work this way?</h2>
  <p>Rules alone are brittle. An exchange hot wallet trips “fan-out” every hour, and a fixed threshold can't weigh mitigating context. A model alone, given raw numbers, is cautious: on bare facts Sapling mostly answers <b>insufficient information</b>. Together they work. The rules surface specific, checkable findings, the guards add context, and Sapling weighs it all against the policy.</p>
  <h2>The counterfactual</h2>
  <p>Every investigation sends Sapling two requests with the same policy, claim and on-chain facts. Only the second also lists what the rules found. Comparing them shows what the detectors contribute. Here is the real Bybit exploiter wallet:</p>
  <div class="split" id="howcf"><div class="skel" style="height:170px"></div><div class="skel" style="height:170px"></div></div>
  <h2>From probabilities to a verdict</h2>
  <p>Sapling's conformal prediction set usually contains all four labels, so its own status reads <b>unsure</b>. Instead of hiding that, ChainSentinel applies three fixed cut-offs, shown on every verdict:</p>
  <div class="scale"><div class="track"></div>
    <div class="z" style="left:0;width:${c.clear_max_violation * 100}%;background:#4dbb8840;border-radius:4px 0 0 4px"></div>
    <div class="z" style="left:${c.clear_max_violation * 100}%;width:${(c.flag_violation - c.clear_max_violation) * 100}%;background:#e3ab4330"></div>
    <div class="z" style="left:${c.flag_violation * 100}%;right:0;background:#ef646145;border-radius:0 4px 4px 0"></div>
    <div class="mk" style="left:${c.clear_max_violation * 100}%"><span>${c.clear_max_violation}</span></div><div class="mk" style="left:${c.flag_violation * 100}%"><span>${c.flag_violation}</span></div>
    <span class="ax" style="left:0">P(violation) 0</span><span class="ax" style="right:0">1</span></div>
  <div class="cuts">
    <div class="card"><h3 class="c-FLAG">FLAG</h3><p>P(violation) ≥ ${c.flag_violation}. The model is confident the claim of legitimacy fails the policy.</p></div>
    <div class="card"><h3 class="c-CLEAR">CLEAR</h3><p>P(supported) ≥ ${c.clear_supported} and P(violation) &lt; ${c.clear_max_violation}. Confident it's fine, with little risk signal.</p></div>
    <div class="card"><h3 class="c-REVIEW">REVIEW</h3><p>Anything else. The evidence doesn't let the model commit, so a human analyst looks.</p></div></div>
  <h2>Real and synthetic data</h2>
  <p>Everything tagged <span class="tag real">Real</span> is public blockchain data fetched live (and cached for offline demos). Everything tagged <span class="tag syn">Synthetic</span> comes from our generator, using random addresses, for laundering shapes with no clean public example. The watchlist's “Simulate suspicious tx” transactions are marked <span class="tag sim">Simulated</span>.</p>
  <ul class="src">
    <li><b>Ethereum</b><span>Blockscout API, no key</span></li><li><b>Bitcoin</b><span>mempool.space API, no key</span></li>
    <li><b>Sanctions</b><span>OFAC SDN crypto addresses (0xB10C list)</span></li><li><b>Labels</b><span>etherscan-labels (MIT) and Blockscout public tags</span></li>
    <li><b>Typologies</b><span>IBM AMLworld (synthetic), Elliptic, Elliptic++ and Elliptic2 informed the rules; they are not queried live</span></li>
    <li><b>Model</b><span>Banyan Sapling by Mubit (research preview)</span></li></ul>
  <h2>What it is not</h2>
  <p>A triage aid, not legal advice or a sanctions-screening certification. Data is bounded (about the first 1,000 transfers), labels can be incomplete, and a buggy detector could mislead Sapling. That is why every finding is shown with the flows behind it.</p>`;
  try {
    const r = await api('/api/analyze?address=0x47666Fab8bd0Ac7003bce3f5C3585383F09486E2');
    $('#howcf').innerHTML = `<div class="card"><h4>Facts only ${vpill(r.verdict_facts)}</h4>${barsHTML(r.sapling_facts.probabilities)}<p class="small" style="margin:12px 0 0">Transfer counts, volumes and counterparties, with no interpretation.</p></div>
      <div class="card"><h4>Facts + rule findings ${vpill(r.verdict)}</h4>${barsHTML(r.sapling_full.probabilities)}<p class="small" style="margin:12px 0 0">Plus: ${r.rules.map(x => `<b>${x.id}</b> ${esc(x.name)}`).join(', ')}.</p></div>`;
    $$('#howcf .bars').forEach((b, i) => animateBars(b, i ? r.sapling_full.probabilities : r.sapling_facts.probabilities));
  } catch (e) { $('#howcf').innerHTML = `<div class="muted">Example unavailable: ${esc(e.message)}</div>`; }
}

// ---------- boot ----------
(async () => {
  hydrate();
  try { SHOW = await api('/api/showcase'); } catch (e) { $('#modetxt').textContent = 'Backend unreachable'; return; }
  $('#mode').classList.toggle('off', !!SHOW.offline);
  $('#modetxt').textContent = SHOW.offline ? 'Offline · cached data' : 'Live · Blockscout, mempool, Sapling';
  $('#chips').innerHTML = SHOW.real.map(c => `<button class="ex" data-a="${esc(c.address)}" title="REAL ${esc(c.chain.toUpperCase())} · ${esc(c.address)}"><span class="d"></span>${esc(c.title.split(' (')[0])}</button>`).join('') +
    SHOW.synthetic.map(c => `<button class="ex s" data-s="${esc(c.case)}" title="SYNTHETIC"><span class="d"></span>${esc(c.title.split(' (')[0])}</button>`).join('');
  $$('#chips .ex').forEach(ch => ch.onclick = () => ch.dataset.a ? investigate(ch.dataset.a) : investigate(null, ch.dataset.s));
  api('/api/watchlist').then(w => { WL = w; $('#wcount').textContent = w.items.length || ''; }).catch(() => {});
  const q = new URLSearchParams(location.search);
  const rule = q.get('rule') ? (isNaN(+q.get('rule')) ? q.get('rule') : +q.get('rule')) : undefined;
  if (q.get('a')) investigate(q.get('a'), null, {rule});
  else if (q.get('s')) investigate(null, q.get('s'), {rule});
  else showTab(q.get('tab') || 'overview');
  if (q.get('batch') && q.get('tab') === 'batch') { /* batch auto-runs on first open */ }
})();
