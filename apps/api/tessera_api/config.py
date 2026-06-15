from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://tessera:tessera@localhost:5432/tessera"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "dev-secret-key-change-in-production"

    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""

    anthropic_api_key: str = ""

    ollama_base_url: str = "http://ollama:11434"
    llm_default_model: str = "claude-opus-4-8"
    llm_draft_model: str = "claude-haiku-4-5"
    llm_economy_model: str = "claude-sonnet-4-6"
    embedding_model: str = "nomic-embed-text"
    embedding_dimensions: int = 768

    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    jwt_algorithm: str = "HS256"

    log_level: str = "INFO"
    environment: str = "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
