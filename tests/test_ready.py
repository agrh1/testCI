from __future__ import annotations

from app import app


def test_ready_endpoint_ok() -> None:
    client = app.test_client()
    resp = client.get("/ready")
    assert resp.status_code == 200

    data = resp.get_json()
    assert data is not None
    assert data.get("status") == "ok"
