"""
src.config.milvus_client
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from src.config.settings import get_settings, Settings
from pymilvus import AsyncMilvusClient

settings: Settings = get_settings()

@asynccontextmanager
async def get_milvus_client() -> AsyncGenerator[AsyncMilvusClient, None]:
    uri = settings.MILVUS_ENDPOINT
    token = settings.MILVUS_TOKEN

    assert uri is not None, "MILVUS_ENDPOINT environment variable not set"
    assert token is not None, "MILVUS_TOKEN environment variable not set"
    
    client = AsyncMilvusClient(
        uri=str(uri), token=str(token)
    )
    try:
        yield client
    finally:
        await client.close()

