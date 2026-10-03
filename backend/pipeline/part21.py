"""Deterministic pipeline stage 21."""
def run(context):
 context.setdefault("stages",[]).append("part21")
 return context
