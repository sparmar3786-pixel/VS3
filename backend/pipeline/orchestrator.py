"""TerminalEngine — per-cycle 32-part pipeline orchestrator."""
from __future__ import annotations
import asyncio
import inspect
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Optional
from loguru import logger
from backend.config import get_settings
from backend.market_cache import cache_age_sec, is_market_open, load_snapshot, save_snapshot
from backend.pipeline.chain_cache import ChainCache, ChainResult
from backend.models import Decision, Snapshot, Tick
from backend.pipeline import loader  # noqa: F401
from backend.pipeline.base import REGISTRY
from backend.pipeline.context import PipelineContext

CYCLE_SECONDS = 5.0
Broadcast = Callable[[str, Any], Awaitable[None]]

class TerminalEngine:
    def __init__(self, memory=None, broadcaster: Optional[Broadcast]=None) -> None:
        self.settings=get_settings(); self.memory=memory; self.broadcaster=broadcaster
        self._source=None; self._ai=None; self._running=False
        self._snapshots: Dict[str,Snapshot]={}; self._decisions: Dict[str,Decision]={}
        self._prev_snapshots: Dict[str,Snapshot]={}; self._contexts: Dict[str,PipelineContext]={}
        self._ticks={i:deque(maxlen=500) for i in self.settings.index_list}
        self._last_bias: Dict[str,float]={}; self._cycle=0
        self._mcp_source=None; self._mcp_task=None
        self._mcp_snapshots: Dict[str,Snapshot]={}; self._mcp_updated: Dict[str,float]={}
        self._after_market_ai_at: Dict[str,float]={}
        self._log_seen: Dict[tuple[str,str,str], float] = {}
        self._chain_cache = ChainCache(
            ttl_sec=self.settings.chain_cache_ttl_sec,
            stale_sec=self.settings.chain_stale_sec,
            failure_backoff_sec=self.settings.chain_failure_backoff_sec,
        )

    async def ensure_source(self):
        if self._source is None:
            from backend.brokers.factory import get_data_source
            self._source=get_data_source()
        return self._source

    async def connect_source(self)->None:
        source=await self.ensure_source()
        try:
            if not getattr(source,"connected",False):
                await source.connect()
        except Exception as e:
            logger.warning("engine: primary live source unavailable ({})",type(e).__name__)
        if self.settings.ai_on and self._ai is None:
            from backend.ai.six_layer_ai import build_ai_client
            self._ai=build_ai_client(self.settings)
        self._running=True
        if self.settings.mcp_on and self._mcp_task is None:
            self._mcp_task=asyncio.create_task(self._mcp_refresh_loop(),name="nse-mcp-chain-cache")

    async def start(self)->None:
        await self.connect_source()
        logger.info("engine: started (source={}, indices={})",getattr(self._source,"name","?"),self.settings.index_list)

    async def stop(self)->None:
        self._running=False
        if self._mcp_task:
            self._mcp_task.cancel()
            try: await self._mcp_task
            except BaseException: pass
            self._mcp_task=None
        if self._mcp_source is not None:
            try: await self._mcp_source.close()
            except Exception: pass
            self._mcp_source=None
        if self._source is not None:
            try: await self._source.close()
            except Exception: pass

    async def run_forever(self)->None:
        while True:
            try:
                if not self._running:
                    await self.start()
                await self.run_cycle()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._running=False
                logger.error("engine: startup/cycle error: {}",e)
                await asyncio.sleep(5.0)
            await asyncio.sleep(self.settings.engine_cycle_sec)

    async def run_cycle(self)->None:
        self._cycle+=1
        if self._source is not None and not getattr(self._source,"connected",False):
            await self.connect_source()
        for index in self.settings.index_list:
            try:
                decision=await self._cycle_for_index(index)
                if decision is not None:
                    self._decisions[index]=decision
                    if self.broadcaster:
                        await self.broadcaster("decision",decision.model_dump(mode="json"))
            except Exception as e:
                key=("cycle_failed", index, type(e).__name__)
                if time.monotonic() - self._log_seen.get(key, 0.0) >= 60.0:
                    self._log_seen[key]=time.monotonic()
                    logger.warning("engine: {} cycle failed ({})",index,type(e).__name__)
        if self.broadcaster: await self.broadcaster("state",self.state_frame())

    async def _mcp_refresh_loop(self)->None:
        """Continuously read NSE MCP option-chain data without replacing Angel live data."""
        try:
            from backend.mcp.mcp_client import MCPSource
            self._mcp_source=MCPSource()
            await self._mcp_source.connect()
            if getattr(self._mcp_source,"_active",None) is None:
                logger.warning("nse-mcp: no active MCP server; background chain cache disabled")
                return
            while self._running:
                for index in self.settings.index_list:
                    try:
                        snap=await self._mcp_source.get_option_chain(index)
                        if snap is not None:
                            snap.source="nse_mcp"
                            self._mcp_snapshots[index]=snap
                            self._mcp_updated[index]=time.time()
                    except Exception as e:
                        key=("mcp_chain_failed", index, type(e).__name__)
                        if time.monotonic() - self._log_seen.get(key, 0.0) >= 60.0:
                            self._log_seen[key]=time.monotonic()
                            logger.warning("nse-mcp: {} chain refresh failed ({})",index,type(e).__name__)
                await asyncio.sleep(max(5.0,self.settings.nse_mcp_poll_sec))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("nse-mcp: background reader stopped ({})",type(e).__name__)

    async def _refresh_source_auth(self) -> None:
        if self._source is None:
            return
        try:
            self._source._connected = False
        except Exception:
            pass
        await self._source.connect()

    async def _chain_result(self, index: str, live: bool) -> ChainResult:
        if not live:
            snap = load_snapshot(index) if self.settings.market_cache_on else None
            age = cache_age_sec(index)
            if snap is not None:
                return ChainResult(snap, max(0.0, age or 0.0),
                                   getattr(snap, "source", "disk"), "MARKET_CLOSED", False)
            return ChainResult(None, max(0.0, age or 0.0), "none", "MARKET_CLOSED", False)

        return await self._chain_cache.get_chain(
            index,
            lambda: self._source.get_option_chain(index),
            disk_fallback=load_snapshot,
            disk_age=cache_age_sec,
            auth_refresh=self._refresh_source_auth,
        )

    async def _cycle_for_index(self,index:str)->Optional[Decision]:
        assert self._source is not None
        live=is_market_open()
        chain=await self._chain_result(index, live)
        snapshot=chain.data

        if snapshot is None:
            if chain.state != "MARKET_CLOSED":
                key=("data_gap", index, chain.state)
                if time.monotonic() - self._log_seen.get(key, 0.0) >= 60.0:
                    self._log_seen[key]=time.monotonic()
                    logger.warning("engine: {} data gap state={} age={}s",
                                   index, chain.state, round(chain.age_sec,1))
            return None

        if chain.state == "FRESH" and self.settings.market_cache_on:
            save_snapshot(snapshot, source=chain.source)

        snapshot.data_quality=None
        self._snapshots[index]=snapshot
        if live:
            try:
                tick=await self._source.get_quote(index,token=index)
                if tick is not None:self._ticks[index].append(tick)
            except Exception: pass
        ctx=PipelineContext(index=index,snapshot=snapshot,settings=self.settings,
                            ticks=deque(self._ticks[index],maxlen=500),
                            prev_snapshot=self._prev_snapshots.get(index))
        ctx.put("_memory",self.memory)
        ctx.put("market_open",live)
        ctx.put("snapshot_source",chain.source)
        ctx.put("snapshot_cache_age_sec",chain.age_sec)
        ctx.put("chain_state",chain.state)
        ctx.put("trade_allowed",chain.trade_allowed)
        ctx.put("nse_mcp_snapshot",self._mcp_snapshots.get(index))
        ctx.put("nse_mcp_age_sec",self._mcp_updated.get(index))
        ai_allowed=self._ai is not None
        if not live:
            now=time.monotonic()
            last=self._after_market_ai_at.get(index,0.0)
            ai_allowed=ai_allowed and (now-last >= self.settings.after_market_ai_interval_sec)
            if ai_allowed:self._after_market_ai_at[index]=now
        ctx.put("_ai",self._ai if ai_allowed else None)
        ctx.put("cross_index",dict(self._last_bias))
        for part in sorted(REGISTRY):
            fn=REGISTRY[part]; res=fn(ctx)
            if inspect.isawaitable(res):res=await res
            ctx.results.append(res)
        self._prev_snapshots[index]=snapshot
        self._contexts[index]=ctx
        self._last_bias[index]=(ctx.get("oi") or {}).get("bias",0.0)
        return ctx.get("decision")

    def latest_snapshot(self,index:str)->Optional[Snapshot]:
        return self._snapshots.get(index.upper())

    def latest_decision(self,index:str)->Optional[Decision]:
        return self._decisions.get(index.upper())

    def latest_context(self,index:str)->Optional[PipelineContext]:
        return self._contexts.get(index.upper())

    async def ai_validate(self,index:str)->Dict[str,Any]:
        if self._ai is None:
            return {"enabled":False,"reason":"AI validation is disabled","layers":[],"wait_override":False}
        ctx=self.latest_context(index)
        if ctx is None:
            return {"enabled":True,"degraded":True,"reason":"no live engine context yet","layers":[],"wait_override":False}
        return await self._ai.validate(ctx)

    def state_frame(self)->Dict[str,Any]:
        return {
            "cycle":self._cycle,
            "timestamp":datetime.now(timezone.utc).isoformat(),
            "source":getattr(self._source,"name","none"),
            "advanced":self.settings.advanced_enabled,
            "market_open":is_market_open(),
            "snapshots":{k:{"spot":v.spot,"atm":v.atm_strike,"expiry":v.expiry,"strikes":len(v.strikes),
                             "source":v.source,"cache_age_sec":cache_age_sec(k)} for k,v in self._snapshots.items()},
            "nse_mcp":{k:{"age_sec":max(0.0,time.time()-t),"source":"mcp","strikes":len(self._mcp_snapshots[k].strikes)}
                       for k,t in self._mcp_updated.items() if k in self._mcp_snapshots},
            "decisions":{k:{"verdict":v.verdict.value,"plans":v.plans_qualifying,"suppressed":v.plans_suppressed} for k,v in self._decisions.items()},
        }

    async def run_strategy_scan(self,index:str)->Dict[str,Any]:
        decision=await self._cycle_for_index(index)
        if decision is None:return {"error":f"no decision for {index}"}
        return decision.model_dump(mode="json")
