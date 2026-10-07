import json
from dataclasses import replace

import httpx
import pytest
from app.main import create_app
from app.schemas import GeneratedCreativeSet
from app.services.generation import (
    CopyGenerator,
    GenerationConfigurationError,
    GenerationProviderError,
)
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def no_retry_delay(monkeypatch):
    monkeypatch.setattr("app.services.generation.time.sleep", lambda seconds: None)


def creative():
    return {
        "headlines": ["Review support trends"],
        "descriptions": ["Plan your next support review."],
        "calls_to_action": ["Learn more"],
        "campaign_concepts": ["A weekly review workflow."],
    }


def envelope(value=None):
    return {
        "status": "completed",
        "output": [
            {"type": "reasoning"},
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(creative() if value is None else value),
                    }
                ],
            },
        ],
        "usage": {"input_tokens": 70, "output_tokens": 40},
    }


def adapter(settings, handler):
    return CopyGenerator(settings, transport=httpx.MockTransport(handler))


def test_http_contract(settings, campaign):
    def handler(request):
        assert request.method == "POST"
        assert str(request.url) == "https://api.openai.com/v1/responses"
        assert request.headers["Authorization"] == "Bearer test-only-key"
        assert request.headers["X-Client-Request-Id"] == "local-request"
        payload = json.loads(request.content)
        assert payload["tools"] == [] and payload["store"] is False
        assert payload["max_output_tokens"] == 2000
        assert "creative_versions" not in json.loads(payload["input"])
        assert "test-only-key" not in payload["input"]
        schema = payload["text"]["format"]["schema"]
        assert set(schema["required"]) == set(schema["properties"])
        assert schema["additionalProperties"] is False
        return httpx.Response(
            200, json=envelope(), headers={"x-request-id": "req_test"}
        )

    result = adapter(settings, handler).generate(campaign, "local-request")
    assert result.creative_set.headlines == creative()["headlines"]
    assert result.metadata.input_tokens == 70 and result.metadata.output_tokens == 40
    assert result.metadata.provider_request_id == "req_test"
    assert result.metadata.attempts == 1 and result.metadata.latency_ms >= 0
    assert "test-only-key" not in result.model_dump_json()
    assert "test-only-key" not in repr(settings)


@pytest.mark.parametrize(
    "field,value",
    [
        ("headlines", []),
        ("headlines", ["x"] * 6),
        ("headlines", ["x" * 121]),
        ("descriptions", ["x" * 301]),
        ("calls_to_action", ["x" * 81]),
        ("campaign_concepts", ["x" * 501]),
        ("headlines", ["   "]),
        ("headlines", [123]),
        ("unexpected", "x"),
    ],
)
def test_field_limits(settings, campaign, field, value):
    data = creative()
    data[field] = value
    with pytest.raises(GenerationProviderError) as caught:
        adapter(settings, lambda r: httpx.Response(200, json=envelope(data))).generate(
            campaign
        )
    assert caught.value.code == "malformed_output"
    assert caught.value.metadata.attempts == 1


@pytest.mark.parametrize(
    "body,code",
    [
        ([], "malformed_output"),
        ({"status": "incomplete"}, "incomplete_output"),
        ({"status": "completed", "output": []}, "malformed_output"),
        (
            {
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "refusal", "refusal": "sensitive text"}],
                    }
                ],
            },
            "refusal",
        ),
        (
            {
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "not JSON"}],
                    }
                ],
            },
            "malformed_output",
        ),
    ],
)
def test_bad_envelopes(settings, campaign, body, code):
    with pytest.raises(GenerationProviderError) as caught:
        adapter(settings, lambda r: httpx.Response(200, json=body)).generate(campaign)
    assert caught.value.code == code and caught.value.metadata.attempts == 1
    assert "sensitive" not in str(caught.value)


@pytest.mark.parametrize("status", [408, 409, 429, 500, 503])
def test_retry_then_success(settings, campaign, status):
    calls = []

    def handler(request):
        calls.append(request)
        return (
            httpx.Response(status)
            if len(calls) == 1
            else httpx.Response(200, json=envelope())
        )

    result = adapter(settings, handler).generate(campaign)
    assert len(calls) == result.metadata.attempts == 2
    assert (
        calls[0].headers["X-Client-Request-Id"]
        == calls[1].headers["X-Client-Request-Id"]
    )


