from __future__ import annotations
import asyncio, datetime as dt, json, os, time
from collections import deque
import httpx, pyotp
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from SmartApi import SmartConnect

E=os.environ.get
MIN_RR=float(E("MIN_RR","2.0")); MAX_AGE=float(E("MAX_TICK_AGE_SEC","5")); POLL=float(E("POLL_SEC","2"))
DRIFT=float(E("MAX_RECHECK_DRIFT_PCT","0.15")); AI_REQUIRED=E("AI_REQUIRED","1")=="1"
MIN_OI=float(E("MIN_OI","50000")); MAX_SPREAD=float(E("MAX_SPREAD_PCT","1.5")); VOL_MULT=float(E("VOL_MULT","1.5")); PERSIST=int(E("PERSIST_CYCLES","2"))
IST=dt.timezone(dt.timedelta(hours=5,minutes=30))
SPOT={"NIFTY":("NSE","99926000",50,"NFO"),"BANKNIFTY":("NSE","99926009",100,"NFO"),"FINNIFTY":("NSE","99926037",50,"NFO"),"MIDCPNIFTY":("NSE","99926074",25,"NFO"),"SENSEX":("BSE","99919000",100,"BFO"),"BANKEX":("BSE","99919012",100,"BFO")}
LAYERS=[("Data collection",1),("Data verification",2),("Independent validation",3),("Quant / OI audit",4),("Market structure",5),("Final risk audit",6)]
MASTER="https://margincalculator.angelbroking.com/OpenAPI_Files/files/OpenAPIScripMaster.json"
STRATS={"Long Buildup":"S001","Short Buildup":"S002","Short Covering":"S003","Long Unwinding":"S004"}
HIST={"spot":{},"vol":{},"streak":{}}

class Feed:
 def __init__(self): self.api=None; self.chain={}; self.prev={}
 def login(self):
  keys=("ANGEL_API_KEY","ANGEL_CLIENT_ID","ANGEL_PIN","ANGEL_TOTP_SECRET"); missing=[k for k in keys if not E(k)]
  if missing: raise RuntimeError("Missing Angel environment variables: "+", ".join(missing))
  self.api=SmartConnect(api_key=E("ANGEL_API_KEY")); d=self.api.generateSession(E("ANGEL_CLIENT_ID"),E("ANGEL_PIN"),pyotp.TOTP(E("ANGEL_TOTP_SECRET")).now())
  if not d.get("status"): raise RuntimeError(f"Angel login failed: {d.get('message')}")
 async def load_master(self):
  async with httpx.AsyncClient(timeout=60) as c: r=await c.get(MASTER); r.raise_for_status(); rows=r.json()
  today=dt.date.today()
  for sym in SPOT:
   opts=[x for x in rows if x.get("name")==sym and x.get("instrumenttype")=="OPTIDX"]; exps=[]
   for x in opts:
    try:
     d=dt.datetime.strptime(x["expiry"],"%d%b%Y").date()
     if d>=today: exps.append(d)
    except (KeyError,ValueError): pass
   if not exps: self.chain[sym]=[]; continue
   exp=min(exps); self.chain[sym]=[{"token":x["token"],"symbol":x["symbol"],"strike":float(x["strike"])/100,"side":x["symbol"][-2:]} for x in opts if dt.datetime.strptime(x["expiry"],"%d%b%Y").date()==exp and x.get("symbol","").endswith(("CE","PE"))]
 def legs(self,sym,spot,n=3):
  step=SPOT[sym][2]; atm=round(spot/step)*step
  return [x for x in self.chain.get(sym,[]) if abs(x["strike"]-atm)<=n*step]
 def quote(self,wanted):
  out={}
  for ex,toks in wanted.items():
   for i in range(0,len(toks),50):
    r=self.api.getMarketData("FULL",{"exchangeTokens":{ex:toks[i:i+50]}})
    for q in (r.get("data") or {}).get("fetched",[]): out[str(q["symbolToken"])]=q
    if i+50<len(toks): time.sleep(1.1)
  return out

def age(q):
 try:
  raw=q.get("exchFeedTime")
  if not raw:return 1e9
  return time.time()-dt.datetime.strptime(raw,"%d-%b-%Y %H:%M:%S").timestamp()
 except (TypeError,ValueError,OverflowError):return 1e9

def quality(spot_q,leg_q):
 if not spot_q or not spot_q.get("ltp"):return False,"Missing spot"
 if age(spot_q)>MAX_AGE:return False,"Stale spot tick"
 for l,q in leg_q:
  if not q or not q.get("ltp") or q["ltp"]<=0:return False,f"Missing LTP {l['symbol']}"
  if q.get("opnInterest") is None or q.get("tradeVolume") is None:return False,f"Missing OI/volume {l['symbol']}"
 return True,"ok"

def klass(dp,doi):
 if dp>0:return "Long Buildup" if doi>0 else "Short Covering"
 return "Short Buildup" if doi>0 else "Long Unwinding"

def wait(x,why):
 for k in ("opt","strike","entry","sl","t","rr","conf","ids","side"):x.pop(k,None)
 x.update(verdict="WAIT",why=why)

