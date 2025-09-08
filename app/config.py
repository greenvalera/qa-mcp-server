"""Application configuration."""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    
    # Confluence Configuration
    confluence_base_url: Optional[str] = None
    confluence_auth_token: Optional[str] = None
    confluence_space_key: Optional[str] = None
    confluence_root_pages: Optional[str] = None
    
    # Database Configuration
    mysql_dsn: str = "mysql+pymysql://qa:qa@localhost:3306/qa"
    vectordb_url: str = "http://localhost:6333"
    
    # Application Configuration
    app_port: int = 3000
    max_top_k: int = 50
    
    # Chunking Configuration
    chunk_size: int = 800
    chunk_overlap: int = 200
    
    # Feature Tagging Configuration
    feature_sim_threshold: float = 0.80
    
    # Environment
    environment: str = "development"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() in ("development", "dev")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() in ("production", "prod")


# Global settings instance
settings = Settings()
