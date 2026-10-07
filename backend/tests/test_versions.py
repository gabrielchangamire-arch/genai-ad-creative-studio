import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from app.main import create_app
from app.schemas import CampaignCreate, CreativeSet
from app.store import CampaignStore
from fastapi.testclient import TestClient
from test_provider import creative


def test_versions_survive_restart_and_preserve_old_values(settings, campaign):
    config = replace(settings, generation_mode="mock")
    client = TestClient(create_app(config))
    brief = CampaignCreate.model_validate(
        campaign.model_dump(include=set(CampaignCreate.model_fields))
    )
    saved = client.post("/api/campaigns", json=brief.model_dump()).json()
    path = f"/api/campaigns/{saved['id']}"
    one = client.post(path + "/generate").json()
    two = client.post(path + "/generate").json()
    assert [v["version"] for v in two["creative_versions"]] == [2, 1]
    assert two["creative_versions"][1] == one["creative_versions"][0]
    restarted = TestClient(create_app(config)).get(path).json()
    assert restarted == two
    assert restarted["creative_set"] == two["creative_versions"][0]["creative_set"]


def test_migration_preserves_legacy_output_and_is_idempotent(settings, campaign):
    store = CampaignStore(settings.database_url)
    store.initialize()
    saved = store.create_campaign(
        CampaignCreate.model_validate(
            campaign.model_dump(include=set(CampaignCreate.model_fields))
        )
    )
    legacy = creative()
    legacy["headlines"] = ["x" * 1000]  # Old output was unbounded; don't lose it.
    with store._connect() as db:
        db.execute(
            "UPDATE campaigns SET creative_set = ? WHERE id = ?",
            (json.dumps(legacy), saved["id"]),
        )
    store.initialize()
    store.initialize()
    result = store.get_campaign(saved["id"])
    assert len(result["creative_versions"]) == 1
    assert result["creative_versions"][0]["creative_set"] == legacy
    assert result["creative_versions"][0]["metadata"]["mode"] == "legacy"


def test_concurrent_saves_get_unique_monotonic_versions(settings, campaign):
    store = CampaignStore(settings.database_url)
    store.initialize()
    saved = store.create_campaign(
        CampaignCreate.model_validate(
            campaign.model_dump(include=set(CampaignCreate.model_fields))
        )
    )
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(
            pool.map(
                lambda i: store.save_creative_set(
                    saved["id"], CreativeSet.model_validate(creative())
                ),
                range(8),
            )
        )
    assert [
        v["version"] for v in store.get_campaign(saved["id"])["creative_versions"]
    ] == list(range(8, 0, -1))
    assert (
        store.save_creative_set("missing", CreativeSet.model_validate(creative()))
        is None
    )


def test_transaction_rolls_back_version_if_latest_update_fails(settings, campaign):
    store = CampaignStore(settings.database_url)
    store.initialize()
    saved = store.create_campaign(
        CampaignCreate.model_validate(
            campaign.model_dump(include=set(CampaignCreate.model_fields))
        )
    )
    with store._connect() as db:
        db.execute(
            "CREATE TRIGGER fail_update BEFORE UPDATE ON campaigns BEGIN SELECT RAISE(ABORT, 'test failure'); END"
        )
    import sqlite3

    import pytest

    with pytest.raises(sqlite3.IntegrityError):
        store.save_creative_set(saved["id"], CreativeSet.model_validate(creative()))
    assert store.get_campaign(saved["id"])["creative_versions"] == []
