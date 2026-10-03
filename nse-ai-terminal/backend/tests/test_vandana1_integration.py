import importlib
from pathlib import Path

def test_active_backend_exposes_vandana_routes():
    main = importlib.import_module("main")
    routes = {getattr(r, "path", "") for r in main.app.routes}
    assert "/health" in routes
    assert "/v1/angel/login" in routes
    assert "/v1/option-chain" in routes
    assert "/v1/strategy/refresh" in routes
    assert "/v1/ai/context" in routes
    assert "/v1/ai/validate" in routes

def test_vandana_backend_is_isolated_from_demo_engine_modules():
    adapter = importlib.import_module("vandana1_adapter")
    assert Path(adapter.VANDANA_ROOT).name == "vandana1"
