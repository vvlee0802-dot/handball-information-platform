from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_env: Literal["development", "test", "production"] = "development"
    app_version: str = "1.0.0"
    log_level: str = "INFO"
    postgres_db: str = "handball"
    postgres_user: str = "handball"
    postgres_password: str = "handball_dev_password"
    postgres_host: str = "localhost"
    postgres_port: int = 5433
    redis_url: str = "redis://localhost:6379/0"
    task_queue_mode: Literal["background", "rq"] = "background"
    task_queue_name: str = "handball"
    session_cookie_name: str = "handball_session"
    session_max_age_seconds: int = 60 * 60 * 24 * 7
    session_cookie_secure: bool = False
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    allowed_hosts: str = "localhost,127.0.0.1,testserver"
    force_https: bool = False
    video_upload_max_bytes: int = 10 * 1024**3
    video_upload_chunk_bytes: int = 8 * 1024**2
    video_upload_dir: Path = PROJECT_ROOT / "backend" / "uploads"
    match_report_max_bytes: int = 10 * 1024**2
    match_report_dir: Path = PROJECT_ROOT / "backend" / "uploads" / "match_reports"
    goal_model_dir: Path = PROJECT_ROOT / "backend" / "model_artifacts" / "goal_detector" / "v2"
    match_report_llm_base_url: str = ""
    match_report_llm_api_key: str = ""
    match_report_llm_model: str = ""
    match_report_prompt_version: str = "match-report-v1"
    match_report_llm_timeout_seconds: float = 180.0
    match_report_llm_enable_thinking: bool = False
    match_report_llm_max_tokens: int = 3000
    knowledge_document_max_bytes: int = 20 * 1024**2
    knowledge_document_dir: Path = PROJECT_ROOT / "backend" / "uploads" / "knowledge"
    knowledge_embedding_model: str = "text-embedding-v4"
    knowledge_rag_prompt_version: str = "knowledge-rag-v1"
    knowledge_retrieval_top_k: int = 5
    knowledge_relevance_threshold: float = 0.3
    match_agent_prompt_version: str = "match-agent-v1"
    match_agent_max_tool_steps: int = 5
    match_agent_history_messages: int = 16

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        return (
            "postgresql+psycopg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origins(self) -> list[str]:
        return [value.strip() for value in self.allowed_origins.split(",") if value.strip()]

    @property
    def trusted_hosts(self) -> list[str]:
        return [value.strip() for value in self.allowed_hosts.split(",") if value.strip()]

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.app_env != "production":
            return self
        errors: list[str] = []
        if self.postgres_password in {"", "handball_dev_password"}:
            errors.append("POSTGRES_PASSWORD must be set to a non-default secret")
        if not self.session_cookie_secure:
            errors.append("SESSION_COOKIE_SECURE must be true")
        if not self.force_https:
            errors.append("FORCE_HTTPS must be true")
        if not self.trusted_hosts or "*" in self.trusted_hosts:
            errors.append("ALLOWED_HOSTS must contain explicit host names")
        if not self.cors_origins or "*" in self.cors_origins:
            errors.append("ALLOWED_ORIGINS must contain explicit HTTPS origins")
        if any(not origin.startswith("https://") for origin in self.cors_origins):
            errors.append("ALLOWED_ORIGINS must use HTTPS in production")
        if errors:
            raise ValueError("Invalid production configuration: " + "; ".join(errors))
        return self

    @property
    def video_storage_path(self) -> Path:
        if self.video_upload_dir.is_absolute():
            return self.video_upload_dir
        return PROJECT_ROOT / self.video_upload_dir

    @property
    def goal_model_path(self) -> Path:
        if self.goal_model_dir.is_absolute():
            return self.goal_model_dir
        return PROJECT_ROOT / self.goal_model_dir

    @property
    def match_report_storage_path(self) -> Path:
        if self.match_report_dir.is_absolute():
            return self.match_report_dir
        return PROJECT_ROOT / self.match_report_dir

    @property
    def knowledge_document_storage_path(self) -> Path:
        if self.knowledge_document_dir.is_absolute():
            return self.knowledge_document_dir
        return PROJECT_ROOT / self.knowledge_document_dir


settings = Settings()
