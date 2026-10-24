// ChainSentinel frontend — plain JS + Cytoscape.js (original code)
const $ = s => document.querySelector(s);
const COL = {self:'#ffd43b', exploit:'#ff4d6d', ofac:'#ff2e88', mixer:'#a970ff', bridge:'#ffa94d', exchange:'#4dabf7', dex:'#38d9a9', unknown:'#5c677d'};
const CATNAME = {self:'Investigated', exploit:'Exploit/hack', ofac:'OFAC sanctioned', mixer:'Mixer', bridge:'Bridge/x-chain', exchange:'Exchange', dex:'DEX', unknown:'Unlabelled'};
const LBL = {supported:'supported', violation:'violation', insufficient_information:'insufficient info', inconsistent_context:'inconsistent ctx'};
const short = a => a ? (a.length > 16 ? a.slice(0,8)+'…'+a.slice(-4) : a) : '?';
const fmtT = ts => ts ? new Date(ts*1000).toISOString().replace('T',' ').slice(0,16) : '';
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
async function api(path, opt) { const r = await fetch(path, opt); const j = await r.json(); if (!r.ok) throw new Error(j.detail || r.statusText); return j; }
let SHOW = null, CY = null, CUR = null;

// ---------- tabs ----------
document.querySelectorAll('nav button').forEach(b => b.onclick = () => showTab(b.dataset.tab));
function showTab(t) {
  document.querySelectorAll('nav button').forEach(b => b.classList.toggle('active', b.dataset.tab === t));
  document.querySelectorAll('.tab').forEach(s => s.classList.toggle('active', s.id === 'tab-' + t));
  if (t === 'lab' && !$('#labgrid').children.length) loadLab();
  if (t === 'watch') loadWatch();
  if (t === 'investigate' && CY) CY.resize();
}
$('#legend').innerHTML = Object.entries(COL).map(([k,c]) => `<span><i style="background:${c}"></i>${CATNAME[k]}</span>`).join('');

// ---------- graph ----------
function drawGraph(container, G, opts = {}) {
  const maxV = Math.max(1e-9, ...G.edges.map(e => e.native ? e.value : 0));
  const els = [];
  G.nodes.forEach(n => els.push({data: {id: n.id, lbl: n.label ? n.label.split(' [')[0].slice(0, 28) : short(n.id), cat: n.is_self ? 'self' : n.cat, real: n.cat, self: n.is_self ? 1 : 0}}));
  G.edges.forEach(e => {
    const w = e.native ? 1 + 9 * Math.sqrt(e.value / maxV) : 1;
    els.push({data: {id: e.id, source: e.source, target: e.target, w, native: e.native ? 1 : 0,
      elbl: e.native ? `${e.value.toLocaleString(undefined,{maximumFractionDigits:2})} ${e.asset}` : `${e.count}× ${e.asset}`}});
  });
  const cy = cytoscape({container, elements: els, wheelSensitivity: 0.25,
    layout: G.nodes.length > 25 ? {name: 'concentric', concentric: n => n.data('self') ? 10 : (n.data('cat') !== 'unknown' ? 5 : 1), levelWidth: () => 1, minNodeSpacing: 18, animate: false}
                                : {name: 'cose', animate: false, randomize: false, nodeRepulsion: 120000, idealEdgeLength: 70, nodeOverlap: 20, gravity: 0.6, numIter: 2500},
    style: [
      {selector: 'node', style: {'background-color': n => COL[n.data('cat')] || COL.unknown, label: 'data(lbl)', color: '#c9d1e0', 'font-size': 9, 'text-valign': 'bottom', 'text-margin-y': 4,
        width: n => n.data('self') ? 30 : (n.data('cat') === 'unknown' ? 12 : 20), height: n => n.data('self') ? 30 : (n.data('cat') === 'unknown' ? 12 : 20), 'border-width': n => n.data('self') ? 3 : 0, 'border-color': '#fff', 'text-outline-color': '#0b0e14', 'text-outline-width': 2}},
      {selector: 'edge', style: {width: 'data(w)', 'line-color': e => e.data('native') ? '#3a4a66' : '#2b3446', 'target-arrow-color': '#3a4a66', 'target-arrow-shape': 'triangle', 'curve-style': 'bezier', opacity: .8, 'arrow-scale': .7, 'line-style': e => e.data('native') ? 'solid' : 'dashed'}},
      {selector: 'edge.hl', style: {'line-color': '#5ce1e6', 'target-arrow-color': '#5ce1e6', opacity: 1, label: 'data(elbl)', 'font-size': 8, color: '#5ce1e6', 'text-background-color': '#0b0e14', 'text-background-opacity': .8, 'z-index': 99}},
      {selector: 'node.hl', style: {'border-width': 3, 'border-color': '#5ce1e6'}},
      {selector: '.faded', style: {opacity: .12}},
    ]});
  if (opts.onNode) cy.on('tap', 'node', ev => opts.onNode(ev.target.id()));
  if (opts.onEdge) cy.on('tap', 'edge', ev => opts.onEdge(ev.target.id()));
  return cy;
}
function highlight(cy, edgeIds, nodeIds = []) {
  cy.elements().removeClass('hl faded');
  if (!edgeIds || (!edgeIds.length && !nodeIds.length)) return;
  const es = cy.collection(); edgeIds.forEach(id => { const e = cy.getElementById(id); if (e.length) es.merge(e); });
  const ns = es.connectedNodes(); nodeIds.forEach(id => { const n = cy.getElementById(id); if (n.length) ns.merge(n); });
  cy.elements().addClass('faded'); es.removeClass('faded').addClass('hl'); ns.removeClass('faded').addClass('hl');
  if (es.length || ns.length) cy.animate({fit: {eles: es.union(ns), padding: 60}}, {duration: 400});
}

