"""
Docstring for src.database.agent_state.session

Provides sessions for interacting with the database. 
> NOTE: must keep sessions short-lived (one request / one operation scope) to avoid long transactions and potential locks. This must be enforced by the caller.
"""
from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from .engine import engine

# Session factory decouples DB config from business logic (Rule #3)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False, # do not expire objects on commit to avoid reloading from DB. May cause stale data within a session if not handled properly.
    autoflush=False,
)

async def get_session() -> AsyncIterator[AsyncSession]:
    """
    FastAPI dependency.
    
    Make sure to use properly closing transactions and sessions.

    short-lived session (one request / one operation scope). 
    """
    async with AsyncSessionLocal() as session:
        yield session
