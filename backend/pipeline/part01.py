"""Deterministic pipeline stage 01."""
def run(context):
 context.setdefault("stages",[]).append("part01")
 return context
