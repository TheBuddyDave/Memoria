import asyncio
import sys

import pytest
import pytest_asyncio
from neo4j import AsyncGraphDatabase

from src.config.settings import get_settings


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for Windows compatibility."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest_asyncio.fixture(scope="function")
async def neo4j_driver():
    """Provide an async Neo4j driver for each test function."""
    settings = get_settings()
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )
    yield driver
    try:
        await driver.close()
    except Exception:
        # Suppress cleanup errors on Windows + Python 3.13
        pass
