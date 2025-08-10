"""Configuration management for DevSync AI."""

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application settings
    app_name: str = "DevSync AI"
    app_version: str = "0.1.0"
    debug: bool = False

    # API settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"

    # Database settings
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_key: str = Field(..., env="SUPABASE_KEY")

    # Redis settings
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")

    # GitHub settings
    github_token: Optional[str] = Field(default=None, env="GITHUB_TOKEN")
    github_webhook_secret: Optional[str] = Field(default=None, env="GITHUB_WEBHOOK_SECRET")
    github_repository: str = Field(default="asakohayase/kiro-devsync-ai", env="GITHUB_REPOSITORY")

    # JIRA settings
    jira_url: Optional[str] = Field(default=None, env="JIRA_URL")
    jira_username: Optional[str] = Field(default=None, env="JIRA_USERNAME")
    jira_token: Optional[str] = Field(default=None, env="JIRA_TOKEN")

    # Slack settings
    slack_bot_token: Optional[str] = Field(default=None, env="SLACK_BOT_TOKEN")
    slack_signing_secret: Optional[str] = Field(default=None, env="SLACK_SIGNING_SECRET")
    slack_default_channel: str = Field(default="#general", env="SLACK_DEFAULT_CHANNEL")

    # Scheduler settings
    standup_time: str = Field(default="09:00", env="STANDUP_TIME")
    changelog_day: str = Field(default="friday", env="CHANGELOG_DAY")

    # Security settings
    secret_key: Optional[str] = Field(default=None, env="SECRET_KEY")
    api_key: Optional[str] = Field(default=None, env="API_KEY")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
