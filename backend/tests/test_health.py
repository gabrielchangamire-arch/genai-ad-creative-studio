from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def test_health_check(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'health.db'}",
        generation_mode="mock",
        provider_api_key=None,
        provider_base_url=None,
        provider_model=None,
        frontend_origins=("http://localhost:5173",),
    )
    client = TestClient(create_app(settings))

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
