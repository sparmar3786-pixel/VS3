/* Final UI for NSE-AI-TERMINAL: 30 reference screens + live connectivity/index extensions. */
var screens=[
['Splash / Launch','Start terminal safely. Paper/Demo first; no order placement.'],
['Login / Authentication','Angel One Client ID, PIN and TOTP are handled by the backend.'],
['Dashboard (Home)','Final engine verdict: CALL BUY / PUT BUY / WAIT / NO QUALIFYING TRADE.'],
['Market Overview','NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY, SENSEX and BANKEX.'],
['Option Chain','CE/PE LTP, OI, change in OI, volume and ATM.'],
['OI Heatmap','Long Buildup, Short Buildup, Short Covering and Long Unwinding.'],
['Premium / Volume','Premium movement with volume and data-quality confirmation.'],
['Greeks / IV Surface','Delta, Gamma, Theta, Vega and IV when supplied by a verified source.'],
['Order Flow','Observed pressure only; no fabricated flow.'],
['Regime','Trend, volatility, momentum and market mode.'],
['Trade Plans (5+)','Only genuine qualifying plans; never pad to five.'],
['Backtest','Performance, expectancy, drawdown and walk-forward evidence.'],
['Strategy Registry','377 core + 25 advanced strategy modules.'],
['AI 6-Layer Panel','Six validation layers; AI cannot create missing trade fields.'],
['Logs / Settings','Backend URL, data source, API status and paper mode.'],
['Portfolio / Positions','Paper positions only.'],
['Charts - Advanced','Price, OI, premium and volume across supported timeframes.'],
['Strategy Details','Exact strategy IDs and available evidence.'],
['Risk Management','One final R:R gate, risk limits and stale-data protection.'],
['Notifications / Alerts','Signal, data-quality and risk alerts.'],
['Help / Education','OI, risk, data quality and AI validation guide.'],
['Splash / Launch - Dark','Dark-mode reference variant.'],
['Login / Authentication - Dark','Dark-mode reference variant.'],
['Dashboard - Dark','Dark-mode reference variant.'],
['Market Overview - Dark','Dark-mode reference variant.'],
['Option Chain - Dark','Dark-mode reference variant.'],
['OI Heatmap - Dark','Dark-mode reference variant.'],
['Premium / Volume - Dark','Dark-mode reference variant.'],
['Greeks / IV Surface - Dark','Dark-mode reference variant.'],
['Order Flow - Dark','Dark-mode reference variant.'],
['All Indian Indices','All verified Indian market indices in one view.'],
['NSE Indices','NSE index universe; live values only from a connected source.'],
['BSE Indices','BSE index universe; live values only from a connected source.'],
['NSE Sub Companies','NSE equity universe with search; no fabricated company rows.'],
['BSE Sub Companies','BSE equity universe with search; no fabricated company rows.'],
['Angel One API','Server-side connection: Client ID, Access Token, MPIN and TOTP.'],
['NSE MCP Live Connect','Initialize and inspect the live NSE MCP bridge.'],
['System Health','Render backend, WebSocket, MCP, data source and paper-mode health.']
];

var state={index:'NIFTY',snap:null,decision:null,screen:1,online:false};
var API=((localStorage.getItem('nse_api_base')||'').replace(/\/$/,'')||'');
if(!API && location.protocol!=='file:' && location.hostname!=='localhost') API=location.origin;
if(!API) API='http://localhost:8000';

