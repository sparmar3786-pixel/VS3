"""Deterministic pipeline stage 13."""
def run(context):
 context.setdefault("stages",[]).append("part13")
 return context
