import asyncio,unittest
from backend.chain_service import *
from backend.log_dedupe import LogDedupe
from tests.helpers import Clock,FakeAngel,ListLogger,MemStore
def make(angel=None,store=None,clock=None,**kw):
 clock=clock or Clock();angel=angel or FakeAngel()
 logger=kw.pop("logger",ListLogger());kw.setdefault("dedupe",LogDedupe(logger,clock=clock))
 return OptionChainService(angel.get_option_chain,store,wall_clock=clock,mono_clock=clock,**kw),angel,clock,logger
class ServiceTests(unittest.IsolatedAsyncioTestCase):
 async def test_ttl_and_single_flight(self):
  svc,a,c,_=make(angel=FakeAngel(.02));rs=await asyncio.gather(*[svc.get("NIFTY") for _ in range(10)])
  self.assertEqual(a.calls,1);self.assertTrue(all(r.state==LIVE for r in rs))
  c.advance(5);r=await svc.get("NIFTY");self.assertEqual(a.calls,1);self.assertEqual(r.source,"memory")
 async def test_expiry(self):
  svc,a,c,_=make();r1=await svc.get("NIFTY");c.advance(12);r2=await svc.get("NIFTY")
  self.assertEqual(a.calls,2);self.assertNotEqual(r1.snapshot_id,r2.snapshot_id)
 async def test_stale_and_gap(self):
  svc,a,c,_=make();await svc.get("NIFTY");a.error=RuntimeError("down");c.advance(30)
  r=await svc.get("NIFTY");self.assertEqual((r.state,r.trade_allowed),(DEGRADED,True))
  c.advance(31);r=await svc.get("NIFTY");self.assertEqual((r.state,r.data,r.trade_allowed),(DATA_GAP,None,False))
 async def test_backoff(self):
  svc,a,c,_=make();a.error=RuntimeError("down");await svc.get("NIFTY");c.advance(5);await svc.get("NIFTY");self.assertEqual(a.calls,1)
  c.advance(10.1);await svc.get("NIFTY");self.assertEqual(a.calls,2)
 async def test_auth_relogin(self):
  a=FakeAngel();a.authed=False;calls=[]
  async def login():calls.append(1);a.authed=True
  svc,_,_,_=make(a,relogin=login);r=await svc.get("NIFTY")
  self.assertEqual(r.state,LIVE);self.assertEqual((a.calls,len(calls)),(2,1))
 async def test_disk_age_uses_original_time(self):
  store,c=MemStore(),Clock();svc,_,_,_=make(store=store,clock=c);r1=await svc.get("NIFTY");c.advance(30)
  a=FakeAngel();a.error=RuntimeError("down");svc2,_,_,_=make(a,store=store,clock=c);r2=await svc2.get("NIFTY")
  self.assertEqual(r2.source,"disk");self.assertAlmostEqual(r2.age_sec,30);self.assertEqual(r2.fetched_at,r1.fetched_at)
class GateTests(unittest.TestCase):
 def test_boundaries(self):
  svc,_,_,_=make()
  self.assertEqual(svc.classify(15),(LIVE,True));self.assertEqual(svc.classify(15.01),(DEGRADED,True));self.assertEqual(svc.classify(60.01),(DATA_GAP,False))
 def test_annotation(self):
  c=ChainResult(None,"s",1.0,61,"none",DATA_GAP,False,"stale")
  self.assertEqual(annotate_decision({"signal":"CALL","confidence":.8},c,degraded_conf_penalty=.1)["signal"],"NO TRADE")
if __name__=="__main__":unittest.main()
