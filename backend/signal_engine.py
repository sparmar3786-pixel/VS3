"""Deterministic market decision layer; AI validates, never invents."""
from __future__ import annotations
from typing import Any
def _f(v:Any):
    try:return None if v is None else float(v)
    except (TypeError,ValueError):return None
def _rows(s):
    out=[]
    for x in getattr(s,"strikes",[]) or []:
        out.append({"strike":_f(getattr(x,"strike",None)),"ce_ltp":_f(getattr(x,"ce_ltp",None)),"pe_ltp":_f(getattr(x,"pe_ltp",None)),"ce_oi":_f(getattr(x,"ce_oi",None)),"pe_oi":_f(getattr(x,"pe_oi",None)),"ce_oi_change":_f(getattr(x,"ce_oi_change",None)),"pe_oi_change":_f(getattr(x,"pe_oi_change",None))})
    return [r for r in out if r["strike"] is not None]
def build_signal(snapshot:Any,*,source="unknown",max_age_sec=180.0,min_rr=1.8):
    if snapshot is None:return {"decision":"NO TRADE","reason":"NO_MARKET_DATA","source":source}
    spot=_f(getattr(snapshot,"spot",None)); rows=_rows(snapshot)
    if spot is None or spot<=0:return {"decision":"NO TRADE","reason":"INVALID_SPOT","source":source}
    if not rows:return {"decision":"NO TRADE","reason":"OPTION_CHAIN_EMPTY","source":source}
    support=max((r["strike"] for r in rows if r["strike"]<=spot),default=None,key=lambda k: next((x["pe_oi"] or 0 for x in rows if x["strike"]==k),0))
    resistance=max((r["strike"] for r in rows if r["strike"]>=spot),default=None,key=lambda k: next((x["ce_oi"] or 0 for x in rows if x["strike"]==k),0))
    ce=sum(r["ce_oi"] or 0 for r in rows); pe=sum(r["pe_oi"] or 0 for r in rows); pcr=pe/ce if ce else None
    near=min(rows,key=lambda r:abs(r["strike"]-spot)); c=near["ce_ltp"]; p=near["pe_ltp"]
    cs=ps=0; cr=[]; pr=[]
    if support is not None:cs+=2;cr.append(f"PE-OI support near {support:g}")
    if resistance is not None:ps+=2;pr.append(f"CE-OI resistance near {resistance:g}")
    if pcr is not None:
        if pcr>1.05:cs+=1;cr.append(f"PCR {pcr:.2f} bullish")
        elif pcr<0.95:ps+=1;pr.append(f"PCR {pcr:.2f} bearish")
    if (near["pe_oi_change"] or 0)>0:cs+=1;cr.append("ATM PE OI build-up")
    if (near["ce_oi_change"] or 0)>0:ps+=1;pr.append("ATM CE OI build-up")
    def risk(entry):
        if entry is None or entry<=0:return (None,None,None)
        sl=entry*.70; target=entry*1.60; return sl,target,(target-entry)/(entry-sl)
    csl,ct,crr=risk(c); psl,pt,prr=risk(p)
    cok=cs>=3 and crr is not None and crr>=min_rr; pok=ps>=3 and prr is not None and prr>=min_rr
    if cok and not pok: d,why,e,sl,t,rr="CALL BUY",cr,c,csl,ct,crr
    elif pok and not cok:d,why,e,sl,t,rr="PUT BUY",pr,p,psl,pt,prr
    elif cok and pok and cs!=ps:d,why,e,sl,t,rr=("CALL BUY",cr,c,csl,ct,crr) if cs>ps else ("PUT BUY",pr,p,psl,pt,prr)
    else:d,why,e,sl,t,rr="WAIT",["conflict or evidence gate not satisfied"],None,None,None,None
    return {"decision":d,"source":source,"spot":spot,"support":support,"resistance":resistance,"pcr":round(pcr,3) if pcr is not None else None,"strike":near["strike"],"option_entry":e,"stop_loss":sl,"target":t,"risk_reward":round(rr,2) if rr is not None else None,"call_score":cs,"put_score":ps,"why":why,"disclaimer":"Rule-based analysis; no profit guarantee."}
