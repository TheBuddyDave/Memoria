"""
Docstring for src.config.llm_clients.openai_client
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from src.config.settings import get_settings
from openai import AsyncOpenAI, DefaultAioHttpClient

@asynccontextmanager
async def get_openai_client() -> AsyncGenerator[AsyncOpenAI, None]:
    """
    Returns an async OpenAI client managed by an async context manager.
    Automatically closes the client and its shared connection pool when the context is exited.
    Configured with the API key from settings and uses aiohttp for better concurrency.

    Usage:
        from src.config.llm_clients.openai_client import get_openai_client

        async with get_openai_client() as client:
            response = await client.chat.completions.create(...)
    """
    settings = get_settings()
    client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        http_client=DefaultAioHttpClient(),
    )
    try:
        yield client
    finally:
        await client.close()


