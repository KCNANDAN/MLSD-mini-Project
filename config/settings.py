
from functools import lru_cache
from typing import Literal
from pydantic import Field, SecretStr, model_validator
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application configuration.

    Values are loaded from environment variables or .env.
    Environment variables take precedence over .env values.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --------------------------------------------------
    # Application
    # --------------------------------------------------

    app_name: str = "Academic Petition Triage Service"
    app_env: Literal["development", "testing", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"

    api_v1_prefix: str = "/api/v1"

    # --------------------------------------------------
    # Database
    # --------------------------------------------------

    database_url: str = "sqlite:///./storage/petitions.db"

    # --------------------------------------------------
    # Redis
    # --------------------------------------------------

    redis_url: str = "redis://localhost:6379/0"
    redis_queue_name: str = "petition-processing"

    # --------------------------------------------------
    # Vector database
    # --------------------------------------------------

    chroma_host: str = "localhost"
    chroma_port: int = Field(default=8000, gt=0, le=65535)

    chroma_collection_name: str = "academic_regulations"

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # --------------------------------------------------
    # LLM provider
    # --------------------------------------------------

    llm_provider: str = "groq"

    llm_model: str = "openai/gpt-oss-120b"

    llm_api_key: SecretStr | None = None

    llm_base_url: str | None = None

    llm_temperature: float = Field(default=0.0, ge=0.0, le=2.0)

    llm_timeout_seconds: float = Field(default=30.0, gt=0)

    # Load testing
    use_stub_llm: bool = False

    stub_llm_latency_ms: int = Field(
        default=100,
        ge=0,
    )
    # --------------------------------------------------
    # Agent execution limits
    # --------------------------------------------------

    max_agent_steps: int = Field(default=8, ge=1, le=20)

    max_tool_calls: int = Field(default=12, ge=1, le=30)

    max_agent_retries: int = Field(default=2, ge=0, le=5)

    max_run_duration_seconds: int = Field(default=120, gt=0)

    # --------------------------------------------------
    # Reliability
    # --------------------------------------------------

    tool_timeout_seconds: float = Field(default=30.0, gt=0)

    retry_backoff_seconds: float = Field(default=0.5, gt=0)

    circuit_breaker_failure_threshold: int = Field(
        default=5,
        ge=1,
    )

    circuit_breaker_recovery_seconds: int = Field(
        default=30,
        gt=0,
    )

    # --------------------------------------------------
    # Retrieval
    # --------------------------------------------------

    retrieval_top_k: int = Field(default=5, ge=1, le=20)

    retrieval_score_threshold: float = Field(
        default=0.0,
        ge=0.0,
    )

    chunk_size: int = Field(default=1000, ge=100)

    chunk_overlap: int = Field(default=150, ge=0)

    # --------------------------------------------------
    # Prompt management
    # --------------------------------------------------

    prompt_version: str = "v1"

    # --------------------------------------------------
    # Observability
    # --------------------------------------------------

    otel_service_name: str = "academic-petition-triage"

    otel_exporter_otlp_endpoint: str = "http://localhost:4317"

    metrics_enabled: bool = True

    # --------------------------------------------------
    # API protection
    # --------------------------------------------------

    rate_limit_per_minute: int = Field(default=30, gt=0)

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    @model_validator(mode="after")
    def validate_chunking(self):
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                "CHUNK_OVERLAP must be smaller than CHUNK_SIZE"
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached application settings instance.
    """
    settings = Settings()

    if settings.chunk_overlap >= settings.chunk_size:
        raise ValueError(
            "CHUNK_OVERLAP must be smaller than CHUNK_SIZE"
        )

    return settings
