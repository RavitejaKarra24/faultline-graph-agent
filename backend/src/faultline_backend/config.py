import re

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    falkordb_host: str = "localhost"
    falkordb_port: int = Field(default=6379, ge=1, le=65535)
    falkordb_password: SecretStr | None = None
    graph_prefix: str = "faultline_"
    query_timeout_ms: int = Field(default=3000, ge=100, le=30000)
    openai_api_key: SecretStr | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)

    @field_validator("graph_prefix")
    @classmethod
    def validate_prefix(cls, value: str):
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", value):
            raise ValueError("graph_prefix must be a safe lowercase graph prefix")
        return value


def workspace_slug(value: str):
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?", value):
        raise ValueError("X-Workspace must be a lowercase slug, 1–40 characters")
    return value
