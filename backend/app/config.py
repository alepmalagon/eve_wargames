"""
Configuration settings for the EVE Wargames application.

Uses Pydantic Settings for environment variable management.
"""

from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application settings
    APP_NAME: str = "EVE Wargames"
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    HOST: str = Field(default="0.0.0.0", description="Host to bind the server")
    PORT: int = Field(default=8000, description="Port to bind the server")
    
    # Security settings
    SECRET_KEY: str = Field(..., description="Secret key for JWT tokens")
    ALLOWED_HOSTS: List[str] = Field(default=["*"], description="Allowed hosts for the application")
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins"
    )
    
    # Database settings
    DATABASE_URL: str = Field(
        default="postgresql://eve_user:eve_password@localhost:5432/eve_wargames",
        description="Database connection URL"
    )
    
    # Redis settings
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching"
    )
    
    # ESI API settings
    ESI_BASE_URL: str = Field(
        default="https://esi.evetech.net/latest",
        description="EVE Online ESI API base URL"
    )
    ESI_CLIENT_ID: Optional[str] = Field(
        default=None,
        description="ESI application client ID"
    )
    ESI_CLIENT_SECRET: Optional[str] = Field(
        default=None,
        description="ESI application client secret"
    )
    ESI_CALLBACK_URL: Optional[str] = Field(
        default=None,
        description="ESI OAuth callback URL"
    )
    ESI_USER_AGENT: str = Field(
        default="EVE Wargames/1.0.0 (https://github.com/alepmalagon/eve_wargames)",
        description="User agent for ESI API requests"
    )
    
    # Data collection settings
    DATA_COLLECTION_INTERVAL: int = Field(
        default=300,  # 5 minutes
        description="Interval in seconds for data collection from ESI"
    )
    KILL_DATA_RETENTION_DAYS: int = Field(
        default=90,
        description="Number of days to retain kill data"
    )
    SYSTEM_DATA_RETENTION_DAYS: int = Field(
        default=365,
        description="Number of days to retain system control data"
    )
    
    # Celery settings
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1",
        description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/1",
        description="Celery result backend URL"
    )
    
    # Logging settings
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    # Faction Warfare specific settings
    MINMATAR_FACTION_ID: int = Field(
        default=500002,
        description="Minmatar Republic faction ID"
    )
    AMARR_FACTION_ID: int = Field(
        default=500003,
        description="Amarr Empire faction ID"
    )
    
    # Cache settings
    CACHE_TTL_SECONDS: int = Field(
        default=300,  # 5 minutes
        description="Default cache TTL in seconds"
    )
    SYSTEM_CACHE_TTL_SECONDS: int = Field(
        default=60,  # 1 minute
        description="System data cache TTL in seconds"
    )
    KILL_CACHE_TTL_SECONDS: int = Field(
        default=180,  # 3 minutes
        description="Kill data cache TTL in seconds"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()
