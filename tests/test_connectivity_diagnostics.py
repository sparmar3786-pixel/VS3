from fastapi.testclient import TestClient

from backend.app import app


def test_public_connectivity_diagnostics_do_not_require_terminal_token():
    client = TestClient(app)
    response = client.get("/v1/angel/status")
    assert response.status_code == 200
    assert "connected" in response.json()
