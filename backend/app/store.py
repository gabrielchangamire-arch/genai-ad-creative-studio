import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .schemas import CampaignCreate, CreativeSet, GenerationMetadata


class CampaignStore:
    def __init__(self, database_url: str) -> None:
        self.database_path = _sqlite_path(database_url)

    def initialize(self) -> None:
        if self.database_path != Path(":memory:"):
            self.database_path.parent.mkdir(parents=True, exist_ok=True)

        with closing(self._connect()) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS campaigns (
                    id TEXT PRIMARY KEY,
                    product_name TEXT NOT NULL,
                    product_description TEXT NOT NULL,
                    target_audience TEXT NOT NULL,
                    tone TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    creative_set TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute("""
                CREATE TABLE IF NOT EXISTS creative_versions (
                    campaign_id TEXT NOT NULL REFERENCES campaigns(id),
                    version INTEGER NOT NULL,
                    creative_set TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (campaign_id, version)
                )
            """)
            # Preserve existing sets exactly once. New validation rules never rewrite legacy data.
            connection.execute(
                """
                INSERT INTO creative_versions (campaign_id, version, creative_set, metadata, created_at)
                SELECT id, 1, creative_set, ?, updated_at FROM campaigns
                WHERE creative_set IS NOT NULL AND NOT EXISTS (
                    SELECT 1 FROM creative_versions WHERE campaign_id = campaigns.id)
            """,
                (
                    GenerationMetadata(
                        mode="legacy", request_id="legacy-import"
                    ).model_dump_json(),
                ),
            )
            connection.commit()

    def create_campaign(self, payload: CampaignCreate) -> dict:
        campaign_id = str(uuid4())
        timestamp = _timestamp()

        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO campaigns (
                    id,
                    product_name,
                    product_description,
                    target_audience,
                    tone,
                    objective,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    campaign_id,
                    payload.product_name,
                    payload.product_description,
                    payload.target_audience,
                    payload.tone,
                    payload.objective,
                    timestamp,
                    timestamp,
                ),
            )
            connection.commit()

        return self.get_campaign(campaign_id)

    def list_campaigns(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM campaigns ORDER BY updated_at DESC"
            ).fetchall()

            return [self._with_versions(connection, row) for row in rows]

    def get_campaign(self, campaign_id: str) -> dict | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM campaigns WHERE id = ?",
                (campaign_id,),
            ).fetchone()

            return self._with_versions(connection, row) if row else None

    def save_creative_set(
        self,
        campaign_id: str,
        creative_set: CreativeSet,
        metadata: GenerationMetadata | None = None,
    ) -> dict | None:
        timestamp = _timestamp()
        metadata = metadata or GenerationMetadata(
            mode="legacy", request_id=str(uuid4())
        )
        with closing(self._connect()) as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT id FROM campaigns WHERE id = ?", (campaign_id,)
                ).fetchone()
                if row is None:
                    connection.rollback()
                    return None
                version = connection.execute(
                    "SELECT COALESCE(MAX(version), 0) + 1 FROM creative_versions WHERE campaign_id = ?",
                    (campaign_id,),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO creative_versions
                    (campaign_id, version, creative_set, metadata, created_at) VALUES (?, ?, ?, ?, ?)""",
                    (
                        campaign_id,
                        version,
                        creative_set.model_dump_json(),
                        metadata.model_dump_json(),
                        timestamp,
                    ),
                )
                connection.execute(
                    "UPDATE campaigns SET creative_set = ?, updated_at = ? WHERE id = ?",
                    (creative_set.model_dump_json(), timestamp, campaign_id),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            row = connection.execute(
                "SELECT * FROM campaigns WHERE id = ?", (campaign_id,)
            ).fetchone()
            return self._with_versions(connection, row)

    @staticmethod
    def _with_versions(connection: sqlite3.Connection, row: sqlite3.Row) -> dict:
        result = _campaign_from_row(row)
        versions = connection.execute(
            "SELECT * FROM creative_versions WHERE campaign_id = ? ORDER BY version DESC",
            (row["id"],),
        ).fetchall()
        result["creative_versions"] = [
            {
                "version": v["version"],
                "created_at": v["created_at"],
                "creative_set": json.loads(v["creative_set"]),
                "metadata": json.loads(v["metadata"]),
            }
            for v in versions
        ]
        return result

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def _sqlite_path(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError("Only sqlite database URLs are supported locally.")

    raw_path = database_url.removeprefix(prefix)
    return Path(raw_path)


def _campaign_from_row(row: sqlite3.Row) -> dict:
    creative_set = json.loads(row["creative_set"]) if row["creative_set"] else None
    return {
        "id": row["id"],
        "product_name": row["product_name"],
        "product_description": row["product_description"],
        "target_audience": row["target_audience"],
        "tone": row["tone"],
        "objective": row["objective"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "creative_set": creative_set,
    }


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