// ---------- investigate ----------
function bars(p) { return Object.keys(LBL).map(k => `<div class="bar"><span>${LBL[k]}</span><div class="t"><div class="f f-${k}" style="width:${(p[k]*100).toFixed(1)}%"></div></div><span>${(p[k]*100).toFixed(0)}%</span></div>`).join(''); }
function miniBar(p) { return `<div class="mini">${['violation','insufficient_information','inconsistent_context','supported'].map(k => `<div class="f-${k}" style="width:${p[k]*100}%"></div>`).join('')}</div>`; }
async function investigate(addr, synthetic) {
  showTab('investigate');
  $('#panel').innerHTML = `<div class="empty spinner">⏳ Fetching transactions, building the flow graph, running rules, asking Sapling…</div>`;
  $('#graphhdr').textContent = ''; $('#timeline').innerHTML = '';
  try {
    const r = synthetic ? await api('/api/synthetic/' + synthetic) : await api('/api/analyze?address=' + encodeURIComponent(addr) + ($('#refresh').checked ? '&refresh=true' : ''));
    if (!synthetic) $('#addr').value = addr;
    render(r);
  } catch (e) { $('#panel').innerHTML = `<div class="card"><b class="flag">Error</b><p>${esc(e.message)}</p></div>`; }
}
function render(r) {
  CUR = r;
  if (CY) CY.destroy();
  CY = drawGraph($('#cy'), r.graph, {onEdge: id => highlight(CY, [id]), onNode: id => nodeInfo(id)});
  CY.on('tap', ev => { if (ev.target === CY) highlight(CY, []); });
  $('#graphhdr').innerHTML = `${r.synthetic ? '<span class="badge tag-syn">SYNTHETIC</span>' : '<span class="badge tag-real">REAL ' + r.chain.toUpperCase() + '</span>'} &nbsp; ${r.n_tx} transfers analysed · showing ${r.graph.nodes.length} addresses, ${r.graph.edges.length} flows (hop 1–2, capped) · click a rule, flow, or timeline row to highlight`;
  // timeline
  const tl = r.timeline.slice().reverse().slice(0, 300);
  $('#tlcount').textContent = `(${r.timeline.length} most recent value transfers)`;
  const w = r.address;
  $('#timeline').innerHTML = tl.map((t, i) => {
    const dir = t.hop === 2 ? 'hop2' : (t.frm === w ? 'out' : 'in'); const cp = dir === 'in' ? t.frm : t.to;
    const node = r.graph.nodes.find(n => n.id === cp);
    return `<div class="tl" data-i="${i}"><span class="muted">${fmtT(t.ts)}</span><span class="${dir === 'hop2' ? 'h2' : dir}">${dir === 'hop2' ? 'HOP2' : dir.toUpperCase()}</span><span>${t.value.toLocaleString(undefined,{maximumFractionDigits:4})} ${esc(t.asset)}</span><span>${esc(node && node.label ? node.label : short(cp))}</span><span class="muted mono">${esc(String(t.hash).slice(0,10))}</span></div>`;
  }).join('');
  document.querySelectorAll('.tl').forEach(el => el.onclick = () => { const t = tl[+el.dataset.i]; const k = t.asset === 'ETH' || t.asset === 'BTC' ? 'native' : t.asset; highlight(CY, [`${t.frm}->${t.to}:${k}`], [t.frm, t.to]); });
  // panel
  const pf = r.sapling_full.probabilities, pp = r.sapling_facts.probabilities, c = r.cutoffs;
  const req = r.sapling_full.request;
  $('#panel').innerHTML = `
  <div class="card"><h4>Entity</h4><div class="addr mono">${esc(r.address)}</div>
    <div style="margin-top:6px">${r.label && r.label.name ? `<span class="badge" style="color:${COL[r.label.cat]||'#aaa'}">${esc(CATNAME[r.label.cat]||r.label.cat)}</span> ${esc(r.label.name)} <span class="muted">(${esc(r.label.src)})</span>` : '<span class="muted">No public label</span>'}</div>
    ${r.meta && r.meta.title ? `<div class="muted" style="margin-top:4px">${esc(r.meta.title)} · expected: ${esc(r.meta.expected)}</div>` : ''}
    <div class="muted" style="margin-top:4px">In ${r.stats.tin.toLocaleString(undefined,{maximumFractionDigits:2})} ${r.graph.unit} (${r.stats.n_in} tx) · Out ${r.stats.tout.toLocaleString(undefined,{maximumFractionDigits:2})} ${r.graph.unit} (${r.stats.n_out} tx)</div></div>
  <div class="card"><h4>Verdict</h4><div class="verdict v-${r.verdict}">${r.verdict}</div>
    <div class="muted">Sapling status: <b>${esc(r.sapling_full.status)}</b> · top label: <b>${esc(r.sapling_full.raw_label)}</b> · conformal set: ${esc((r.sapling_full.prediction_set||[]).join(', '))} · ${Math.round((r.sapling_full.timing_ms||{}).model||0)} ms</div>
    <div style="margin-top:8px">${bars(pf)}</div>
    <div class="muted" style="font-size:11px;margin-top:6px">Cutoffs: <b class="flag">FLAG</b> if P(violation) ≥ ${c.flag_violation} · <b class="clear">CLEAR</b> if P(supported) ≥ ${c.clear_supported} and P(violation) &lt; ${c.clear_max_violation} · otherwise <b class="review">REVIEW</b></div></div>
  <div class="card"><h4>Why</h4><div>${esc(r.why)}</div></div>
  <div class="card"><h4>Rules fired (${r.rules.length}) — click to see it on the graph</h4>
    ${r.rules.map((x, i) => `<div class="rule" data-r="${i}"><b>${x.id}</b> ${esc(x.name)}<br><small>${esc(x.detail)}</small><br><small class="muted">${x.edges_in_graph.length} flows highlighted${x.edges.length > x.edges_in_graph.length ? ` (${x.edges.length - x.edges_in_graph.length} more outside the capped view)` : ''}</small></div>`).join('') || '<div class="muted">No rule fired.</div>'}
    ${r.lookalikes.map(l => `<div class="rule look"><b>Look-alike</b> <small>${esc(l)}</small></div>`).join('')}</div>
  <div class="card"><h4>Counterfactual: what do the rules add?</h4><div class="cf">
    <div><b>Facts only</b> → <span class="v-${r.verdict_facts}">${r.verdict_facts}</span>${bars(pp)}</div>
    <div><b>Facts + rule findings</b> → <span class="v-${r.verdict}">${r.verdict}</span>${bars(pf)}</div></div>
    <div class="muted" style="font-size:11px;margin-top:6px">Same policy and claim, same on-chain facts. The right side also tells Sapling which rules our detectors matched.</div></div>
  <div class="card"><h4>Exactly what Sapling saw</h4>
    <details><summary>Claim</summary><pre>${esc(req.claim)}</pre></details>
    <details><summary>Evidence (facts + findings)</summary><pre>${esc(req.evidence)}</pre></details>
    <details><summary>Evidence (facts only)</summary><pre>${esc(r.sapling_facts.request.evidence)}</pre></details>
    <details><summary>Policy</summary><pre>${esc(req.policy)}</pre></details>
    <details><summary>Raw Sapling response</summary><pre>${esc(JSON.stringify({status:r.sapling_full.status, raw_label:r.sapling_full.raw_label, prediction_set:r.sapling_full.prediction_set, probabilities:pf, timing_ms:r.sapling_full.timing_ms}, null, 1))}</pre></details></div>
  <div class="card" id="nodeinfo"><h4>Selected address</h4><div class="muted">Click a node.</div></div>`;
  document.querySelectorAll('.rule[data-r]').forEach(el => el.onclick = () => {
    document.querySelectorAll('.rule').forEach(x => x.classList.remove('on')); el.classList.add('on');
    const x = r.rules[+el.dataset.r]; highlight(CY, x.edges_in_graph, x.nodes);
  });
}
function nodeInfo(id) {
  const n = CUR.graph.nodes.find(x => x.id === id); if (!n) return;
  const es = CUR.graph.edges.filter(e => e.source === id || e.target === id);
  highlight(CY, es.map(e => e.id), [id]);
  const ex = CUR.chain === 'btc' ? `https://mempool.space/address/${id}` : `https://eth.blockscout.com/address/${id}`;
  $('#nodeinfo').innerHTML = `<h4>Selected address</h4><div class="addr mono">${esc(id)}</div><div><span class="badge" style="color:${COL[n.is_self?'self':n.cat]}">${CATNAME[n.is_self?'self':n.cat]}</span> ${esc(n.label || '')} <span class="muted">${esc(n.src || '')}</span></div>
   ${es.map(e => `<div class="muted" style="font-size:11px">${e.source === id ? '→ ' + short(e.target) : '← ' + short(e.source)} ${e.value.toLocaleString(undefined,{maximumFractionDigits:3})} ${esc(e.asset)} · ${e.count} tx · ${fmtT(e.first)}</div>`).join('')}
   ${CUR.synthetic ? '<div class="muted">synthetic address</div>' : `<a href="${ex}" target="_blank" style="color:var(--acc)">Open in explorer ↗</a> &nbsp; <a href="#" onclick="investigate('${id}');return false" style="color:var(--acc)">Investigate this address</a>`}`;
  $('#nodeinfo').scrollIntoView({behavior: 'smooth'});
}
$('#go').onclick = () => investigate($('#addr').value.trim());
$('#addr').onkeydown = e => { if (e.key === 'Enter') $('#go').click(); };

