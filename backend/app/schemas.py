from datetime import datetime

from pydantic import BaseModel, Field


class CampaignCreate(BaseModel):
    product_name: str = Field(min_length=2, max_length=120)
    product_description: str = Field(min_length=10, max_length=1200)
    target_audience: str = Field(min_length=3, max_length=240)
    tone: str = Field(min_length=3, max_length=80)
    objective: str = Field(min_length=3, max_length=240)


class CreativeSet(BaseModel):
    headlines: list[str]
    descriptions: list[str]
    calls_to_action: list[str]
    campaign_concepts: list[str]


class CampaignRead(CampaignCreate):
    id: str
    created_at: datetime
    updated_at: datetime
    creative_set: CreativeSet | None = None


class HealthRead(BaseModel):
    status: str

