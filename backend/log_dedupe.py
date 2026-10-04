from __future__ import annotations
import logging,time
from dataclasses import dataclass
@dataclass
class _Entry: total:int; suppressed:int; last_logged:float
class LogDedupe:
 def __init__(self,logger,repeat_every_sec=60.0,clock=time.monotonic):self._log=logger;self._every=repeat_every_sec;self._clock=clock;self._seen={}
 def warn(self,event,scope,kind,detail=""):
  k=(event,scope,kind);n=self._clock();e=self._seen.get(k)
  if e is None:self._seen[k]=_Entry(1,0,n);self._log.warning("%s scope=%s kind=%s %s",event,scope,kind,detail);return
  e.total+=1;e.suppressed+=1
  if n-e.last_logged>=self._every:self._log.warning("%s scope=%s kind=%s repeated x%d in last %.0fs (latest: %s)",event,scope,kind,e.suppressed,n-e.last_logged,detail);e.suppressed=0;e.last_logged=n
 def recovered(self,event,scope):
  keys=[k for k in self._seen if k[0]==event and k[1]==scope]
  if keys:self._log.info("%s scope=%s recovered after %d failure(s)",event,scope,sum(self._seen.pop(k).total for k in keys))
