/* nse-ai-terminal browser terminal — vanilla JS, no build step.
 * Connects to the FastAPI backend over WebSocket, renders each tab, and drives the
 * zero-key Puter.js AI panel (see puter-ai.js).
 *
 * HONESTY: confidence shown anywhere is a heuristic score, not a win rate.
 */
const HOST = location.hostname || "localhost";
const API = `http://${HOST}:8000`;
const WS_URL = `ws://${HOST}:8000/ws`;
const S = { config: null, indices: [], selected: null, snapshot: null, decision: null, lastState: null, };

/* ---------------- tabs ---------------- */
document.querySelectorAll("#tabs button").forEach((b) => {
  b.addEventListener("click", () => {
    document.querySelectorAll("#tabs button").forEach((x) => x.classList.remove("active"));
    document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    document.getElementById("tab-" + b.dataset.tab).classList.add("active");
    renderAll();
  });
});

/* ---------------- websocket ---------------- */
function setConn(ok) {
  const el = document.getElementById("conn");
  el.textContent = ok ? "connected" : "disconnected";
  el.className = "pill " + (ok ? "good" : "bad");
}
function connect() {
  const ws = new WebSocket(WS_URL);
  ws.onopen = () => setConn(true);
  ws.onclose = () => { setConn(false); setTimeout(connect, 3000); };
  ws.onerror = () => setConn(false);
  ws.onmessage = (ev) => {
    let msg;
    try { msg = JSON.parse(ev.data); } catch { return; }
    log("ws:" + msg.channel);
    if (msg.channel === "config") {
      S.indices = msg.payload.indices || [];
      buildIndexSelect();
    } else if (msg.channel === "state") {
      S.lastState = msg.payload;
      renderHeader();
      renderLogs();
    } else if (msg.channel === "decision") {
      if (msg.payload.index === S.selected) refreshSelected();
    }
  };
}

/* ---------------- data ---------------- */
async function getJSON(path) {
  try {
    const r = await fetch(API + path);
    if (!r.ok) return null;
    return await r.json();
  } catch { return null; }
}
async function loadConfig() {
  S.config = await getJSON("/api/config");
  if (S.config) {
    document.getElementById("src").textContent = "source: " + S.config.data_source;
    document.getElementById("adv").textContent = "advanced: " + (S.config.advanced_engine ? "on" : "off");
    document.getElementById("demo").style.display = S.config.data_source === "demo" ? "" : "none";
    document.getElementById("settingsBox").textContent = JSON.stringify(S.config, null, 2);
  }
}
function buildIndexSelect() {
  const sel = document.getElementById("chainIndex");
  sel.innerHTML = "";
  S.indices.forEach((i) => {
    const o = document.createElement("option");
    o.value = i; o.textContent = i; sel.appendChild(o);
  });
  if (!S.selected && S.indices.length) S.selected = S.indices[0];
  sel.value = S.selected;
  sel.onchange = () => { S.selected = sel.value; refreshSelected(); };
}
async function refreshSelected() {
  if (!S.selected) return;
  S.snapshot = await getJSON("/api/snapshot/" + S.selected);
  S.decision = await getJSON("/api/decision/" + S.selected);
  renderAll();
}

/* ---------------- header / logs ---------------- */
function renderHeader() {
  const d = S.decision;
  if (d) {
    const v = document.getElementById("verdict");
    v.textContent = d.verdict;
    v.style.background = d.verdict.includes("CALL") ? "#12351f" : d.verdict.includes("PUT") ? "#3a1620" : "#22303f";
  }
}
function log(line) {
  const box = document.getElementById("logBox");
  if (!box) return;
  const t = new Date().toLocaleTimeString();
  box.textContent = `${t} ${line}\n` + box.textContent.split("\n").slice(0, 200).join("\n");
}
function renderLogs() {
  if (S.lastState) log(`cycle ${S.lastState.cycle} source=${S.lastState.source}`);
}

/* ---------------- render orchestration ---------------- */
function renderAll() {
  renderHeader(); renderChain(); renderHeatmap(); renderPremVol(); renderGreeks();
  renderFlow(); renderRegime(); renderPlans(); renderBacktest();
}

