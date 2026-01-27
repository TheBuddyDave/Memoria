"""
Docstring for src.tests.pg_connection_test

Checks the database connection of running PostgreSQL instance in docker.
Run: python -m src.tests.pg_connection_test
"""

import asyncio
from src.database.agent_state.engine import engine 

async def test_connection():
    # Debug: Print the connection string URL (safely)
    url = engine.url
    print(f"Attempting to connect to: {url.drivername}://{url.username}:{url.password}@{url.host}:{url.port}/{url.database}")
    
    try:
        async with engine.connect() as conn:
            print("✓ PostgreSQL Database connection successful.")
    except Exception as e:
        print(f"✗ PostgreSQL Database connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())