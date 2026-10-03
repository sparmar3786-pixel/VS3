"""Deterministic pipeline stage 12."""
def run(context):
 context.setdefault("stages",[]).append("part12")
 return context
