from __future__ import annotations
from enum import Enum
class OIClass(str,Enum):
    LONG_BUILDUP="LONG_BUILDUP";SHORT_BUILDUP="SHORT_BUILDUP";SHORT_COVERING="SHORT_COVERING";LONG_UNWINDING="LONG_UNWINDING";NEUTRAL="NEUTRAL"
def classify_oi(price_change:float,oi_change:float)->str:
    p=float(price_change);o=float(oi_change)
    if p>0 and o>0:return OIClass.LONG_BUILDUP.value
    if p<0 and o>0:return OIClass.SHORT_BUILDUP.value
    if p>0 and o<0:return OIClass.SHORT_COVERING.value
    if p<0 and o<0:return OIClass.LONG_UNWINDING.value
    return OIClass.NEUTRAL.value
def chain_bias(rows):
    score=0.0
    for r in rows:
        score += r.get("ce_oi",0)-r.get("pe_oi",0)
    return "CALL" if score>0 else "PUT" if score<0 else "NEUTRAL"
