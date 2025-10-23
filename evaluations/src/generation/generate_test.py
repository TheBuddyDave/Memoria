"""minimal test to see whether the LLM is working"""

from openai import OpenAI

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

resp = client.chat.completions.create(
    model="llama3.2",
    messages=[
        {"role": "user", "content": "what is 1+1?"}
    ],
)
print(resp.choices[0].message.content)
