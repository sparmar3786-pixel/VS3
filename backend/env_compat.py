from __future__ import annotations
import logging,os
log=logging.getLogger("vs3.config")
def resolve_angel_client_id(env=None):
 env=os.environ if env is None else env
 new=(env.get("ANGEL_CLIENT_ID") or "").strip()
 if new:return new
 old=(env.get("ANGEL_CLIENT_CODE") or "").strip()
 if old:log.warning("ANGEL_CLIENT_CODE is deprecated; rename it to ANGEL_CLIENT_ID")
 return old
