import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
pytestmark = [pytest.mark.integration]


def test_root_serves_sales_landing_page():
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Yahoo Finance data via API" in response.text
    assert "href=\"/dashboard/#/overview\"" in response.text
    assert "href=\"/docs\"" in response.text


def test_docs_serves_scalar_explorer_with_no_code_quickstarts():
    response = client.get("/docs")

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "@scalar/api-reference" in response.text
    assert "data-url=\"/openapi.json\"" in response.text
    assert "Zapier quickstart" in response.text
    assert "Make quickstart" in response.text


def test_openapi_json_available_for_interactive_docs():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["openapi"].startswith("3.")
    assert payload["info"]["title"] == "Y Finance API"
    security_schemes = payload.get("components", {}).get("securitySchemes", {})
    assert "APIKeyHeader" in security_schemes
    assert security_schemes["APIKeyHeader"].get("type") == "apiKey"
