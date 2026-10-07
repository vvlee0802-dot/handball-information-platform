import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_configuration_rejects_insecure_defaults() -> None:
    with pytest.raises(ValidationError, match="POSTGRES_PASSWORD"):
        Settings(
            app_env="production",
            postgres_password="handball_dev_password",
            session_cookie_secure=False,
            force_https=False,
            allowed_hosts="localhost",
            allowed_origins="http://localhost:5173",
            _env_file=None,
        )


def test_production_configuration_accepts_explicit_https_settings() -> None:
    settings = Settings(
        app_env="production",
        postgres_password="a-long-production-only-secret",
        session_cookie_secure=True,
        force_https=True,
        allowed_hosts="handball.example.com",
        allowed_origins="https://handball.example.com",
        _env_file=None,
    )

    assert settings.cors_origins == ["https://handball.example.com"]
    assert settings.trusted_hosts == ["handball.example.com"]
