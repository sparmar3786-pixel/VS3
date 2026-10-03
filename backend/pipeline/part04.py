"""Deterministic pipeline stage 04."""
def run(context):
 context.setdefault("stages",[]).append("part04")
 return context
