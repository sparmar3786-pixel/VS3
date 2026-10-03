"""Deterministic pipeline stage 17."""
def run(context):
 context.setdefault("stages",[]).append("part17")
 return context
