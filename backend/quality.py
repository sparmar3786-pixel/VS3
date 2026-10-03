from datetime import datetime,timezone
def age_seconds(ts):
 try:return max(0,(datetime.now(timezone.utc)-datetime.fromisoformat(ts.replace("Z","+00:00"))).total_seconds())
 except:return float("inf")
def data_quality(s,max_age=15):
 if not s.calls or not s.puts:return False,"DATA_GAP: missing CE/PE leg"
 if age_seconds(s.timestamp)>max_age:return False,"DATA_GAP: stale snapshot"
 for x in s.calls+s.puts:
  if x.ltp is None or x.oi is None or x.volume is None:return False,"DATA_GAP: missing observable field"
  if x.ltp<0 or x.oi<0 or x.volume<0:return False,"DATA_GAP: invalid value"
 return True,"OK"
