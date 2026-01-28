"""
Run: python -m milvus.scripts_with_data.graphembedding_filler
"""

import asyncio
from milvus.scripts_with_data.helpers import AsyncMilvus, WriteDataOnFile, GraphEmbeddingsEntry, AsyncOpenAIClient
from neo4j_db.scripts_with_data.neo4jHelpers import DIRECTORY_PATH as NEO4J_DIRECTORY_PATH

async def create_graphembeddings(directory_path: str, filename: str, indices_to_process: list[int] | None = None) -> None:
    """
    💣 WARNING:This will make LOTS OF API CALLS - $$$$ COSTS MONEYYYYY $$$$$
    Loads JSON entries from the given file (expects 'text' and 'elementId' fields), generates embeddings using OpenAI in batches of size 100.
    Stores the complete entry with embeddings into 'GraphEmbeddingsData.jsonl'.
    
    Args:
        directory_path (str): Directory where the input file is located.
        filename (str): Name of the input JSON file.
        indices_to_process (list[int] | None): Optional list of indices to process. If None, processes all entries.
    
    Returns:
        None
    """
    writer = WriteDataOnFile(filename="GraphEmbeddingsData.jsonl")
    reader = WriteDataOnFile(filename=filename, path=directory_path)
    await writer.open()
    
    openai_client = AsyncOpenAIClient()
    
    # Create semaphore to limit concurrent OpenAI requests
    batch_size = 100 # my tier (tier 1) allows 3000 per minute
    sem = asyncio.Semaphore(value=batch_size)
    
    # Loop through all entries and create tasks
    tasks = []
    
    async def process_entry(entry_index: int, entry: dict) -> tuple[int, GraphEmbeddingsEntry | Exception]:
        async with sem: 
            try:
                embedding = await openai_client.get_embedding(text=entry["text"])
                
                print(f"Created embedding for index = {entry_index}")
                
                # note we are validating here 
                result = GraphEmbeddingsEntry(
                    pointer_to_node=entry["elementId"],
                    text=entry["text"],
                    dense_vector=embedding
                )
                # write immediately to file to avoid data loss on large runs
                await writer.write(result.model_dump())
                return (entry_index, result)
            except Exception as e:
                print(f"Failed to process entry at index {entry_index}: {e}")
                return (entry_index, e)
    
    index = 0
    async for entry in reader.read():
        # Check if the entry should be processed based on indices_to_process (if none then process all entries)
        if indices_to_process is not None and index not in indices_to_process:
            index += 1
            continue
        else:
            # Add the get embedding task to the list
            tasks.append(asyncio.create_task(process_entry(entry_index=index, entry=entry)))
            index += 1
    
    successful_indices = []
    failed_indices = []
    
    # Gather all tasks (concurrency already limited by semaphore in each)
    results = await asyncio.gather(*tasks)
    
    # loop through results and write successful ones to file, log failed indices
    for idx, result in results:
        if isinstance(result, Exception):
            failed_indices.append(idx)
        else:
            successful_indices.append(idx)
    
    # Log summary
    print(f"Successful Indices: {successful_indices} \nFailed Indices: {failed_indices}")
    
    await writer.close()
    await openai_client.close()

async def fill_graphembeddings_collection(batch_size: int = 200) -> None:
    """
    Populate the Milvus graphembeddings collection with entries from GraphEmbeddingsData.jsonl.
    Reads and inserts entries in batches of `batch_size`. Entries are already validated.
    
    Args:
        batch_size (int): Number of entries to insert in Milvus in each batch. Defaults to 200.
    
    Returns:
        None
    """
    milvus_client = AsyncMilvus(collection_name="graphembeddings")
    
    # Read entries from file
    reader = WriteDataOnFile(filename="GraphEmbeddingsData.jsonl")
    
    # Read entries and collect in batches
    batch: list[GraphEmbeddingsEntry] = []
    batch_count = 0
    total_entries = 0
    
    async for entry in reader.read():
        batch.append(GraphEmbeddingsEntry.model_validate(obj=entry))
        total_entries += 1
        
        # Insert when batch is full
        if len(batch) == batch_size:
            batch_count += 1
            await milvus_client.insert_entries(entries=batch)
            print(f"Inserted batch {batch_count} = ({len(batch)} entries)")
            batch = [] # empty batch after insertion
    
    # Insert remaining entries in the last batch (leftovers less than batch size)
    if batch:
        batch_count += 1
        await milvus_client.insert_entries(entries=batch)
        print(f"Inserted batch {batch_count} = ({len(batch)} entries)")
    
    print(f"Reader closed. Total entries inserted: {total_entries}")
    
    await milvus_client.close()

if __name__ == "__main__":
    # ⚠️ Running this costs API money
    # asyncio.run(create_graphembeddings(directory_path=NEO4J_DIRECTORY_PATH, filename="AllNodesTextWithID.jsonl"))
    
    # ⚠️ Running this on same data again will create duplicate entries in Milvus collection! DO NOT RUN MULTIPLE TIMES. HAVE TO EMPTY COLLECTION FIRST.
    # asyncio.run(fill_graphembeddings_collection(batch_size=200))
    pass