/* ---------------- chain table ---------------- */
function renderChain() {
  const t = document.getElementById("chainTable");
  const snap = S.snapshot;
  if (!snap) { t.innerHTML = "<tr><td class='muted'>no snapshot yet</td></tr>"; return; }
  document.getElementById("chainMeta").textContent = `${snap.index} spot=${snap.spot} atm=${snap.atm_strike} expiry=${snap.expiry} src=${snap.source}`;
  let html = `<tr><th>strike</th><th>CE LTP</th><th>CE OI</th><th>CE ΔOI</th><th>CE IV</th><th>PE LTP</th><th>PE OI</th><th>PE ΔOI</th><th>PE IV</th></tr>`;
  for (const s of snap.strikes) {
    const atm = s.strike === snap.atm_strike ? "style='font-weight:700;color:#5aa9ff'" : "";
    html += `<tr ${atm}><td>${s.strike}</td><td>${fmt(s.ce_ltp)}</td><td>${fmt(s.ce_oi)}</td><td class="${cls(s.ce_oi_change)}">${fmt(s.ce_oi_change)}</td><td>${fmt(s.ce_iv)}</td><td>${fmt(s.pe_ltp)}</td><td>${fmt(s.pe_oi)}</td><td class="${cls(s.pe_oi_change)}">${fmt(s.pe_oi_change)}</td><td>${fmt(s.pe_iv)}</td></tr>`;
  }
  t.innerHTML = html;
}

/* ---------------- canvas helpers ---------------- */
function clear(c) {
  const x = c.getContext("2d"); x.clearRect(0, 0, c.width, c.height); return x;
}
function drawBars(canvas, groups, title) {
  const ctx = clear(canvas), W = canvas.width, H = canvas.height, pad = 30;
  ctx.strokeStyle = "#1e2a36"; ctx.beginPath(); ctx.moveTo(pad, H-pad); ctx.lineTo(W-pad, H-pad); ctx.stroke();
  ctx.fillStyle = "#7c8b9c"; ctx.fillText(title || "", pad, 16);
  if (!groups.length) return;
  const maxV = Math.max(...groups.flatMap(g => g.values.map(Math.abs)), 1);
  const slot = (W-2*pad)/groups.length;
  groups.forEach((g,i) => {
    const x0=pad+i*slot+2, bw=(slot-4)/g.values.length;
    g.values.forEach((v,j) => { const h=Math.abs(v)/maxV*(H-2*pad); ctx.fillStyle=g.colors[j]; ctx.fillRect(x0+j*bw,H-pad-h,bw-1,h); });
    if (i%2===0) { ctx.fillStyle="#5c6b7c"; ctx.font="10px monospace"; ctx.fillText(String(g.label),x0,H-pad+12); }
  });
}
function drawLine(canvas, series, title) {
  const ctx=clear(canvas), W=canvas.width, H=canvas.height, pad=30;
  ctx.fillStyle="#7c8b9c"; ctx.fillText(title||"",pad,16);
  if(!series.length)return;
  const min=Math.min(...series), max=Math.max(...series), rng=max-min||1;
  ctx.strokeStyle="#5aa9ff"; ctx.beginPath();
  series.forEach((v,i)=>{const x=pad+(i/(series.length-1))*(W-2*pad),y=H-pad-((v-min)/rng)*(H-2*pad);i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);});
  ctx.stroke();
}