def decide(sym,spot,legs,prev):
 if not legs:return {"verdict":"WAIT","why":"No option legs"}
 atm=min((l["strike"] for l,_ in legs),key=lambda s:abs(s-spot)); cls={}
 for l,q in legs:
  if l["strike"]!=atm:continue
  p=prev.get(l["token"])
  if not p or (p.get("ltp"),p.get("opnInterest"),p.get("tradeVolume"))==(q.get("ltp"),q.get("opnInterest"),q.get("tradeVolume")):return {"verdict":"WAIT","why":"Warming up or duplicate tick, no fresh evidence"}
  cls[l["side"]]=klass(q["ltp"]-p["ltp"],q["opnInterest"]-p["opnInterest"])
 bull={"Long Buildup","Short Covering"}; bear={"Short Buildup","Long Unwinding"}; call=cls.get("CE") in bull and cls.get("PE") in bear; put=cls.get("PE") in bull and cls.get("CE") in bear
 if not(call or put):return {"verdict":"WAIT","why":f"OI/premium disagree (CE {cls.get('CE')}, PE {cls.get('PE')})"}
 side="CE" if call else "PE"; leg,q=next((l,q) for l,q in legs if l["strike"]==atm and l["side"]==side)
 cand=[(l["strike"],q2["opnInterest"]) for l,q2 in legs if l["side"]==side and (l["strike"]>=spot if call else l["strike"]<=spot)]
 if not cand:return {"verdict":"WAIT","why":"No OI wall in range"}
 wall=max(cand,key=lambda z:z[1])[0]; entry=q["ltp"]; risk=entry*.20; t2=entry+.5*abs(wall-spot); t1=entry+.6*(t2-entry); rr=(t2-entry)/risk
 if rr<MIN_RR:return {"verdict":"WAIT","why":f"R:R 1 : {rr:.1f} below 1 : {MIN_RR} gate"}
 k=klass(q["ltp"]-prev[leg["token"]]["ltp"],q["opnInterest"]-prev[leg["token"]]["opnInterest"])
 return {"verdict":"CALL BUY" if call else "PUT BUY","opt":leg["symbol"],"strike":leg["strike"],"side":side,"entry":entry,"sl":entry-risk,"t":[t1,t2],"rr":rr,"conf":int(min(90,50+10*(rr-MIN_RR)+(10 if q["tradeVolume"]>prev[leg["token"]]["tradeVolume"] else 0))),"ids":[f"{STRATS[k]} {k}","S368 CALL Qualification" if call else "S369 PUT Qualification"],"token":leg["token"]}

def remember(prev,legs,sym,spot):
 HIST["spot"].setdefault(sym,deque(maxlen=6)).append(spot)
 for l,q in legs:
  p=prev.get(l["token"])
  if q and p and q.get("tradeVolume") is not None:HIST["vol"].setdefault(l["token"],deque(maxlen=10)).append(max(0,q["tradeVolume"]-p.get("tradeVolume",0)))
 prev.update({l["token"]:dict(q) for l,q in legs if q})

def qualify(sym,spot,legs,x,prev):
 if x["verdict"] not in ("CALL BUY","PUT BUY"):HIST["streak"].pop(sym,None);return
 call=x["verdict"]=="CALL BUY"; q=next(q for l,q in legs if l["token"]==x["token"])
 def oid(side):return sum(q2["opnInterest"]-prev[l["token"]]["opnInterest"] for l,q2 in legs if l["side"]==side and l["token"] in prev)
 dce,dpe=oid("CE"),oid("PE"); vh=list(HIST["vol"].get(x["token"],[])); vd=q["tradeVolume"]-prev[x["token"]]["tradeVolume"]; avg=sum(vh)/len(vh) if len(vh)>=3 else 0
 dep=q.get("depth") or {}; bid=((dep.get("buy") or [{}])[0]).get("price"); ask=((dep.get("sell") or [{}])[0]).get("price"); spr=(ask-bid)/((ask+bid)/2)*100 if bid and ask else 99
 s=list(HIST["spot"].get(sym,[])); now=dt.datetime.now(IST).time()
 checks=[("OI 2×2 both legs",True),("Chain OI agrees",(dpe-dce)>0 if call else (dce-dpe)>0),("Volume surge",avg>0 and vd>=VOL_MULT*avg),("Tight spread + OI",spr<=MAX_SPREAD and q["opnInterest"]>=MIN_OI),("Spot momentum",len(s)>=4 and (s[-1]>s[0] if call else s[-1]<s[0])),(f"R:R ≥ 1 : {MIN_RR:g}",x["rr"]>=MIN_RR),("Trading window",dt.time(9,30)<=now<=dt.time(15,0))]
 x["checks"]=[[n,bool(ok)] for n,ok in checks]; bad=[n for n,ok in checks if not ok]
 if bad:HIST["streak"].pop(sym,None);wait(x,f"Quality gate: {bad[0]} not met");return
 key=(x["verdict"],x["strike"]);st=HIST["streak"].get(sym);n=st[1]+1 if st and st[0]==key else 1;HIST["streak"][sym]=(key,n)
 if n<PERSIST:wait(x,f"Confirming {n}/{PERSIST} cycles");return
 x["conf"]=min(95,75+int(6*(x["rr"]-MIN_RR))+(5 if vd>=2*avg else 0))

