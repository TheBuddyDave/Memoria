"""
Run at (after cd to backend): python -m neo4j_db.scripts_with_data.neo4jHelpers

⚠️ Default username: neo4j, password = memoria1 , If you set a different password make sure to update it here.
Also the connection URI should be default but if due to OS it's different, update it in env as well. You can check it in Neo4j desktop -> left tab -> local instances -> on the card for your connected instance it shows "Connection URI"
Default URI = neo4j://127.0.0.1:7687

⚠️ Neo4j Docs say connecting a driver is expensive and should be done once per application and reused. But make sure to close it.
connection docs: https://neo4j.com/docs/python-manual/current/connect/

Here is API reference: https://neo4j.com/docs/api/python-driver/6.0/index.html

# when we run execute_query it returns 3 things:
- list[Record]: https://neo4j.com/docs/api/python-driver/6.0/api.html#neo4j.Record
- ResultSummary: https://neo4j.com/docs/api/python-driver/6.0/api.html#resultsummary
- list of keys (list[str]): name of columns returned
"""
from typing import Any
from milvus.scripts_with_data.helpers import WriteDataOnFile
import os
from src.database.neo4j.client import Neo4jClient

DIRECTORY_PATH = path = os.path.dirname(__file__)

# ################
# Get text for all nodes with their ID and store it in a file
# ################


async def fetch_all_node_texts(path: str, filename: str):
    """
    Fetch text property for all nodes in the Neo4j database along with the id we created (deprecated: we used to use elementId but not anymore).
    Writes the data to a specified file. One json per line.
    
    Args:
        path: absolute path to the folder where the file will be stored. Defaults to the folder of this script.
        filename: name of the file to store the node texts.

    Returns:
        None
    """
    async with Neo4jClient() as neo4jclient:
        if not await neo4jclient.verify_connection():
            print("\nNeo4j connection could not be verified. Ending process\n")
            return

        neo4jAsyncDriver = await neo4jclient.get_async_driver()

        query = """
            MATCH (n)
            WHERE n.text IS NOT NULL
            RETURN n.text AS text, n.id AS elementId
        """
        
        try:
            # note we must provide the database name since we are not using the default 'neo4j' database. Also their docs say always provide it for performance enhancement as their driver doesn't have to resolve the database.
            records, summary, keys = await neo4jAsyncDriver.execute_query(query, database_="memorygraph")
            
            results: list[dict[str, Any]] = [
                # note we are assure that text and elementId are present due to the query. Otherwise, safer to use `record.get("text", default_value)`
                {"text": record["text"], "elementId": record["elementId"]}
                for record in records
            ]

            # write it to our own file to store
            file_writer = WriteDataOnFile(filename=filename, path=path)
            await file_writer.open()
            
            for record in results:
                await file_writer.write(data=record)  # Serialize dict to JSON string before writing
            await file_writer.close()
            
        except Exception as e:
            print(f"CHANGE ABSOLUTE PATH IF ERROR OCCURED IN FILE WRITER.\nError: {e}")
            raise e
        
if __name__ == "__main__":
    """
    run: python -m neo4j_db.scripts_with_data.neo4jHelpers
    """
    import asyncio

    filename = "AllNodesTextWithID.jsonl" # store it in current directory and note jsonl extension
    
    # uncomment to run
    asyncio.run(fetch_all_node_texts(path=DIRECTORY_PATH, filename=filename))