"""Part 02 — Data Quality Engine (locked gate)."""
from __future__ import annotations
from datetime import datetime, timezone
from backend.models import DataQualityFlag, DataQualityReport
from backend.pipeline.base import PartResult, register
from backend.pipeline.context import PipelineContext

def evaluate_quality(ctx: PipelineContext)->DataQualityReport:
    s=ctx.settings; snap=ctx.snapshot; rep=DataQualityReport()
    now=datetime.now(timezone.utc); ts=snap.timestamp
    if ts.tzinfo is None: ts=ts.replace(tzinfo=timezone.utc)
    age=(now-ts).total_seconds(); rep.age_sec=age
    if age>s.max_snapshot_age_sec: rep.fail(DataQualityFlag.STALE,f"snapshot age {age:.1f}s > {s.max_snapshot_age_sec}s")
    seen=set()
    for t in ctx.ticks:
        key=(t.symbol,t.timestamp)
        if key in seen: rep.fail(DataQualityFlag.DUPLICATE,f"duplicate tick {t.symbol}@{t.timestamp}")
        seen.add(key)
        tts=t.timestamp if t.timestamp.tzinfo else t.timestamp.replace(tzinfo=timezone.utc)
        t_age=(now-tts).total_seconds()
        if t_age>s.max_tick_age_sec: rep.fail(DataQualityFlag.STALE,f"tick {t.symbol} age {t_age:.1f}s")
        if t.close and t.ltp and t.close>0:
            jump=abs(t.ltp-t.close)/t.close*100
            if jump>s.max_tick_jump_pct: rep.fail(DataQualityFlag.ABNORMAL,f"tick {t.symbol} jump {jump:.1f}%")
    strikes=snap.strikes
    if not strikes: rep.fail(DataQualityFlag.GAP,"empty option chain")
    seen_strikes=set(); missing_oi=missing_vol=0
    for st in strikes:
        if st.strike<=0 or st.strike in seen_strikes: rep.fail(DataQualityFlag.INVALID_STRIKE,f"invalid/dup strike {st.strike}")
        seen_strikes.add(st.strike)
        if st.ce_oi is None or st.pe_oi is None: missing_oi+=1
        if st.ce_volume is None or st.pe_volume is None: missing_vol+=1
    if missing_oi>len(strikes)*0.5: rep.fail(DataQualityFlag.MISSING_OI,f"{missing_oi}/{len(strikes)} strikes missing OI")
    if missing_vol>len(strikes)*0.5: rep.fail(DataQualityFlag.MISSING_VOLUME,f"{missing_vol}/{len(strikes)} strikes missing volume")
    if ctx.ticks:
        last_tick=max(t.timestamp for t in ctx.ticks)
        if last_tick.tzinfo is None: last_tick=last_tick.replace(tzinfo=timezone.utc)
        if ts<last_tick: rep.fail(DataQualityFlag.OUT_OF_ORDER,"snapshot older than newest tick")
    return rep

@register(2)
def run(ctx: PipelineContext)->PartResult:
    rep=evaluate_quality(ctx); ctx.put("dq",rep); ctx.snapshot.data_quality=rep
    res=PartResult(part=2,name="Data Quality Engine",ok=rep.passed,data_gap=not rep.passed)
    res.output={"passed":rep.passed,"flags":[f.value for f in rep.flags],"reasons":rep.reasons,"age":rep.age_sec}
    if not rep.passed: ctx.flag("DATA_QUALITY_FAIL: "+"; ".join(rep.reasons))
    return res
