"""Deterministic pipeline stage 07."""
def run(context):
 context.setdefault("stages",[]).append("part07")
 return context
