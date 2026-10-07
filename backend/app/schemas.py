from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class CampaignCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
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


class GeneratedCreativeSet(BaseModel):
    """New outputs have bounds; historical sets remain readable without data loss."""

    model_config = ConfigDict(extra="forbid", strict=True)
    headlines: list[
        Annotated[
            str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
        ]
    ] = Field(min_length=1, max_length=5)
    descriptions: list[
        Annotated[
            str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)
        ]
    ] = Field(min_length=1, max_length=5)
    calls_to_action: list[
        Annotated[
            str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)
        ]
    ] = Field(min_length=1, max_length=5)
    campaign_concepts: list[
        Annotated[
            str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
        ]
    ] = Field(min_length=1, max_length=5)


class GenerationMetadata(BaseModel):
    mode: Literal["mock", "provider", "legacy"]
    request_id: str
    provider_request_id: str | None = None
    model: str | None = None
    attempts: int = 0
    latency_ms: float = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None


class GenerationResult(BaseModel):
    creative_set: CreativeSet
    metadata: GenerationMetadata


class CreativeVersion(BaseModel):
    version: int
    created_at: datetime
    creative_set: CreativeSet
    metadata: GenerationMetadata


class CampaignRead(CampaignCreate):
    id: str
    created_at: datetime
    updated_at: datetime
    creative_set: CreativeSet | None = None
    creative_versions: list[CreativeVersion] = Field(default_factory=list)


class HealthRead(BaseModel):
    status: str
