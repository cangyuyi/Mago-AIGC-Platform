"""Application configuration using pydantic-settings."""

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        # Native launches usually run from services/agent, while Compose
        # injects environment variables directly. Support service-local,
        # services-level, and repository-root .env files.
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    # Server
    app_name: str = "mago-agent-service"
    app_version: str = "0.1.0"
    host: str = Field(
        default="0.0.0.0",
        validation_alias=AliasChoices("APP_HOST", "HOST"),
    )
    port: int = Field(
        default=8000,
        validation_alias=AliasChoices("APP_PORT", "PORT"),
    )
    environment: str = "development"
    debug: bool = True
    agent_auth_enabled: bool = False
    jwt_secret: str = ""

    # Database
    database_url: str = "postgresql+psycopg2://mago:mago_secret@localhost:5432/mago?sslmode=disable"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # LangGraph checkpointer. Paused HITL runs are stored here, so production
    # should point this at Postgres/Redis; leave empty to fall back to an
    # in-process MemorySaver (dev/tests only).
    checkpointer_url: str = ""
    agent_checkpoint_path: str = ""

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = Field(
        default="magoadmin",
        validation_alias=AliasChoices("MINIO_ACCESS_KEY", "MINIO_ROOT_USER"),
    )
    minio_secret_key: str = Field(
        default="magoadmin123",
        validation_alias=AliasChoices("MINIO_SECRET_KEY", "MINIO_ROOT_PASSWORD"),
    )
    minio_bucket: str = "mago-agent"
    minio_secure: bool = False

    # Milvus
    milvus_host: str = "localhost"
    milvus_port: int = 19530

    # LLM API Keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    deepseek_api_key: str = ""
    zhipu_api_key: str = ""
    dashscope_api_key: str = ""

    # Default LLM models
    default_model: str = "gpt-4o"
    fast_model: str = "gpt-4o-mini"
    multimodal_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"

    # CORS
    allowed_origins: str = "http://localhost:3000,http://localhost"

    # Agent defaults
    agent_max_iterations: int = 10
    agent_timeout_seconds: int = 300

    # Trend Intelligence
    ffmpeg_path: str = "ffmpeg"
    video_temp_dir: str = "/tmp/mago_videos"
    keyframe_dir: str = "/tmp/mago_keyframes"
    crawl_interval_minutes: int = 30
    crawl_enabled_platforms: str = "douyin,kuaishou,xiaohongshu,bilibili,weibo"
    crawl_use_sample_data: bool = False
    douyin_cookie: str = ""
    crawl_request_delay_min: float = 1.0
    crawl_request_delay_max: float = 3.0
    # Keep synchronous trend insights responsive when an upstream platform is
    # unavailable. Background crawl jobs can still run with the normal crawler
    # timeout; this limit only applies to the dashboard-facing insights API.
    trend_insights_timeout_seconds: float = 15.0
    crawl_proxies: str = ""
    asr_engine: str = "whisper"  # whisper / funasr
    scene_detect_mode: str = "fast"  # fast / accurate
    max_video_analysis_duration: int = 300  # seconds
    viral_analysis_concurrent: int = 2
    # Mago Platform
    mago_api_url: str = "http://localhost:8080"
    mago_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
