from pydantic import AnyHttpUrl, PostgresDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings.

    Args:
        BaseSettings: Base settings class
    """

    # Prometheus settings
    ENABLE_METRICS: bool = False

    # Database settings
    DATABASE_URL: PostgresDsn

    # Application settings
    APP_NAME: str = "zODC Backend"
    DEBUG: bool = False

    # API settings
    API_V1_STR: str = "/api/v1"

    # Logging
    LOG_LEVEL: str = "INFO"

    # Port
    PORT: int = 8001

    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None  # Add password if Redis is secured
    REDIS_DB: int = 0  # Default Redis database

    # FastAPI Azure Auth settings
    BACKEND_CORS_ORIGINS: list[str | AnyHttpUrl] = [
        "http://localhost:8001", "http://localhost:4200"]
    OPENAPI_CLIENT_ID: str = ""
    APP_CLIENT_ID: str = ""

    # Client and server settings
    CLIENT_AZURE_CLIENT_ID: str = ""
    CLIENT_AZURE_TENANT_ID: str = ""
    CLIENT_AZURE_REDIRECT_URI: str = ""
    CLIENT_AZURE_CLIENT_SECRET: str = ""

    # Azure Blob Storage settings
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_STORAGE_ACCOUNT: str = ""

    # NATS settings
    NATS_URL: str = "nats://localhost:4222"
    NATS_CLIENT_NAME: str = "auth_service"
    NATS_CLUSTER_ID: str = "test-cluster"
    NATS_USERNAME: str = "myuser"
    NATS_PASSWORD: str = "mypassword"

    # Jira settings
    JIRA_BASE_URL: str = "https://api.atlassian.com/ex/jira/cloud-id"
    AUTH_SERVICE_URL: str = "http://localhost:8081"

    class Config:
        """Configuration settings."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
