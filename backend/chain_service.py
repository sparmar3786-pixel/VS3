from __future__ import annotations
import asyncio,logging,math,time
from dataclasses import dataclass
from typing import Any,Awaitable,Callable,Dict,Optional
from backend.log_dedupe import LogDedupe
LIVE="LIVE"; DEGRADED="DEGRADED"; DATA_GAP="DATA_GAP"
class AuthError(Exception): pass
class EmptyChainError(Exception): pass
@dataclass(frozen=True)
class ChainResult:
 data:Any; snapshot_id:Optional[str]; fetched_at:Optional[float]; age_sec:Optional[float]; source:str; state:str; trade_allowed:bool; reason:Optional[str]=None
@dataclass(frozen=True)
class _Snap:
 data:Any; fetched_at:float; snapshot_id:str
class OptionChainService:
 def __init__(self,fetch:Callable[[str],Awaitable[Any]],store=None,*,ttl_sec=12.0,live_max_sec=15.0,degraded_max_sec=60.0,backoff_sec=15.0,fetch_timeout_sec=8.0,relogin=None,relogin_cooldown_sec=30.0,is_auth_error=None,dedupe=None,wall_clock=time.time,mono_clock=time.monotonic):
  if not 0<ttl_sec<=live_max_sec<=degraded_max_sec: raise ValueError("need 0 < ttl_sec <= live_max_sec <= degraded_max_sec")
  self._fetch,self._store=fetch,store; self.ttl_sec,self.live_max_sec=ttl_sec,live_max_sec; self.degraded_max_sec,self.backoff_sec=degraded_max_sec,backoff_sec
  self.fetch_timeout_sec,self.relogin_cooldown_sec=fetch_timeout_sec,relogin_cooldown_sec; self._relogin=relogin
  self._is_auth=is_auth_error or (lambda e:isinstance(e,AuthError)); self._dedupe=dedupe or LogDedupe(logging.getLogger("vs3.chain"))
  self._wall,self._mono=wall_clock,mono_clock; self._mem={}; self._locks={}; self._fail_until={}
  self._relogin_lock=None; self._relogin_gen=0; self._last_relogin_try=-math.inf
  self.metrics={"angel_calls":0,"memory_hits":0,"refresh_failures":0,"fallbacks":0,"data_gaps":0}
 def classify(self,age):
  if age is None or age>self.degraded_max_sec:return DATA_GAP,False
  if age<=self.live_max_sec:return LIVE,True
  return DEGRADED,True
 def _age(self,s):return max(0.0,self._wall()-s.fetched_at)
 def _result(self,s,source):
  age=self._age(s); state,allowed=self.classify(age)
  if not allowed:return ChainResult(None,s.snapshot_id,s.fetched_at,age,source,DATA_GAP,False,"stale")
  return ChainResult(s.data,s.snapshot_id,s.fetched_at,age,source,state,True)
 async def get(self,index):
  key=index.upper(); s=self._mem.get(key)
  if s and self._age(s)<self.ttl_sec:self.metrics["memory_hits"]+=1;return self._result(s,"memory")
  lock=self._locks.setdefault(key,asyncio.Lock())
  async with lock:
   s=self._mem.get(key)
   if s and self._age(s)<self.ttl_sec:self.metrics["memory_hits"]+=1;return self._result(s,"memory")
   if self._mono()>=self._fail_until.get(key,0):
    fresh=await self._refresh(key)
    if fresh:return self._result(fresh,"angel")
   return await self._fallback(key)
 async def _fetch_snapshot(self,index):
  self.metrics["angel_calls"]+=1; data=await asyncio.wait_for(self._fetch(index),self.fetch_timeout_sec)
  if data is None or (hasattr(data,"__len__") and len(data)==0):raise EmptyChainError(index)
  t=self._wall();return _Snap(data,t,f"{index}-{int(t*1000)}")
 async def _refresh(self,index):
  gen=self._relogin_gen
  try:s=await self._fetch_snapshot(index)
  except Exception as e:
   if self._is_auth(e) and await self._try_relogin(gen):
    try:s=await self._fetch_snapshot(index)
    except Exception as e2:return self._failed(index,e2)
   else:return self._failed(index,e)
  self._mem[index]=s;await self._persist(index,s);self._dedupe.recovered("chain_refresh_failed",index);self._dedupe.recovered("using_cache",index);return s
 def _failed(self,index,e):
  self._fail_until[index]=self._mono()+self.backoff_sec;self.metrics["refresh_failures"]+=1;self._dedupe.warn("chain_refresh_failed",index,type(e).__name__,str(e));return None
 async def _try_relogin(self,seen):
  if self._relogin is None:return False
  self._relogin_lock=self._relogin_lock or asyncio.Lock()
  async with self._relogin_lock:
   if self._relogin_gen!=seen:return True
   now=self._mono()
   if now-self._last_relogin_try<self.relogin_cooldown_sec:return False
   self._last_relogin_try=now
   try:await self._relogin()
   except Exception as e:self._dedupe.warn("relogin_failed","angel",type(e).__name__,str(e));return False
   self._relogin_gen+=1;return True
 async def _persist(self,index,s):
  if self._store is None:return
  try:await self._store.save(index,{"data":s.data,"fetched_at":s.fetched_at,"snapshot_id":s.snapshot_id})
  except Exception as e:self._dedupe.warn("snapshot_save_failed",index,type(e).__name__,str(e))
 async def _load(self,index):
  if self._store is None:return None
  try:
   raw=await self._store.load(index)
   if not raw:return None
   t=float(raw["fetched_at"])
   if not math.isfinite(t) or t>self._wall()+5:raise ValueError("bad fetched_at")
   return _Snap(raw["data"],t,str(raw.get("snapshot_id") or f"{index}-{int(t*1000)}"))
  except Exception as e:self._dedupe.warn("snapshot_load_failed",index,type(e).__name__,str(e));return None
 async def _fallback(self,index):
  c=[];m=self._mem.get(index)
  if m:c.append(("memory_stale",m))
  d=await self._load(index)
  if d:c.append(("disk",d))
  best=None;freshest=None
  for source,s in c:
   if freshest is None or s.fetched_at>freshest.fetched_at:freshest=s
   r=self._result(s,source)
   if r.trade_allowed and (best is None or r.age_sec<best.age_sec):best=r
  if best:self.metrics["fallbacks"]+=1;self._dedupe.warn("using_cache",index,best.source,f"age={best.age_sec:.1f}s");return best
  self.metrics["data_gaps"]+=1
  if freshest is None:return ChainResult(None,None,None,None,"none",DATA_GAP,False,"no_snapshot")
  return ChainResult(None,None,freshest.fetched_at,self._age(freshest),"none",DATA_GAP,False,"stale")
def annotate_decision(decision:dict,chain:ChainResult,*,degraded_conf_penalty:float):
 out=dict(decision);out.update(data_state=chain.state,data_age_sec=chain.age_sec,data_source=chain.source,snapshot_id=chain.snapshot_id)
 if not chain.trade_allowed:out["signal"]="NO TRADE";out["reason"]="DATA_GAP";return out
 if chain.state==DEGRADED:
  out["data_degraded"]=True;c=out.get("confidence")
  if isinstance(c,(int,float)) and not isinstance(c,bool):out["confidence"]=max(0.0,c-degraded_conf_penalty)
 return out
