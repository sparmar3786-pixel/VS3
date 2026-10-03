from .config import settings
def risk_gate(entry,sl,target,min_rr=None):
 risk=entry-sl; rr=(target-entry)/risk if risk>0 else 0
 return rr>=(min_rr if min_rr is not None else settings.min_rr),rr
def closed_verdict(side): return "CALL BUY" if side=="CE" else "PUT BUY" if side=="PE" else "WAIT"
