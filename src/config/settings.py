from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    """
    Comprehensive application configuration management
    Handles environment-specific settings with validation
    """
    
    # Application configuration
    app_name: str = "AI Email Assistant"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Database configuration
    database_url: str = "postgresql+asyncpg://user:password@localhost/ai_email_db"
    database_pool_size: int = 20
    database_max_overflow: int = 30
    
    # Redis configuration
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 0
    
    # Google API configuration
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/callback"
    google_scopes: List[str] = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/userinfo.email"
    ]
    
    # OpenAI configuration
    openai_api_key: str = ""
    openai_model: str = "gpt-4"
    
    # Vector database configuration
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    weaviate_url: str = "http://localhost:8080"
    
    # Celery configuration
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    
    # Security configuration
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()