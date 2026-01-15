from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    openai_api_key: str = ""
    oura_client_id: str = ""
    oura_client_secret: str = ""
    whoop_client_id: str = ""
    whoop_client_secret: str = ""
    database_url: str = "sqlite:///./health_platform.db"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
