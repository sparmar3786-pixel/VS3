"""SQLite strategy memory for observations, trades and failure-pattern analysis."""
from __future__ import annotations
import json,sqlite3,threading
from datetime import datetime,timezone
from pathlib import Path
from typing import Any,Dict,List,Optional

class StrategyMemory:
 def __init__(self,db_path:str="data/strategy_memory.sqlite")->None:
  self.db_path=db_path;Path(db_path).parent.mkdir(parents=True,exist_ok=True);self._lock=threading.Lock();self._init_db()
 def _connect(self):
  c=sqlite3.connect(self.db_path,check_same_thread=False);c.row_factory=sqlite3.Row;return c
 def _init_db(self):
  with self._lock,self._connect() as c:
   c.execute("""CREATE TABLE IF NOT EXISTS observations(
    id INTEGER PRIMARY KEY AUTOINCREMENT,ts TEXT NOT NULL,index_name TEXT,regime TEXT,strategy TEXT,
    strike REAL,side TEXT,entry REAL,oi REAL,premium REAL,volume INTEGER,iv REAL,greeks TEXT,
    expiry TEXT,day_time TEXT,result TEXT,confidence REAL,extra TEXT)""")
   c.execute("""CREATE TABLE IF NOT EXISTS trades(
    id INTEGER PRIMARY KEY AUTOINCREMENT,ts TEXT NOT NULL,strategy TEXT,index_name TEXT,side TEXT,
    strike REAL,entry REAL,exit REAL,r REAL,result TEXT,regime TEXT,expiry TEXT,strike_distance REAL,
    day_time TEXT,is_expiry INTEGER,extra TEXT)""")
 def record_observation(self,rec:Dict[str,Any])->None:
  with self._lock,self._connect() as c:
   c.execute("INSERT INTO observations(ts,index_name,regime,strategy,strike,side,entry,oi,premium,volume,iv,greeks,expiry,day_time,result,confidence,extra) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
    (datetime.now(timezone.utc).isoformat(),rec.get("index"),rec.get("regime"),rec.get("strategy"),rec.get("strike"),rec.get("side"),rec.get("entry"),rec.get("oi"),rec.get("premium"),rec.get("volume"),rec.get("iv"),_j(rec.get("greeks")),rec.get("expiry"),rec.get("time"),rec.get("result"),rec.get("confidence"),_j(rec.get("extra"))))
 def record_trade(self,t:Dict[str,Any])->None:
  with self._lock,self._connect() as c:
   c.execute("INSERT INTO trades(ts,strategy,index_name,side,strike,entry,exit,r,result,regime,expiry,strike_distance,day_time,is_expiry,extra) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
    (datetime.now(timezone.utc).isoformat(),t.get("strategy_id"),t.get("index"),t.get("side"),t.get("strike"),t.get("entry"),t.get("exit"),t.get("r"),t.get("result"),t.get("regime"),t.get("expiry"),t.get("strike_distance"),t.get("time"),1 if t.get("is_expiry") else 0,_j(t.get("extra"))))
 def strategy_summary(self,index:str)->Dict[str,Any]:
  with self._lock,self._connect() as c: rows=c.execute("SELECT r,result FROM trades WHERE index_name=?",(index,)).fetchall()
  rs=[float(x["r"]) for x in rows if x["r"] is not None];n=len(rs);wins=sum(r>0 for r in rs)
  return {"n":n,"win_rate":round(wins/n,4) if n else None,"average_r":round(sum(rs)/n,4) if n else None,"note":"sample statistic — not a forward promise"}
 def regime_behaviour(self,regime:Optional[str],index:str)->Dict[str,Any]:
  with self._lock,self._connect() as c:r=c.execute("SELECT COUNT(*) AS c FROM observations WHERE regime=? AND index_name=?",(regime,index)).fetchone()
  return {"regime":regime,"index":index,"observations":int(r["c"] if r else 0)}
 def failure_patterns(self,limit:int=20)->List[Dict[str,Any]]:
  with self._lock,self._connect() as c:rows=c.execute("SELECT strategy,index_name,regime,COUNT(*) AS losses FROM trades WHERE r IS NOT NULL AND r<=0 GROUP BY strategy,index_name,regime ORDER BY losses DESC LIMIT ?",(limit,)).fetchall()
  return [dict(x) for x in rows]
 def trades_for_backtest(self,index:Optional[str]=None)->List[Dict[str,Any]]:
  q="SELECT * FROM trades";args=()
  if index:q+=" WHERE index_name=?";args=(index,)
  with self._lock,self._connect() as c:rows=c.execute(q,args).fetchall()
  out=[]
  for row in rows:
   d=dict(row);d["is_expiry"]=bool(d.get("is_expiry"));out.append(d)
  return out

def _j(v:Any)->Optional[str]:
 if v is None:return None
 try:return json.dumps(v,default=str)
 except Exception:return str(v)
