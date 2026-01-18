"""
Docstring for src.database.agent_state.engine

This same engine instance will be used across the application to interact with the database. It's created once at application startup. 
"""

from src.config.settings import Settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

keys: Settings = Settings()
DATABASE_URL = keys.DATABASE_URL

# Global engine: created once and reused
# Docs: https://docs.sqlalchemy.org/en/20/core/engines.html
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    # pool_size / max_overflow can be tuned later if needed
)
