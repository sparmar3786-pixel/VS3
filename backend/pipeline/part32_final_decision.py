"""Part 32 — Final Decision. Single risk/R:R gate, data-quality gate, confidence gate and AI WAIT override. Never pads plans."""
from __future__ import annotations
from backend.models import Decision,OverrideAction,Regime,Side,TradePlan,Verdict
from backend.pipeline.base import PartResult,register
from backend.pipeline.context import PipelineContext
from backend.pipeline.part25_risk_engine import TUNING,passes_risk_gate,position_size
def _step(ctx:PipelineContext)->float:
    ks=sorted(s.strike for s in ctx.snapshot.strikes); diffs=[b-a for a,b in zip(ks,ks[1:]) if b-a>0]; return min(diffs) if diffs else 50.0
def _build_plan(ctx:PipelineContext,side:Side,strike:float,strategy_ids:list[str])->tuple[TradePlan|None,str]:
    row=next((s for s in ctx.snapshot.strikes if s.strike==strike),None)
    if row is None:return None,"missing_strike"
    opt=side.value; entry=getattr(row,f"{opt.lower()}_ltp"); bid=getattr(row,f"{opt.lower()}_bid"); ask=getattr(row,f"{opt.lower()}_ask")
    if entry is None or entry<=0:return None,"missing_premium"
    liq=ctx.get("liquidity") or {}
    if liq.get("low_liquidity"):return None,"low_liquidity"
    if bid is not None and ask is not None and entry and (ask-bid)>0.05*entry:return None,"wide_spread"
    sl_dist=max(TUNING["premium_sl_pct"]*entry,0.05); sl=round(entry-sl_dist,2); min_rr=ctx.settings.min_rr
    t1=round(entry+min_rr*sl_dist,2); t2=round(entry+(min_rr+0.6)*sl_dist,2); t3=round(entry+(min_rr+1.2)*sl_dist,2); rr=round((t1-entry)/sl_dist,2) if sl_dist>0 else 0.0
    if not passes_risk_gate(rr,min_rr):return None,"below_min_rr"
    lot=ctx.settings.lot_size(ctx.index); size=position_size(TUNING["capital_inr"],ctx.settings.max_risk_per_trade,entry,sl,lot)
    return TradePlan(plan_id=f"{ctx.index}-{opt}-{strike:g}",index=ctx.index,side=side,strike=strike,option_type=opt,entry=round(entry,2),stop_loss=sl,targets=[t1,t2,t3],trailing_sl_plan="move SL to break-even after T1; trail at 0.5*SL-dist after T2",time_exit="square-off by 15:15 IST or on regime flip",rr=rr,position_size=size,confidence=ctx.get("confidence",0.0),strategy_ids=strategy_ids,regime=Regime(ctx.get("regime")) if ctx.get("regime") else None),"ok"
@register(32)
def run(ctx:PipelineContext)->PartResult:
    dq=ctx.get("dq"); override=ctx.get("override") or {}; oi=ctx.get("oi") or {}; ce=ctx.get("ce_engine") or {}; pe=ctx.get("pe_engine") or {}; ai=ctx.get("ai") or {}; conflict=ctx.get("conflict") or {}
    decision=Decision(index=ctx.index); decision.data_quality=dq; decision.regime=Regime(ctx.get("regime")) if ctx.get("regime") else None; decision.ai_summary=ai
    if dq is not None and not dq.passed:
        decision.verdict=Verdict.WAIT; decision.notes.append("DATA_QUALITY_FAIL -> NO SIGNAL (gate 374)"); ctx.put("decision",decision); return PartResult(part=32,name="Final Decision",data_gap=True,output={"verdict":decision.verdict.value})
    action=override.get("action","NONE"); decision.override=OverrideAction(action); decision.override_reason=override.get("reason","")
    net=oi.get("bias",0.0)+ce.get("score",0.0)*0.5+pe.get("score",0.0)*0.5; side=Side.CALL if net>=0 else Side.PUT; confidence=ctx.get("confidence",0.0); min_conf=TUNING["min_confidence"]
    results=ctx.ensure_strategy_scan(); confirming=[r.strategy_id for r in results if r.fired and r.side==side]
    if not confirming:confirming=(oi.get("per_strike") and ["S001"]) or ["S001"]
    if action==OverrideAction.BLOCK.value or conflict.get("conflict"):
        decision.verdict=Verdict.WAIT; decision.notes.append("blocked: opposite-side/strategy conflict"); ctx.put("decision",decision); return PartResult(part=32,name="Final Decision",output={"verdict":decision.verdict.value})
    if abs(net)<0.05:
        decision.verdict=Verdict.WAIT; decision.notes.append("directional evidence too weak -> WAIT"); ctx.put("decision",decision); return PartResult(part=32,name="Final Decision",output={"verdict":decision.verdict.value})
    if confidence<min_conf:
        decision.verdict=Verdict.WAIT; decision.notes.append(f"confidence {confidence:.2f} < {min_conf} -> WAIT"); ctx.put("decision",decision); return PartResult(part=32,name="Final Decision",output={"verdict":decision.verdict.value})
    atm=ctx.get("atm_strike"); step=_step(ctx); candidates=[]
    if atm is not None:
        for k in [atm+i*step for i in range(-2,3)]:
            plan,reason=_build_plan(ctx,side,k,confirming[:6])
            if plan is not None:candidates.append(plan)
            else:decision.suppression_reasons.append(f"{side.value} {k:g}: {reason}")
    decision.plans=candidates; decision.plans_qualifying=len(candidates); decision.plans_suppressed=len(decision.suppression_reasons)
    if ai.get("wait_override"):
        decision.verdict=Verdict.WAIT; decision.notes.append("AI final WAIT override (layer 362)"); ctx.put("decision",decision); return PartResult(part=32,name="Final Decision",output={"verdict":decision.verdict.value})
    if candidates:
        decision.verdict=Verdict.CALL_BUY if side==Side.CALL else Verdict.PUT_BUY
        if len(candidates)<ctx.settings.min_trade_plans:decision.notes.append(f"only {len(candidates)} plan(s) qualified (target {ctx.settings.min_trade_plans}); {decision.plans_suppressed} suppressed: {'; '.join(decision.suppression_reasons[:5])}")
    else:
        decision.verdict=Verdict.NO_QUALIFYING_TRADE; decision.notes.append(f"direction {side.value} but 0 plans passed the gates; {decision.plans_suppressed} suppressed: {'; '.join(decision.suppression_reasons[:5])}")
    ctx.put("decision",decision)
    return PartResult(part=32,name="Final Decision",output={"verdict":decision.verdict.value,"plans":decision.plans_qualifying,"suppressed":decision.plans_suppressed})
