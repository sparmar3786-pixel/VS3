"""Part 22 — Time Engine (session phase, time-of-day, last-hour behaviour). """
from __future__ import annotations
from datetime import datetime
from zoneinfo import ZoneInfo
from backend.pipeline.base import PartResult, register
from backend.pipeline.context import PipelineContext
_IST=ZoneInfo("Asia/Kolkata")
@register(22)
def run(ctx: PipelineContext)->PartResult:
    now=datetime.now(_IST); minutes=now.hour*60+now.minute; open_m,close_m=9*60+15,15*60+30; phase="pre"
    if open_m<=minutes<9*60+45: phase="opening_range"
    elif minutes<12*60: phase="morning"
    elif minutes<14*60: phase="afternoon"
    elif minutes<=close_m: phase="last_hour"
    out={"ist_time":now.strftime("%H:%M:%S"),"phase":phase,"last_hour":phase=="last_hour","market_open":open_m<=minutes<=close_m and now.weekday()<5}
    ctx.put("time",out); return PartResult(part=22,name="Time Engine",output=out)
