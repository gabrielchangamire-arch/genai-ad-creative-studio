from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def _client(tmp_path) -> TestClient:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'campaigns.db'}",
        generation_mode="mock",
        provider_api_key=None,
        provider_base_url=None,
        provider_model=None,
        frontend_origins=("http://localhost:5173",),
    )
    return TestClient(create_app(settings))


def test_campaign_workflow(tmp_path):
    client = _client(tmp_path)
    campaign_payload = {
        "product_name": "Signal Desk",
        "product_description": "A dashboard that turns support trends into weekly action plans.",
        "target_audience": "customer success leaders",
        "tone": "practical",
        "objective": "book more product demos",
    }

    create_response = client.post("/api/campaigns", json=campaign_payload)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["product_name"] == "Signal Desk"
    assert created["creative_set"] is None

    list_response = client.get("/api/campaigns")
    assert list_response.status_code == 200
    assert [campaign["id"] for campaign in list_response.json()] == [created["id"]]

    get_response = client.get(f"/api/campaigns/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["objective"] == campaign_payload["objective"]

    generate_response = client.post(f"/api/campaigns/{created['id']}/generate")
    assert generate_response.status_code == 200
    creative_set = generate_response.json()["creative_set"]
    assert len(creative_set["headlines"]) == 3
    assert "Signal Desk" in creative_set["headlines"][0]
    assert len(creative_set["campaign_concepts"]) == 3