// ---------- batch ----------
$('#runbatch').onclick = async () => {
  $('#batchinfo').textContent = '⏳ running real + synthetic cases through rules and Sapling…';
  ['FLAG','REVIEW','CLEAR'].forEach(k => $('#col-' + k).innerHTML = '');
  const t0 = Date.now(); const b = await api('/api/batch');
  b.items.forEach(it => {
    const d = document.createElement('div'); d.className = 'bcard';
    const ok = (it.expected === 'violation' && it.verdict === 'FLAG') || (it.expected === 'supported' && it.verdict === 'CLEAR');
    d.innerHTML = `<div><span class="badge ${it.kind === 'REAL' ? 'tag-real' : 'tag-syn'}">${it.kind}${it.kind === 'REAL' ? ' ' + (it.chain||'').toUpperCase() : ''}</span> <b>${esc(it.title)}</b></div>
      <div class="muted mono" style="font-size:11px">${esc(short(it.address))}</div>
      <div class="rules">${(it.rules||[]).map(x => `<span class="rtag">${x}</span>`).join('') || '<span class="muted" style="font-size:11px">no rules fired</span>'}</div>
      ${it.p ? miniBar(it.p) + `<div class="muted" style="font-size:11px;margin-top:3px">P(violation) ${(it.p.violation*100).toFixed(0)}% · P(supported) ${(it.p.supported*100).toFixed(0)}% · facts-only: ${it.verdict_facts} · expected ${it.expected} ${ok ? '✓' : ''}</div>` : `<div class="flag">${esc(it.error)}</div>`}`;
    d.onclick = () => it.kind === 'REAL' ? investigate(it.address) : investigate(null, it.case);
    $('#col-' + it.verdict).appendChild(d);
  });
  const n = k => b.items.filter(i => i.verdict === k).length;
  $('#batchinfo').textContent = `${b.items.length} wallets (${b.items.filter(i => i.kind === 'REAL').length} real, ${b.items.filter(i => i.kind === 'SYNTHETIC').length} synthetic) · ${n('FLAG')} flagged, ${n('REVIEW')} review, ${n('CLEAR')} cleared · ${((Date.now() - t0) / 1000).toFixed(1)}s`;
};

