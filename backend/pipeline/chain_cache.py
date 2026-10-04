"""Compatibility facade: TerminalEngine keeps its existing API while all option-chain
fetching is delegated to OptionChainService (TTL/single-flight/backoff/age gate)."""
from __future__ import annotations
import asyncio
from typing import Awaitable,Callable,Optional
from backend.chain_service import OptionChainService,ChainResult,DEGRADED,DATA_GAP
from backend.brokers.base import AuthError as BrokerAuthError
from backend.snapshot_store import DiskSnapshotStore

class ChainCache:
 def __init__(self,*,ttl_sec=15.0,stale_sec=60.0,failure_backoff_sec=15.0,store=None):
  self.ttl_sec=ttl_sec;self.stale_sec=stale_sec;self.failure_backoff_sec=failure_backoff_sec
  self._store=store
  self._services={}
 def _service(self,index,fetch,disk_fallback,disk_age,auth_refresh):
  key=index.upper()
  svc=self._services.get(key)
  if svc is None:
   async def wrapped(i):return await fetch()
   async def save(i,snap):
    if self._store is not None:return await self._store.save(i,snap)
    return None
   async def load(i):
    if self._store is not None:return await self._store.load(i)
    snap=disk_fallback(i)
    if snap is None:return None
    age=disk_age(i)
    if age is None:return None
    # Preserve original fetch time from Snapshot.timestamp; never use file mtime.
    return {"data":snap,"fetched_at":snap.timestamp.timestamp(),
            "snapshot_id":f"{i}-{int(snap.timestamp.timestamp()*1000)}"}
   class Adapter:
    async def save(self,i,snap):await save(i,snap)
    async def load(self,i):return await load(i)
   async def relogin():
    if auth_refresh is not None:await auth_refresh()
   svc=OptionChainService(wrapped,Adapter(),ttl_sec=self.ttl_sec,
       live_max_sec=min(15.0,self.stale_sec),degraded_max_sec=self.stale_sec,
       backoff_sec=self.failure_backoff_sec,relogin=relogin,
       is_auth_error=lambda e:isinstance(e,BrokerAuthError))
   self._services[key]=svc
  return svc
 async def get_chain(self,index:str,fetch:Callable[[],Awaitable],*,disk_fallback,disk_age,auth_refresh=None)->ChainResult:
  return await self._service(index,fetch,disk_fallback,disk_age,auth_refresh).get(index)
 @property
 def metrics(self):
  out={"angel_calls":0,"memory_hits":0,"refresh_failures":0,"fallbacks":0,"data_gaps":0}
  for s in self._services.values():
   for k,v in s.metrics.items():out[k]=out.get(k,0)+v
  return out
