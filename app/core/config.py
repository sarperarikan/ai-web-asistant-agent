from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    gemini_api_key  : str
    jwt_secret_key  : str
    jwt_algorithm   : str = "HS256"
    agent_retries: int = 3
    agent_retry_delay: float = 2.0
    agent_max_steps: int = 25
    agent_max_actions: int = 4
    gemini_model: str = "gemini-2.0-flash-exp"
    gemini_temperature: float = 0.9
    gemini_max_tokens: int = 512
    gemini_top_p: float = 0.9
    database_url    : str = "sqlite:///./db.sqlite3"
    keep_browser_open: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
