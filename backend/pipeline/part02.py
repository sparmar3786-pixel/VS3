"""Deterministic pipeline stage 02."""
def run(context):
 context.setdefault("stages",[]).append("part02")
 return context
