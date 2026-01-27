"""
Script to test the OpenAI API connectivity and the async client.

Run command:
python -m src.tests.openai_api_test
"""
import asyncio
from src.config.llm_clients.openai_client import get_openai_client

async def test_openai_connection():
    """
    Tests the OpenAI client by making a simple request to gpt-5-mini (cheapest)
    """
    print("Initializing OpenAI client...")
    async with get_openai_client() as client:
        print("Sending request to gpt-5-mini...") 
        # For chat completions, use client.chat.completions.create
        try:
            # Using the responses API as requested. 
            # Note: If this fails type checking, it may be due to the beta status of the responses API.
            response = await client.responses.create(
                model="gpt-5-mini",
                input="Only Reply with OK",
                max_output_tokens=5
            )
            print(f"Received response: {response}")
        except Exception as e:
            print(f"Error connecting to OpenAI: {e}")

if __name__ == "__main__":
    asyncio.run(test_openai_connection())
