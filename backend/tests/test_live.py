"""Opt-in, one-case live smoke. Normal CI never needs credentials or network."""

import os
from dataclasses import replace

import pytest
from app.config import get_settings
from app.schemas import GeneratedCreativeSet
from app.services.generation import CopyGenerator


@pytest.mark.live
@pytest.mark.skipif(
    os.getenv("STUDIO_RUN_LIVE") != "1", reason="Live provider smoke is opt-in"
)
def test_live_smoke(campaign):
    settings = replace(get_settings(), generation_mode="provider", max_retries=0)
    if not settings.provider_api_key:
        pytest.fail(
            "Set GENAI_PROVIDER_API_KEY on the backend before opting into the live smoke"
        )
    result = CopyGenerator(settings).generate(campaign)
    GeneratedCreativeSet.model_validate(result.creative_set.model_dump())
    assert result.metadata.attempts == 1
    assert result.metadata.latency_ms > 0
    # Only safe metadata is printed, never credentials, prompts, or provider bodies.
    print(result.metadata.model_dump_json())
