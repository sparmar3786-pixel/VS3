"""Part 21 — Cross-Index Engine (ADVANCED). Compares this index's bias against the other tracked indices. Requires the orchestrator to publish a cross_index map; otherwise DATA_GAP (never guessed). """
from __future__ import annotations
from backend.pipeline.base import PartResult, register
from backend.pipeline.context import PipelineContext
@register(21)
def run(ctx: PipelineContext)->PartResult:
    if not ctx.advanced:return PartResult(part=21,name="Cross-Index Engine",skipped=True,notes=["advanced engine disabled"])
    cross=ctx.get("cross_index") or {}
    if len(cross)<2:
        ctx.put("cross_index_res",{"data_gap":True}); return PartResult(part=21,name="Cross-Index Engine",data_gap=True,notes=["need >=2 indices for relative analysis"])
    my=cross.get(ctx.index,0.0); others={k:v for k,v in cross.items() if k!=ctx.index}; avg_other=sum(others.values())/len(others)
    out={"self_bias":my,"others_avg":avg_other,"relative_strength":round(my-avg_other,4),"divergence":bool((my>0.2 and avg_other<-0.2) or (my<-0.2 and avg_other>0.2)),"leadership":max(cross,key=lambda k:abs(cross[k])) if cross else None}
    ctx.put("cross_index_res",out); return PartResult(part=21,name="Cross-Index Engine",output=out)
