from fastapi.routing import APIRoute
from backend.app import app


def test_pdf_v1_contract_routes_are_mounted():
    paths = {r.path for r in app.routes}
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
    assert any(getattr(r, "path", None) == "/v1/ws" for r in app.routes)
