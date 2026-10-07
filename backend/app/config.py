import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_URL = f"sqlite:///{BACKEND_ROOT / 'data' / 'studio.db'}"


@dataclass(frozen=True)
class Settings:
    database_url: str
    generation_mode: str
    provider_api_key: str | None = field(repr=False)
    provider_base_url: str | None
    provider_model: str | None
    frontend_origins: tuple[str, ...]
    request_timeout_seconds: float = 20
    max_retries: int = 2
    max_output_tokens: int = 2000

    def __post_init__(self) -> None:
        if not 0 < self.request_timeout_seconds <= 60:
            raise ValueError("Timeout must be between 0 and 60 seconds")
        if not 0 <= self.max_retries <= 3:
            raise ValueError("Retries must be between 0 and 3")
        if not 128 <= self.max_output_tokens <= 8000:
            raise ValueError("Output token cap must be between 128 and 8000")


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
        provider_base_url=os.getenv(
            "GENAI_PROVIDER_BASE_URL", "https://api.openai.com/v1"
        ),
        provider_model=os.getenv("GENAI_PROVIDER_MODEL", "gpt-5-mini"),
        request_timeout_seconds=float(os.getenv("GENAI_TIMEOUT_SECONDS", "20")),
        max_retries=int(os.getenv("GENAI_MAX_RETRIES", "2")),
        max_output_tokens=int(os.getenv("GENAI_MAX_OUTPUT_TOKENS", "2000")),
        frontend_origins=_read_origins(os.getenv("FRONTEND_ORIGINS")),
    )
