from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()
BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_URL = f"sqlite:///{BACKEND_ROOT / 'data' / 'studio.db'}"


@dataclass(frozen=True)
class Settings:
    database_url: str
    generation_mode: str
    provider_api_key: str | None
    provider_base_url: str | None
    provider_model: str | None
    frontend_origins: tuple[str, ...]


def _read_origins(value: str | None) -> tuple[str, ...]:
    if not value:
        return ("http://localhost:5173",)

    return tuple(origin.strip() for origin in value.split(",") if origin.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        generation_mode=os.getenv("GENERATION_MODE", "mock").strip().lower(),
        provider_api_key=os.getenv("GENAI_PROVIDER_API_KEY"),
        provider_base_url=os.getenv("GENAI_PROVIDER_BASE_URL"),
        provider_model=os.getenv("GENAI_PROVIDER_MODEL"),
        frontend_origins=_read_origins(os.getenv("FRONTEND_ORIGINS")),
    )
