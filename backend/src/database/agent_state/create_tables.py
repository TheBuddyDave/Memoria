"""
Docstring for src.database.agent_state.create_tables

This script creates all tables defined in the ORM models for the agent_state database.
"""
import asyncio
from src.database.agent_state.engine import engine
from src.database.agent_state.base import Base
from src.database.agent_state import models  # noqa: F401  (ensures models are registered)

async def create_all() -> None:
    # NOTE: we use engine.begin() not sessionmaker here because these are DDL operations not DML
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def drop_and_create_all() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    # NOTE: this will drop existing tables! If no tables exist, it will just create them.
    asyncio.run(drop_and_create_all())
    print("Dropped + created all tables.")
