import logging

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "test-only-api-token")
    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize("authorization", [None, "Bearer invalid", "Bearer", "Basic test-only-api-token"])
def test_rejects_missing_or_invalid_token(api, authorization):
    headers = {} if authorization is None else {"Authorization": authorization}
    response = api.get("/v1/reference/SGD", headers=headers)
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_reference_and_correlation(api, caplog):
    headers = {"Authorization": "Bearer test-only-api-token", "x-request-id": "request-123"}
    with caplog.at_level(logging.INFO, logger="reference-api"):
        response = api.get("/v1/reference/sgd", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"code": "SGD", "name": "Singapore Dollar"}
    assert response.headers["x-request-id"] == "request-123"
    assert "test-only-api-token" not in caplog.text
    assert api.get("/v1/reference/USD", headers=headers).json()["code"] == "USD"
    assert api.get("/v1/reference/XXX", headers=headers).status_code == 404
    assert api.get("/livez").status_code == 200
    assert api.get("/readyz").status_code == 200
    assert api.get("/metrics/").status_code == 200


@pytest.mark.parametrize("token", [None, "", " ", "bad token", "bad\ntoken"])
def test_token_required_at_startup(monkeypatch, token):
    if token is None:
        monkeypatch.delenv("API_TOKEN", raising=False)
    else:
        monkeypatch.setenv("API_TOKEN", token)
    with pytest.raises(RuntimeError, match="API_TOKEN"):
        with TestClient(app):
            pass


def test_token_rotation_on_restart(monkeypatch):
    for token in ["first-test-token", "replacement-test-token"]:
        monkeypatch.setenv("API_TOKEN", token)
        with TestClient(app) as client:
            assert client.get("/v1/reference/SGD", headers={"Authorization": f"Bearer {token}"}).status_code == 200
            if token == "replacement-test-token":
                assert client.get("/v1/reference/SGD", headers={"Authorization": "Bearer first-test-token"}).status_code == 401
        assert app.state.api_token == b""