/* ---------------- tab renderers ---------------- */
function renderHeatmap() {
  const c=document.getElementById("heatmap");
  if(!S.snapshot){clear(c);return;}
  const groups=S.snapshot.strikes.map(s=>({label:String(s.strike),values:[s.ce_oi||0,s.pe_oi||0,s.ce_oi_change||0,s.pe_oi_change||0],colors:["#31d07a","#ff5d6c","#1d7a4c","#8f3440"]}));
  drawBars(c,groups,"OI heatmap — CE(green) PE(red) CEΔOI(dk-green) PEΔOI(dk-red)");
}
function renderPremVol() {
  const dec=S.decision,t=document.getElementById("premvolText");
  if(!S.snapshot){clear(document.getElementById("premvol"));return;}
  const premSeries=S.snapshot.strikes.map(s=>(s.ce_ltp||0)-(s.pe_ltp||0));
  drawLine(document.getElementById("premvol"),premSeries,"CE-PE premium spread across strikes");
  t.textContent=dec?`verdict ${dec.verdict}, plans ${dec.plans_qualifying}, suppressed ${dec.plans_suppressed}`:"";
}
function renderGreeks() {
  const c=document.getElementById("ivsurface");
  if(!S.snapshot){clear(c);return;}
  const groups=S.snapshot.strikes.map(s=>({label:String(s.strike),values:[(s.ce_iv||0)*100,(s.pe_iv||0)*100],colors:["#5aa9ff","#ffcc66"]}));
  drawBars(c,groups,"IV surface — CE (blue) vs PE (amber), %");
  document.getElementById("greeksText").textContent="delta/gamma/theta/vega per strike are in the chain table and the MCP get_greeks tool.";
}
function renderFlow() {
  const el=document.getElementById("flowText"),dec=S.decision;
  el.textContent=dec?"Order-flow inference uses the tick rule approximation (retail feeds lack aggressor tags). See pipeline part 16.":"no decision yet";
}
function renderRegime() {
  const el=document.getElementById("regimeText"),dec=S.decision;
  el.textContent=dec?JSON.stringify({regime:dec.regime,override:dec.override,override_reason:dec.override_reason,notes:dec.notes},null,2):"no decision yet";
}
function renderPlans() {
  const t=document.getElementById("plansTable"),st=document.getElementById("planStatus"),dec=S.decision;
  if(!dec){t.innerHTML="";st.textContent="no decision yet";return;}
  st.textContent=`${dec.verdict} • qualifying plans: ${dec.plans_qualifying} • suppressed: ${dec.plans_suppressed}`+
    (dec.suppression_reasons&&dec.suppression_reasons.length?" • reasons: "+dec.suppression_reasons.slice(0,5).join("; "):"");
  if(!dec.plans||!dec.plans.length){t.innerHTML="<tr><td class='muted'>No qualifying trade. (Plans are never padded to five.)</td></tr>";return;}
  let html="<tr><th>side</th><th>strike</th><th>entry</th><th>SL</th><th>targets</th><th>R:R</th><th>size</th><th>conf</th><th>strategies</th></tr>";
  for(const p of dec.plans) html+=`<tr><td class="${p.side==="CALL"?"cell-pos":"cell-neg"}">${p.side}</td><td>${p.strike}</td><td>${fmt(p.entry)}</td><td>${fmt(p.stop_loss)}</td><td>${(p.targets||[]).map(fmt).join(" / ")}</td><td>${fmt(p.rr)}</td><td>${p.position_size}</td><td>${fmt(p.confidence)}</td><td>${(p.strategy_ids||[]).join(",")}</td></tr>`;
  t.innerHTML=html;
}
function renderBacktest() {
  const el=document.getElementById("backtestText"),dec=S.decision;
  el.textContent=dec?"Per-cycle backtest memory summary is attached in the decision notes; full backtests run via the /api and MCP tools on stored trade samples.":"Run a scan to populate the backtest view.";
}

/* ---------------- strategy registry ---------------- */
async function loadRegistry(q) {
  const data=await getJSON("/api/strategies"+(q?"?q="+encodeURIComponent(q):""));
  if(!data)return;
  document.getElementById("regCount").textContent=data.count+" modules";
  const ul=document.getElementById("regList"); ul.innerHTML="";
  data.strategies.slice(0,400).forEach(m=>{
    const li=document.createElement("li");
    li.innerHTML=`<span class="id">${m.id}</span><span>${m.name}</span> <span class="fam">${m.family}${m.advanced?" • ADV":""}</span>`;
    ul.appendChild(li);
  });
}
document.getElementById("regSearch").addEventListener("input",e=>loadRegistry(e.target.value));

/* ---------------- AI panel (Puter.js zero-key) ---------------- */
document.getElementById("aiRun").addEventListener("click",async()=>{
  const st=document.getElementById("aiStatus");
  if(!window.PuterAI||!window.PuterAI.available()){st.textContent="Puter.js not loaded (open over http and allow the script)";return;}
  st.textContent="running 6 layers via Puter.js (billed to your signed-in Puter account)...";
  const digest=S.decision?{index:S.selected,verdict:S.decision.verdict,regime:S.decision.regime,confidence:(S.decision.plans&&S.decision.plans[0])?S.decision.plans[0].confidence:null,plans:S.decision.plans_qualifying,notes:S.decision.notes}:{index:S.selected,note:"no decision yet"};
  const results=await window.PuterAI.runSixLayers(digest),box=document.getElementById("aiLayers"); box.innerHTML="";
  results.forEach(r=>{const d=document.createElement("div");d.className="layer";d.innerHTML=`<h4>${r.layer} — ${r.model||"?"}</h4><div class="${r.agrees?"agree":"disagree"}">${r.agrees?"agrees":"disagrees"}</div><div class="muted">${(r.concerns||[]).join("; ")}</div><div>${r.verdict_recommendation||""} ${r.notes?"• "+r.notes:""}</div>`;box.appendChild(d);});
  st.textContent="done — AI is validation only; confidence is not a win rate";
});

/* ---------------- utils ---------------- */
function fmt(v){return(v===null||v===undefined)?"-":(typeof v==="number"?v.toLocaleString():v);}
function cls(v){return(v===null||v===undefined)?"":(v>0?"cell-pos":v<0?"cell-neg":"");}

/* ---------------- boot ---------------- */
(async function boot(){
  await loadConfig();
  if(S.config&&S.config.indices){S.indices=S.config.indices;buildIndexSelect();}
  loadRegistry("");
  await refreshSelected();
  connect();
  setInterval(refreshSelected,5000);
})();