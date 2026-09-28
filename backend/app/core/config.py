from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    postgres_db: str = "handball"
    postgres_user: str = "handball"
    postgres_password: str = "handball_dev_password"
    postgres_port: int = 5433
    session_cookie_name: str = "handball_session"
    session_max_age_seconds: int = 60 * 60 * 24 * 7
    session_cookie_secure: bool = False
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
            f"@localhost:{self.postgres_port}/{self.postgres_db}"
        )

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