async def ask(n,role,payload):
 base,key,model=E("AI_BASE_URL"),E("AI_API_KEY"),E(f"AI_MODEL_L{n}");out={"n":n,"role":role,"model":model or "-","s":"skipped","note":"AI layer not configured"}
 if not(base and key and model):return out
 msg=[{"role":"system","content":f'You are layer {n} ({role}). Check engine output for data errors or contradictions. Reply JSON only: {{"status":"pass|flag","note":"max 20 words"}}. Never propose strike, entry, stop loss, target or size.'},{"role":"user","content":json.dumps(payload)}]
 try:
  async with httpx.AsyncClient(timeout=20) as c:r=await c.post(f"{base.rstrip('/')}/chat/completions",headers={"Authorization":f"Bearer {key}"},json={"model":model,"messages":msg,"temperature":0});r.raise_for_status()
  j=json.loads(r.json()["choices"][0]["message"]["content"].strip().strip(chr(96)).removeprefix("json").strip())
  if j.get("status") in ("pass","flag"):out.update(s=j["status"],note=str(j.get("note",""))[:160])
 except Exception as e:out.update(s="skipped",note=f"AI error: {type(e).__name__}")
 return out

async def validate(x):
 safe={k:x[k] for k in ("sym","spot","verdict","opt","strike","entry","sl","t","rr","ids","checks") if k in x};layers=await asyncio.gather(*[ask(n,r,safe) for r,n in LAYERS]);flags=sum(l["s"]=="flag" for l in layers);skipped=sum(l["s"]=="skipped" for l in layers);x["ai"]={"layers":layers}
 if flags or(AI_REQUIRED and skipped):
  x.update(verdict="WAIT",why="AI final WAIT override" if flags else "AI validation unavailable")
  for k in ("opt","strike","entry","sl","t","rr","conf","ids"):x.pop(k,None)

feed=Feed();clients=set();last=None
async def loop():
 global last
 await asyncio.to_thread(feed.login);await feed.load_master();cycle=0
 while True:
  t0=time.time();cycle+=1;spots=await asyncio.to_thread(feed.quote,{"NSE":[v[1] for v in SPOT.values() if v[0]=="NSE"],"BSE":[v[1] for v in SPOT.values() if v[0]=="BSE"]});items=[];okall=True;ages=[]
  for sym,(ex,tok,_,fo) in SPOT.items():
   sq=spots.get(tok);spot=(sq or {}).get("ltp") or 0;x={"sym":sym,"spot":spot}
   if not spot:x.update(verdict="NO QUALIFYING TRADE",why="Missing spot");okall=False;items.append(x);continue
   lg=feed.legs(sym,spot);qs=await asyncio.to_thread(feed.quote,{fo:[l["token"] for l in lg]});legs=[(l,qs.get(l["token"])) for l in lg];good,note=quality(sq,legs);ages.append(age(sq))
   if not good:x.update(verdict="NO QUALIFYING TRADE",why=f"Data gate: {note}");okall=False
   else:
    x.update(decide(sym,spot,legs,feed.prev));qualify(sym,spot,legs,x,feed.prev)
    if x["verdict"] in ("CALL BUY","PUT BUY"):
     r=(await asyncio.to_thread(feed.quote,{fo:[x["token"]]})).get(x["token"])
     if not r or abs(r["ltp"]-x["entry"])/x["entry"]*100>DRIFT:wait(x,"Recheck failed: price moved or tick missing")
     else:await validate(x)
   remember(feed.prev,legs,sym,spot);x.pop("token",None);items.append(x)
  last={"cycle":cycle,"ts":int(time.time()*1000),"dq":{"ok":okall,"age_ms":int(max(ages or [0])*1000)},"items":items,"paper_only":True}
  for ws in list(clients):
   try:await ws.send_json(last)
   except Exception:clients.discard(ws)
  await asyncio.sleep(max(0,POLL-(time.time()-t0)))

async def supervised():
 while True:
  try:await loop()
  except asyncio.CancelledError:raise
  except Exception as e:print("engine error:",repr(e));await asyncio.sleep(5)

app=FastAPI(title="Vandana1 Signal Engine",version="1.0")
@app.on_event("startup")
async def start_engine():asyncio.create_task(supervised())
@app.get("/health")
def health():return {"ok":True,"cycle":(last or {}).get("cycle",0),"paper_only":True,"order_placement":False}
@app.get("/signals")
def signals():return last or {"cycle":0,"items":[],"paper_only":True,"status":"warming_up"}
@app.websocket("/ws/signals")
async def ws_signals(ws:WebSocket):
 await ws.accept();clients.add(ws)
 try:
  if last:await ws.send_json(last)
  while True:await ws.receive_text()
 except (WebSocketDisconnect,Exception):clients.discard(ws)
