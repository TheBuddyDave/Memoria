from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from functools import lru_cache

# This will help us locate .env file automatically. 
# WARNING ⚠️: If you change the relative path of .env file, update this accordingly.
# .parent → config
# .parent.parent → src
# .parent.parent.parent → backend (where .env is)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    """
    Settings class to manage application configuration.

    Example usage:

    1. Accessing settings directly:
        settings = Settings()
        print(settings.DEBUG)
        print(settings.OPENAI_API_KEY)

    2. Using as a dependency in FastAPI:
        from fastapi import FastAPI, Depends
        from config import get_settings

        app = FastAPI()

        @router.get("/status")
        async def check_status(settings = Depends(get_settings)):
            return {"is_debug": settings.DEBUG}
    """
    
    # variables from .env file with type hints
    DEBUG: bool = True
    OPENAI_API_KEY: str = ""
    MILVUS_ENDPOINT: str = ""
    MILVUS_TOKEN: str = ""
    NEO4J_URI: str = "neo4j://127.0.0.1:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "memoria1"
    
    # database url should change if we switch environments. I.e. if backend runs in docker container, replace localhost with db (service name)
    DATABASE_URL: str = "postgresql+asyncpg://memoriateam:longterm@localhost:5433/agent_state_db"
    
    # Configuration for loading environment variables
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",  # path to .env file
        env_file_encoding="utf-8",
        env_ignore_empty=True, # ignore empty variables in .env
        extra="allow", # allow extra env variables not defined here
    )

@lru_cache
def get_settings() -> Settings:
    """
    Using lru_cache ensures the settings are only read once. 
    Subsequent calls will return the same object.
    """
    return Settings()
