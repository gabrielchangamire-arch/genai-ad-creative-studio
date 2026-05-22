import json

import httpx

from ..config import Settings
from ..schemas import CampaignRead, CreativeSet


class GenerationConfigurationError(RuntimeError):
    pass


class GenerationProviderError(RuntimeError):
    pass


class CopyGenerator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def create_set(self, campaign: CampaignRead) -> CreativeSet:
        if self.settings.generation_mode == "mock":
            return _mock_creative_set(campaign)

        if self.settings.generation_mode == "provider":
            return self._provider_creative_set(campaign)

        raise GenerationConfigurationError(
            "GENERATION_MODE must be set to mock or provider."
        )

    def _provider_creative_set(self, campaign: CampaignRead) -> CreativeSet:
        if not self.settings.provider_api_key:
            raise GenerationConfigurationError(
                "GENAI_PROVIDER_API_KEY is required in provider mode."
            )

        if not self.settings.provider_base_url:
            raise GenerationConfigurationError(
                "GENAI_PROVIDER_BASE_URL is required in provider mode."
            )

        request_body = {
            "model": self.settings.provider_model,
            "campaign": campaign.model_dump(mode="json", exclude={"creative_set"}),
            "output_schema": {
                "headlines": ["string"],
                "descriptions": ["string"],
                "calls_to_action": ["string"],
                "campaign_concepts": ["string"],
            },
        }

        try:
            response = httpx.post(
                self.settings.provider_base_url,
                headers={"Authorization": f"Bearer {self.settings.provider_api_key}"},
                json=request_body,
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise GenerationProviderError("Provider generation request failed.") from exc

        creative_payload = payload.get("creative_set", payload)
        try:
            return CreativeSet.model_validate(creative_payload)
        except ValueError as exc:
            raise GenerationProviderError(
                "Provider response did not match the creative set schema."
            ) from exc


def _mock_creative_set(campaign: CampaignRead) -> CreativeSet:
    product = campaign.product_name.strip()
    audience = campaign.target_audience.strip()
    tone = campaign.tone.strip().lower()
    objective = campaign.objective.strip().lower()

    return CreativeSet(
        headlines=[
            f"{product} for {audience}",
            f"Bring {product} to the next campaign",
            f"{product}, tuned for a {tone} message",
        ],
        descriptions=[
            f"Shape a {tone} campaign around {product} for {audience}.",
            f"Keep the brief grounded in the product detail: {campaign.product_description.strip()}",
            f"Connect {product} to the campaign objective: {campaign.objective.strip()}.",
        ],
        calls_to_action=[
            f"Explore {product}",
            "See the campaign fit",
            "Start the brief",
        ],
        campaign_concepts=[
            f"Problem to proof: lead with the blockers {audience} face, then show where {product} changes the outcome.",
            f"Objective-led: use {objective} as the campaign spine and keep each idea tied to a next step.",
            f"Tone match: keep the message {tone}, useful, and tied to the product detail that earns attention.",
        ],
    )