// ---------- pattern lab ----------
async function loadLab() {
  for (const s of SHOW.synthetic) {
    const d = document.createElement('div'); d.className = 'labcard';
    d.innerHTML = `<div><span class="badge tag-syn">SYNTHETIC</span> <b>${esc(s.title)}</b> <span class="muted">expected: ${s.expected}</span></div><div class="labcy"></div><div class="res muted">⏳ analysing…</div>`;
    $('#labgrid').appendChild(d);
    api('/api/synthetic/' + s.case).then(r => {
      const cy = drawGraph(d.querySelector('.labcy'), r.graph);
      const all = r.rules.flatMap(x => x.edges_in_graph); highlight(cy, all, []); cy.stop(); cy.fit(undefined, 20);
      d.querySelector('.res').innerHTML = `<span class="verdict v-${r.verdict}" style="font-size:18px">${r.verdict}</span> &nbsp; ${r.rules.map(x => `<span class="rtag" title="${esc(x.detail)}">${x.id} ${esc(x.name)}</span>`).join('') || '<span class="muted">no rules</span>'}
        ${miniBar(r.sapling_full.probabilities)}<div style="font-size:11px;margin-top:4px">Sapling P(violation) <b>${(r.sapling_full.probabilities.violation*100).toFixed(0)}%</b> with findings vs <b>${(r.sapling_facts.probabilities.violation*100).toFixed(0)}%</b> on facts only (${r.verdict_facts}) · P(supported) ${(r.sapling_full.probabilities.supported*100).toFixed(0)}%</div>
        <button style="margin-top:6px" class="open">Open full investigation →</button>`;
      d.querySelector('.open').onclick = () => investigate(null, s.case);
    }).catch(e => d.querySelector('.res').textContent = e.message);
  }
}

