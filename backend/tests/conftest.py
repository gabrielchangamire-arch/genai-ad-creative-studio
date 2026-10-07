import pytest
from app.config import Settings
from app.schemas import CampaignRead


@pytest.fixture
def settings(tmp_path):
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        generation_mode="provider",
        provider_api_key="test-only-key",
        provider_base_url="https://api.openai.com/v1",
        provider_model="gpt-5-mini",
        frontend_origins=("http://localhost:5173",),
        max_retries=2,
    )


@pytest.fixture
def campaign():
    return CampaignRead(
        id="test-campaign",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        product_name="Signal Desk",
        product_description="A dashboard for weekly support review.",
        target_audience="Support managers",
        tone="practical",
        objective="Book demos",
    )
