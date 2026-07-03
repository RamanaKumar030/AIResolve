from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "AIResolve"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "production"

    supabase_url: str
    supabase_key: str
    supabase_jwt_secret: str

    database_url: str

    openai_api_key: str
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"

    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60

    cors_origins: str = "http://localhost:5173,https://airesolve.onrender.com,https://ai-resolve-shy8.vercel.app"
    cors_allow_credentials: bool = True
    cors_allow_methods: str = "*"
    cors_allow_headers: str = "*"

    log_level: str = "INFO"
    log_format: str = "json"

    max_message_length: int = 10000
    max_history_messages: int = 50
    stream_chunk_size: int = 50

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
