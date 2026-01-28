"""
⚠️ See warnings in main function before running this script. 

❗ SERIOUSLY, BE CAREFUL RUNNING THIS. IT WILL MAKE LOTS OF OPENAI API CALLS AND COST YOU MONEY.
💣 RUNNING COLLECTION FILL WITH SAME DATA WILL CREATE DUPLICATES IN MILVUS 

 Run: python -m milvus.scripts_with_data.reasoning_filler
"""

from milvus.scripts_with_data.helpers import WriteDataOnFile, ReasoningBankEntry, AsyncMilvus, AsyncOpenAIClient
import asyncio
# make sure this is filled with the entries we will append to. 
from milvus.scripts_with_data.reasoning_entries import entries


async def create_reasoning_embeddings(indices_to_process: list[int] | None = None) -> None:
    """
    ⚠️ BE CAREFUL RUNNING THIS. It will make lots of OpenAI API calls and cost money. ⚠️
    
    Will create embeddings for all entries defined above and store them in ReasoningBankData.jsonl.\n
    **Note:** this function does NOT insert anything into Milvus. It only creates embeddings and stores them in a file.
    
    ALSO NOTE: If indices_to_process is provided, only those entries will be processed. This is useful for generating embeddings for failed entries from a previous run.
    ALSO NOTE: the failed indices are printed so please copy them from console to run in next round. 
    
    Args:
        indices_to_process: Optional list of indices to process. If None, process all entries from the entries list above.
    """
    openai_async = AsyncOpenAIClient()
    writer = WriteDataOnFile(filename="ReasoningBankData.jsonl") # should be in same directory as this script
    await writer.open()
    
    # Limit concurrent API calls to avoid rate limits
    sem = asyncio.Semaphore(value=100)  # Max 100 concurrent embedding requests (my current Rate limit is 3000/minute (tier 1))
    
    async def process_entry(entry: dict, index: int) -> tuple[int, dict | Exception]:
        """
        Process single entry with rate limiting.
        """
        try:
            async with sem:  # Acquire semaphore slot (blocks if all slots taken)
                key_lesson_vector, context_to_prefer_vector = await asyncio.gather(
                    openai_async.get_embedding(text=entry["key_lesson"]),
                    openai_async.get_embedding(text=entry["context_to_prefer"])
                )
            # Semaphore automatically released here
            
            enriched_entry = {
                **entry,
                "key_lesson_vector": key_lesson_vector,
                "context_to_prefer_vector": context_to_prefer_vector
            }
            
            print("Processed entry = ", index)
            # Write enriched entry to file immediately
            await writer.write(data=enriched_entry)
            return (index, enriched_entry)
        except Exception as e:
            # if error occurs we return the index so we can log it and run it later.
            return (index, e)

    # Gather all the tasks so we can run them concurrently
    if indices_to_process is None:
        tasks = [process_entry(entry=entry, index=i) for i, entry in enumerate(entries)]
    else:
        tasks = [process_entry(entry=entries[i], index=i) for i in indices_to_process]

    # gather all the results.
    results = await asyncio.gather(*tasks)
    
    # now we must iterate to find if any call failed and log that
    failed_indices: list[tuple[int, str]] = []
    successful_indices: list[int] = []
    for index, result in results:
        if isinstance(result, Exception):
            failed_indices.append((index, str(result)))
        else:
            successful_indices.append(index)
    
    print(f"Successfully processed entries at indices: {successful_indices}")
    
    # print failed indices with ther error messages
    if failed_indices:
        print("Failed to process the following entries:")
        for index, error_msg in failed_indices:
            print(f"Index {index} : Error =  {error_msg}")
    else:
        print("All entries processed successfully.")
    
    await writer.close()
    await openai_async.close()

async def populate_reasoning_bank_collection() -> None:
    """
    Populate the Milvus reasoning bank collection with entries stored in ReasoningBankData.json
    """
    
    milvus_client = AsyncMilvus(collection_name="reasoningbank")
    
    # ❗make sure this file exists in the same directory as this script and contains the complete entries with embeddings.
    reader = WriteDataOnFile(filename="ReasoningBankData.jsonl")
    
    # Read and validate entries before inserting into Milvus
    index = 0
    enriched_entries: list[ReasoningBankEntry] = []
    failed_indices: list[int] = []
    async for entry in reader.read():
        try:
            enriched_entry = ReasoningBankEntry.model_validate(obj=entry)
            enriched_entries.append(enriched_entry)
            print(f"Validated index = {index}")
        except Exception as e:
            print(f"At index {index} : Error =  {e}")
            failed_indices.append(index)
        index += 1    
        
    print("Reader closed")
    print(f"Failed to validate entries at indices: {failed_indices}")

    # Insert into Milvus (NOTE: I didn't batch limit this but I don't expect reasoning bank entries to be a large enough number for now)
    print(f"Inserting {len(enriched_entries)} entries into Milvus reasoning bank collection...")
    await milvus_client.insert_entries(entries=enriched_entries)
    print("Insertion complete.")
     
    await milvus_client.close()
    
if __name__ == "__main__":
    
    # ⚠️ BE CAREFUL RUNNING THIS. It will make lots of OpenAI API calls and cost you money. ⚠️
    # asyncio.run(create_reasoning_embeddings())
    
    # ⚠️ WARNING: Running this on already inserted data WILL CREATE DUPLICATES in Milvus since it used "insert" operation.
    # DO NOT RUN THIS MULTIPLE TIMES ON SAME DATA. See duplication warning here: https://docs.zilliz.com/docs/insert-entities
    # asyncio.run(populate_reasoning_bank_collection())
    pass