"""Deterministic pipeline stage 03."""
def run(context):
 context.setdefault("stages",[]).append("part03")
 return context
