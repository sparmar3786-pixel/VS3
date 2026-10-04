from __future__ import annotations
import asyncio,json,os,re
from pathlib import Path
class DiskSnapshotStore:
 def __init__(self,directory):self._dir=Path(directory)
 def _path(self,index):return self._dir/f"chain_{re.sub(r'[^A-Za-z0-9_-]','_',index)}.json"
 def _save_sync(self,index,snap):
  self._dir.mkdir(parents=True,exist_ok=True);p=self._path(index);tmp=p.with_name(p.name+".tmp")
  try:
   with open(tmp,"w",encoding="utf-8") as f:json.dump(snap,f)
   os.replace(tmp,p)
  except BaseException:tmp.unlink(missing_ok=True);raise
 def _load_sync(self,index):
  try:
   with open(self._path(index),encoding="utf-8") as f:return json.load(f)
  except FileNotFoundError:return None
 async def save(self,index,snap):await asyncio.to_thread(self._save_sync,index,snap)
 async def load(self,index):return await asyncio.to_thread(self._load_sync,index)