function $(s){return document.querySelector(s)}
function esc(v){return String(v==null?'—':v).replace(/[&<>"']/g,function(c){return({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]})}
function setTheme(mode){var t=mode==='dark'?'dark':'light';document.documentElement.dataset.theme=t;localStorage.setItem('nse_theme',t);var b=$('#theme');if(b)b.textContent=t==='dark'?'☀ Light':'☾ Dark'}
function card(title,value,sub,cls){return '<div class="metric '+(cls||'')+'"><small>'+esc(title)+'</small><b>'+esc(value)+'</b><span>'+esc(sub||'')+'</span></div>'}
function emptyState(msg){return '<div class="empty"><b>WAIT</b><p>'+esc(msg)+'</p><small>No unverified market values are displayed.</small></div>'}
function commonHeader(){return '<div class="page-head"><div><span class="eyebrow">SCREEN '+state.screen+' / '+screens.length+'</span><h1>'+esc(screens[state.screen-1][0])+'</h1><p>'+esc(screens[state.screen-1][1])+'</p></div><span class="status '+(state.online?'ok':'wait')+'">'+(state.online?'SERVER READY':'UI READY / BACKEND OFFLINE')+'</span></div>'}
function renderTabs(){var nav=$('#screen-tabs'),h='';for(var i=0;i<screens.length;i++){h+='<button type="button" class="tab '+(state.screen===i+1?'active':'')+'" data-screen="'+(i+1)+'"><b>'+(i+1)+'</b><span>'+esc(screens[i][0])+'</span></button>'}nav.innerHTML=h;nav.querySelectorAll('[data-screen]').forEach(function(b){b.addEventListener('click',function(){setScreen(Number(b.dataset.screen))})})}
function setScreen(n){if(n<1||n>screens.length)return;state.screen=n;renderTabs();renderDetail();var a=$('#screen-tabs .active');if(a)a.scrollIntoView({behavior:'smooth',block:'nearest',inline:'center'})}
function get(path){return fetch(API+path,{headers:{Accept:'application/json'}}).then(function(r){if(!r.ok)return r.text().then(function(t){throw Error(t||r.status)});return r.json()})}
function post(path,body){return fetch(API+path,{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json'},body:JSON.stringify(body||{})}).then(function(r){return r.json().then(function(d){if(!r.ok)throw Error(d.detail||d.message||'Request failed');return d})})}

function genericBody(){
 var s=state.snap||{},d=state.decision||{};
 return commonHeader()+'<div class="metrics">'+card('Index',state.index,'Selected')+card('Spot',s.spot==null?'—':s.spot,'Verified source')+card('Regime',s.regime||'—','Engine')+card('Verdict',d.verdict||'WAIT','Final gate')+'</div>'+emptyState(state.online?'This screen is connected and ready for verified payloads.':'Connect the Render backend in Settings.');
}
function chainBody(){
 var s=state.snap||{},rows=s.chain||[];
 if(!rows.length)return commonHeader()+emptyState('Option-chain data is unavailable.');
 var h=commonHeader()+'<div class="metrics">'+card('Spot',s.spot,'Source '+(s.source||'—'))+card('ATM',s.atm_strike,'Selected')+card('Quality',s.data_quality||'—','Gate')+card('Rows',rows.length,'Chain')+'</div><div class="tablewrap"><table><thead><tr><th>Strike</th><th>CE LTP</th><th>CE OI</th><th>CE ΔOI</th><th>CE Vol</th><th>PE LTP</th><th>PE OI</th><th>PE ΔOI</th><th>PE Vol</th></tr></thead><tbody>';
 rows.forEach(function(x){h+='<tr class="'+(x.strike===s.atm_strike?'atm':'')+'"><td>'+esc(x.strike)+'</td><td>'+esc(x.ce_ltp)+'</td><td>'+esc(x.ce_oi)+'</td><td>'+esc(x.ce_chg_oi)+'</td><td>'+esc(x.ce_vol)+'</td><td>'+esc(x.pe_ltp)+'</td><td>'+esc(x.pe_oi)+'</td><td>'+esc(x.pe_chg_oi)+'</td><td>'+esc(x.pe_vol)+'</td></tr>'});
 return h+'</tbody></table></div>';
}
function plansBody(){
 var d=state.decision||{},p=d.plans||[],h=commonHeader()+'<div class="metrics">'+card('Qualifying',p.length,'No padding')+card('Suppressed',d.suppressed_count||0,'Risk/data gate')+card('Verdict',d.verdict||'WAIT','Final')+card('Mode','PAPER','Live OFF')+'</div>';
 if(!p.length)return h+emptyState('No qualifying plan. The terminal does not fabricate a five-plan quota.');
 h+='<div class="tablewrap"><table><thead><tr><th>Side</th><th>Strike</th><th>Entry</th><th>SL</th><th>Target</th><th>R:R</th><th>Strategies</th></tr></thead><tbody>';
 p.forEach(function(x){h+='<tr><td class="'+(x.side==='CALL'?'up':'down')+'">'+esc(x.side)+'</td><td>'+esc(x.strike)+'</td><td>'+esc(x.entry)+'</td><td>'+esc(x.sl)+'</td><td>'+esc((x.targets||[]).join(' / '))+'</td><td>'+esc(x.rr)+'</td><td>'+esc((x.strategy_ids||[]).join(', '))+'</td></tr>'});
 return h+'</tbody></table></div>';
}
function registryBody(){return commonHeader()+'<div class="searchbar"><input id="strategy-q" placeholder="Search strategy ID or name…"><span>377 core + 25 advanced</span></div><div id="registry" class="registry"></div>'}
function aiBody(){return commonHeader()+'<div class="ai-actions"><button class="primary" id="server-ai">Run Server 6-Layer</button><button id="browser-ai">Run Browser Puter</button></div><div id="ai-results" class="layers"></div>'}
function settingsBody(){return commonHeader()+'<div class="settings"><label>Backend URL<input id="api-url" value="'+esc(API)+'" placeholder="https://your-render-service.onrender.com"></label><button class="primary" id="save-api">Save & Test Backend</button><div class="metrics">'+card('Source',state.snap&&state.snap.source||'—','Verified only')+card('Mode','PAPER','Live orders disabled')+card('Connection',state.online?'READY':'OFFLINE','Backend')+'</div></div>'}
function helpBody(){return commonHeader()+'<div class="help-grid"><article><b>OI 2×2</b><p>Price ↑ + OI ↑ = Long Buildup; Price ↓ + OI ↑ = Short Buildup; Price ↑ + OI ↓ = Short Covering; Price ↓ + OI ↓ = Long Unwinding.</p></article><article><b>Data quality</b><p>Stale, duplicate, missing OI or missing volume can block a signal.</p></article><article><b>AI guard</b><p>AI validates engine output and cannot invent strike, entry, SL, target or size.</p></article><article><b>Execution</b><p>PAPER/dry-run is default and live order placement is disabled.</p></article></div>'}

function indicesBody(group){
 var h=commonHeader()+'<div class="subtabs">';
 [['all','All Indices'],['nse','NSE'],['bse','BSE'],['nse-sub','NSE Subs'],['bse-sub','BSE Subs']].forEach(function(x){h+='<button class="'+(group===x[0]?'active':'')+'" data-index-group="'+x[0]+'">'+x[1]+'</button>'});
 h+='</div>';
 if(group==='nse-sub'||group==='bse-sub')return h+'<div class="searchbar"><input id="equity-q" placeholder="Search company / symbol…"><span>Verified master only</span></div><div id="equity-list" class="equity-list"></div>';
 var rows=group==='nse'?['NIFTY 50','NIFTY NEXT 50','NIFTY BANK','NIFTY FIN SERVICE','NIFTY MIDCAP SELECT']:group==='bse'?['SENSEX','BANKEX','BSE 100','BSE 200','BSE 500']:['NIFTY 50','NIFTY BANK','FINNIFTY','MIDCPNIFTY','SENSEX','BANKEX'];
 h+='<div class="index-grid">'+rows.map(function(x){return '<article><b>'+esc(x)+'</b><strong>—</strong><small>Connect verified feed for live value</small></article>'}).join('')+'</div>';
 return h+emptyState('Index names are navigation metadata. No fabricated prices are shown.');
}
function angelBody(){
 return commonHeader()+'<div class="connect-card"><div class="warning">Credentials are transmitted to the configured backend only. They are not written to localStorage or bundled into the APK.</div><div class="form-grid">'+
 '<label>Client ID<input id="angel-client-id" autocomplete="off"></label>'+
 '<label>Access Token<input id="angel-access-token" type="password" autocomplete="off"></label>'+
 '<label>MPIN<input id="angel-mpin" type="password" inputmode="numeric" autocomplete="off"></label>'+
 '<label>TOTP<input id="angel-totp" type="password" inputmode="numeric" autocomplete="off"></label>'+
 '</div><div class="ai-actions"><button class="primary" id="angel-connect">Test Angel One Connection</button><button id="angel-clear">Clear</button></div><div id="angel-status" class="empty"><b>DISCONNECTED</b><p>Live orders remain disabled.</p></div></div>';
}
function mcpBody(){
 return commonHeader()+'<div class="metrics">'+card('NSE MCP','Live bridge','Initialize + tools/list')+card('Transport','HTTP / SSE','Backend')+card('Mode','READ / ANALYZE','No live orders')+card('Status','—','Check now')+'</div><div class="ai-actions"><button class="primary" id="mcp-connect">Connect NSE MCP Live</button></div><div id="mcp-status" class="empty"><b>NOT CHECKED</b><p>Initialize the configured NSE MCP bridge.</p></div>';
}
function healthBody(){return commonHeader()+'<div id="health-grid" class="metrics">'+card('Render Backend',state.online?'READY':'OFFLINE','API')+card('NSE MCP','—','Bridge')+card('WebSocket','—','Live channel')+card('Orders','PAPER ONLY','Live disabled')+'</div>'}

function loadRegistry(q){return get('/api/strategies?q='+encodeURIComponent(q||'')).then(function(rows){var box=$('#registry');if(box)box.innerHTML=rows.map(function(x){return '<article><b>'+esc(x.id)+'</b><strong>'+esc(x.name)+'</strong><small>'+esc(x.family)+(x.advanced?' · ADVANCED':'')+'</small></article>'}).join('')||emptyState('No matching strategies.')}).catch(function(){var box=$('#registry');if(box)box.innerHTML=emptyState('Strategy registry unavailable.')})}
function loadEquities(board,q){return get('/api/equities?board='+encodeURIComponent(board)+'&q='+encodeURIComponent(q||'')).then(function(rows){var box=$('#equity-list');if(box)box.innerHTML=rows.map(function(x){return '<article><b>'+esc(x.symbol||x.tradingsymbol)+'</b><strong>'+esc(x.name||'—')+'</strong><small>'+esc(x.exchange||board)+'</small></article>'}).join('')||emptyState('No verified equity master is configured.')}).catch(function(){var box=$('#equity-list');if(box)box.innerHTML=emptyState('Equity master unavailable; no company rows are invented.')})}
function connectAngel(){
 var box=$('#angel-status');if(!box)return;box.innerHTML='<div class="empty"><b>CONNECTING…</b><p>Processing server-side.</p></div>';
 post('/api/angel/connect',{client_id:$('#angel-client-id').value.trim(),access_token:$('#angel-access-token').value.trim(),mpin:$('#angel-mpin').value.trim(),totp:$('#angel-totp').value.trim()}).then(function(d){box.innerHTML='<div class="empty"><b class="up">'+esc(d.status||'CONNECTED')+'</b><p>'+esc(d.message||'Angel One connection verified.')+'</p></div>'}).catch(function(e){box.innerHTML='<div class="empty"><b class="down">CONNECTION FAILED</b><p>'+esc(e.message)+'</p></div>'});
}
function connectMCP(){
 var box=$('#mcp-status');if(!box)return;box.innerHTML='<div class="empty"><b>CONNECTING…</b><p>Initializing NSE MCP.</p></div>';
 post('/api/mcp/connect',{}).then(function(d){box.innerHTML='<div class="empty"><b class="up">'+(d.connected?'CONNECTED':'NOT CONNECTED')+'</b><p>'+esc(d.message||'')+'</p><small>'+esc((d.tools||[]).join(' · '))+'</small></div>'}).catch(function(e){box.innerHTML='<div class="empty"><b class="down">MCP OFFLINE</b><p>'+esc(e.message)+'</p></div>'});
}
function runBrowserAI(){
 var box=$('#ai-results');if(!box)return;box.innerHTML='<div class="empty"><b>LOADING BROWSER AI…</b><p>Validation only.</p></div>';
 var s=document.createElement('script');s.src='https://js.puter.com/v2/';s.async=true;s.onload=function(){if(!window.puter||!puter.ai){box.innerHTML=emptyState('Puter AI unavailable.');return}puter.ai.chat('Validate only. Never invent strike, entry, stop-loss, target or size. Engine data: '+JSON.stringify({index:state.index,plans:(state.decision&&state.decision.plans)||[]}),{temperature:.1}).then(function(r){box.innerHTML='<div class="layer"><b>Browser AI</b><strong class="up">Validated</strong><small>'+esc(String(r&&r.message&&r.message.content||r).slice(0,500))+'</small></div>'}).catch(function(e){box.innerHTML=emptyState('Browser AI validation failed.')})};s.onerror=function(){box.innerHTML=emptyState('Puter script could not load.')};document.head.appendChild(s);
}
function renderDetail(){
 var n=state.screen,body;
 if(n===5||n===26)body=chainBody();else if(n===11)body=plansBody();else if(n===13)body=registryBody();else if(n===14)body=aiBody();else if(n===15)body=settingsBody();else if(n===21)body=helpBody();
 else if(n===31)body=indicesBody('all');else if(n===32)body=indicesBody('nse');else if(n===33)body=indicesBody('bse');else if(n===34)body=indicesBody('nse-sub');else if(n===35)body=indicesBody('bse-sub');else if(n===36)body=angelBody();else if(n===37)body=mcpBody();else if(n===38)body=healthBody();else body=genericBody();
 $('#detail').innerHTML=body;
 if(n===13){var q=$('#strategy-q');q.addEventListener('input',function(){loadRegistry(q.value)});loadRegistry('')}
 if(n===14){$('#server-ai').addEventListener('click',function(){post('/api/ai/validate',{index:state.index,plans:(state.decision&&state.decision.plans)||[],regime:state.snap&&state.snap.regime,data_quality:state.snap&&state.snap.data_quality}).then(function(d){$('#ai-results').innerHTML=(d.layers||[]).map(function(l){return '<article class="layer"><b>'+esc(l.layer)+' · '+esc(l.model)+'</b><strong class="'+(l.agrees?'up':'down')+'">'+(l.agrees?'Agrees':'Flagged')+'</strong><small>'+esc((l.concerns||[]).join(' · '))+'</small></article>'}).join('')}).catch(function(){ $('#ai-results').innerHTML=emptyState('Server AI unavailable.')})});$('#browser-ai').addEventListener('click',runBrowserAI)}
 if(n===15)$('#save-api').addEventListener('click',function(){var v=$('#api-url').value.trim().replace(/\/$/,'');if(v){localStorage.setItem('nse_api_base',v);API=v;refresh()}});
 if(n>=31&&n<=35){document.querySelectorAll('[data-index-group]').forEach(function(b){b.addEventListener('click',function(){var g=b.dataset.indexGroup;setScreen(g==='all'?31:g==='nse'?32:g==='bse'?33:g==='nse-sub'?34:35)})});var eq=$('#equity-q');if(eq){eq.addEventListener('input',function(){loadEquities(n===34?'NSE':'BSE',eq.value)});loadEquities(n===34?'NSE':'BSE','')}}
 if(n===36){$('#angel-connect').addEventListener('click',connectAngel);$('#angel-clear').addEventListener('click',function(){['angel-client-id','angel-access-token','angel-mpin','angel-totp'].forEach(function(id){$('#'+id).value=''})})}
 if(n===37)$('#mcp-connect').addEventListener('click',connectMCP);
 if(n===38){get('/api/mcp/health').then(function(d){$('#health-grid').children[1].querySelector('b').textContent=d.reachable?'CONNECTED':'OFFLINE'}).catch(function(){})}
}
function refresh(){
 $('#conn').textContent='Connecting…';
 return get('/api/config').then(function(c){$('#index').innerHTML=(c.indices||['NIFTY']).map(function(x){return '<option value="'+esc(x)+'">'+esc(x)+'</option>'}).join('');$('#index').value=state.index;return Promise.all([get('/api/snapshot/'+encodeURIComponent(state.index)),get('/api/decision/'+encodeURIComponent(state.index))])}).then(function(a){state.snap=a[0];state.decision=a[1];state.online=true;$('#conn').textContent='Server Ready';$('#source').textContent=state.snap.source||'SERVER';$('#verdict').textContent=state.decision.verdict||'WAIT'}).catch(function(){state.online=false;$('#conn').textContent='UI Ready · Backend Offline';$('#source').textContent='PAPER / LIVE OFF';$('#verdict').textContent='WAIT'}).then(function(){renderDetail()});
}

document.addEventListener('DOMContentLoaded',function(){
 if(screens.length<37)throw Error('Final terminal requires original 30 screens plus connectivity/index tabs');
 setTheme(localStorage.getItem('nse_theme')||'light');
 $('#theme').addEventListener('click',function(){setTheme(document.documentElement.dataset.theme==='dark'?'light':'dark')});
 $('#index').addEventListener('change',function(){state.index=this.value;refresh()});
 renderTabs();renderDetail();refresh();
});
