from backend.app import app

def _routes(routes):
    for route in routes:
        nested = getattr(route, "routes", None)
        if nested is not None:
            yield from _routes(nested)
        else:
            yield route

def test_pdf_v1_contract_routes_are_mounted():
    paths = {r.path for r in _routes(app.routes) if getattr(r, "path", None)}
    expected = {
        "/health",
        "/v1/angel/status",
        "/v1/angel/login",
        "/v1/angel/market",
        "/v1/angel/option-chain",
        "/v1/nse/mcp/tools",
        "/v1/nse/mcp/context",
        "/v1/nse/option-chain.csv",
        "/v1/ai/context",
        "/v1/terminal",
    }
    assert expected.issubset(paths)

def test_pdf_v1_websocket_contract_is_mounted():
    assert any(getattr(r, "path", None) == "/v1/ws" for r in _routes(app.routes))
