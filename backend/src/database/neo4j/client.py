from neo4j.exceptions import DriverError
from neo4j import AsyncGraphDatabase, AsyncDriver
from src.config.settings import Settings

class Neo4jClient:

    def __init__(self):
        """
        Use this client as an async context manager to ensure the driver closes:
        `async with Neo4jClient() as client:`
        """
        settings = Settings()

        self.uri: str = settings.NEO4J_URI
        self.user: str = settings.NEO4J_USER
        self.password: str = settings.NEO4J_PASSWORD

        # define the async driver connection
        self.asyncDriver = AsyncGraphDatabase.driver(
            uri=self.uri, auth=(self.user, self.password)
        )

    async def close(self):
        await self.asyncDriver.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def get_asyncdriver(self) -> AsyncDriver:
        return self.asyncDriver

    async def verify_connection(self) -> bool:
        try:
            await self.asyncDriver.verify_connectivity()
            print("\nNeo4j connection verified successfully!\n")
            return True

        except DriverError as de:
            print(f"Neo4j Driver error seems like it was closed: {de}")
            return False

        except Exception as e:
            print(f"Neo4j connection verification failed: {e}")
            return False

    async def get_async_driver(self):
        return self.asyncDriver