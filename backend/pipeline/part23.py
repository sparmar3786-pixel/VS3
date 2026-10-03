"""Deterministic pipeline stage 23."""
def run(context):
 context.setdefault("stages",[]).append("part23")
 return context