// ---------- watchlist ----------
function renderWatch(w) {
  $('#wtable').innerHTML = `<tr><th>Address</th><th>Verdict</th><th>Rules</th><th>Last check</th><th></th></tr>` + w.items.map(it => `<tr>
    <td><span class="badge tag-real">${it.chain.toUpperCase()}</span> <span class="mono">${esc(short(it.address))}</span><br><span class="muted">${esc(it.label || '')}</span>${it.injected ? '<span class="sim">SIMULATED TX INJECTED</span>' : ''}</td>
    <td class="v-${it.last_verdict}"><b>${it.last_verdict || '…'}</b>${it.p ? `<br><span class="muted">P(v) ${(it.p.violation*100).toFixed(0)}%</span>` : ''}</td>
    <td>${(it.rules||[]).map(x => `<span class="rtag">${x}</span>`).join('') || '<span class="muted">none</span>'}</td>
    <td class="muted">${fmtT(it.last_check)}</td>
    <td><button onclick="investigate('${it.address}')">Open</button> ${it.chain === 'eth' ? `<button onclick="wsim('${it.address}')" title="Demo mode: inject a SYNTHETIC Tornado Cash deposit">Simulate suspicious tx</button>` : ''} ${it.injected ? `<button onclick="wreset('${it.address}')">Reset</button>` : ''} <button onclick="wdel('${it.address}')">✕</button></td></tr>`).join('');
  $('#alerts').innerHTML = w.alerts.map(a => `<div class="alert"><div><b class="v-${a.to}">${a.frm} → ${a.to}</b> <span class="mono muted">${esc(short(a.address))}</span>${a.simulated ? '<span class="sim">SIMULATED</span>' : ''} <span class="muted" style="float:right">${fmtT(a.ts)}</span></div><div style="font-size:12px;margin-top:4px">${esc(a.text)}</div></div>`).join('') || '<div class="muted">No alerts yet. Try “Simulate suspicious tx” on a watched Ethereum wallet.</div>';
}
async function loadWatch() { renderWatch(await api('/api/watchlist')); }
async function wsim(a) { renderWatch(await api('/api/watchlist/simulate/' + a, {method: 'POST'})); }
async function wreset(a) { renderWatch(await api('/api/watchlist/reset/' + a, {method: 'POST'})); }
async function wdel(a) { renderWatch(await api('/api/watchlist/' + a, {method: 'DELETE'})); }
$('#wadd').onclick = async () => { try { renderWatch(await api('/api/watchlist', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({address: $('#waddr').value.trim()})})); $('#waddr').value = ''; } catch (e) { alert(e.message); } };
$('#wcheck').onclick = async () => { $('#wcheck').textContent = 'Checking…'; renderWatch(await api('/api/watchlist/check', {method: 'POST'})); $('#wcheck').textContent = 'Check now'; };
setInterval(() => { if ($('#tab-watch').classList.contains('active')) loadWatch(); }, 15000);

// ---------- boot ----------
(async () => {
  SHOW = await api('/api/showcase');
  $('#mode').textContent = SHOW.offline ? 'OFFLINE · cached data' : 'LIVE · Blockscout + mempool.space + Sapling';
  $('#chips').innerHTML = SHOW.real.map(c => `<span class="chip" data-a="${c.address}"><b class="tag-real">REAL ${c.chain.toUpperCase()}</b>${esc(c.title)}</span>`).join('') +
    SHOW.synthetic.map(c => `<span class="chip" data-s="${c.case}"><b class="tag-syn">SYN</b>${esc(c.title)}</span>`).join('');
  document.querySelectorAll('.chip').forEach(ch => ch.onclick = () => ch.dataset.a ? investigate(ch.dataset.a) : investigate(null, ch.dataset.s));
  const q = new URLSearchParams(location.search);
  if (q.get('tab')) showTab(q.get('tab'));
  if (q.get('a')) investigate(q.get('a')); else if (q.get('s')) investigate(null, q.get('s'));
  if (q.get('batch')) $('#runbatch').click();
  if (q.get('rule')) setTimeout(() => { const el = document.querySelector(`.rule[data-r="${q.get('rule')}"]`); if (el) el.click(); }, 2500);
})();
