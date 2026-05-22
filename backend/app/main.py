from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .schemas import CampaignCreate, CampaignRead, CreativeSet, HealthRead
from .services.generation import (
    CopyGenerator,
    GenerationConfigurationError,
    GenerationProviderError,
)
from .store import CampaignStore


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    store = CampaignStore(resolved_settings.database_url)
    store.initialize()
    generator = CopyGenerator(resolved_settings)

    app = FastAPI(title="GenAI Ad Creative Studio API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.frontend_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", response_model=HealthRead)
    def health() -> HealthRead:
        return HealthRead(status="ok")

    @app.post(
        "/api/campaigns",
        response_model=CampaignRead,
        status_code=status.HTTP_201_CREATED,
    )
    def create_campaign(payload: CampaignCreate) -> dict:
        return store.create_campaign(payload)

    @app.get("/api/campaigns", response_model=list[CampaignRead])
    def list_campaigns() -> list[dict]:
        return store.list_campaigns()

    @app.get("/api/campaigns/{campaign_id}", response_model=CampaignRead)
    def get_campaign(campaign_id: str) -> dict:
        campaign = store.get_campaign(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found.")

        return campaign

    @app.post(
        "/api/campaigns/{campaign_id}/generate",
        response_model=CampaignRead,
    )
    def generate_campaign_copy(campaign_id: str) -> dict:
        campaign = store.get_campaign(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail="Campaign not found.")

        try:
            creative_set: CreativeSet = generator.create_set(CampaignRead.model_validate(campaign))
        except GenerationConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except GenerationProviderError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        saved_campaign = store.save_creative_set(campaign_id, creative_set)
        if not saved_campaign:
            raise HTTPException(status_code=404, detail="Campaign not found.")

        return saved_campaign

    return app


app = create_app()