@pytest.mark.parametrize("kind", ["timeout", "network", "rate_limit", "server"])
def test_exhausted_retries(settings, campaign, kind):
    def handler(request):
        if kind == "timeout":
            raise httpx.ReadTimeout("sensitive text", request=request)
        if kind == "network":
            raise httpx.ConnectError("sensitive text", request=request)
        return httpx.Response(
            429 if kind == "rate_limit" else 500, text="sensitive text"
        )

    with pytest.raises(GenerationProviderError) as caught:
        adapter(settings, handler).generate(campaign)
    assert caught.value.metadata.attempts == 3
    assert "sensitive" not in str(caught.value)


@pytest.mark.parametrize("status", [400, 401, 403, 422])
def test_permanent_failures(settings, campaign, status):
    with pytest.raises(GenerationProviderError) as caught:
        adapter(settings, lambda r: httpx.Response(status)).generate(campaign)
    assert caught.value.metadata.attempts == 1


def test_quota_and_retry_after_budget(settings, campaign):
    for response in [
        httpx.Response(429, json={"error": {"code": "insufficient_quota"}}),
        httpx.Response(429, headers={"retry-after": "60"}),
    ]:
        with pytest.raises(GenerationProviderError) as caught:
            adapter(settings, lambda r: response).generate(campaign)
        assert caught.value.metadata.attempts == 1


def test_retry_after_honored_within_budget(settings, campaign, monkeypatch):
    sleeps = []
    monkeypatch.setattr("app.services.generation.time.sleep", sleeps.append)
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return (
            httpx.Response(429, headers={"retry-after": "1"})
            if calls == 1
            else httpx.Response(200, json=envelope())
        )

    adapter(settings, handler).generate(campaign)
    assert sleeps == [1]


def test_settings_reject_unbounded_limits(settings):
    for field, value in [
        ("max_retries", 50),
        ("request_timeout_seconds", 0),
        ("max_output_tokens", 999999),
    ]:
        with pytest.raises(ValueError):
            replace(settings, **{field: value})


def test_no_key_to_arbitrary_endpoint(settings, campaign):
    with pytest.raises(GenerationConfigurationError):
        CopyGenerator(
            replace(settings, provider_base_url="http://elsewhere.invalid")
        ).generate(campaign)


def test_mock_at_maximum_brief_lengths(settings, campaign):
    campaign.product_name = "x" * 120
    campaign.product_description = "d" * 1200
    campaign.target_audience = "a" * 240
    campaign.objective = "o" * 240
    result = CopyGenerator(replace(settings, generation_mode="mock")).generate(campaign)
    GeneratedCreativeSet.model_validate(result.creative_set.model_dump())
    assert result.metadata.attempts == 0 and result.metadata.input_tokens is None


def test_api_failure_has_request_id_and_keeps_versions(settings, campaign, monkeypatch):
    app = create_app(replace(settings, generation_mode="mock"))
    client = TestClient(app)
    brief = campaign.model_dump(
        include={
            "product_name",
            "product_description",
            "target_audience",
            "tone",
            "objective",
        }
    )
    saved = client.post("/api/campaigns", json=brief).json()
    path = f"/api/campaigns/{saved['id']}"
    first = client.post(path + "/generate").json()
    original = CopyGenerator.generate

    def fail_once(self, campaign, request_id=None):
        generator = adapter(
            settings, lambda r: httpx.Response(429, text="test-only-key")
        )
        return original(generator, campaign, request_id)

    monkeypatch.setattr(CopyGenerator, "generate", fail_once)
    failed = client.post(path + "/generate")
    assert failed.status_code == 502
    assert failed.json()["detail"]["metadata"]["attempts"] == 3
    assert failed.headers["X-Request-ID"] == failed.json()["detail"]["request_id"]
    assert "test-only-key" not in failed.text
    assert client.get(path).json()["creative_versions"] == first["creative_versions"]


def test_non_json_response_and_oversized_body(settings, campaign):
    for body in ["not JSON", "x" * 256001]:
        with pytest.raises(GenerationProviderError) as caught:
            adapter(settings, lambda r: httpx.Response(200, text=body)).generate(
                campaign
            )
        assert caught.value.code == "malformed_output"
        assert caught.value.metadata.attempts == 1
