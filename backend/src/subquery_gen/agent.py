from typing import Optional
from src.config.llm_clients.openai_client import get_openai_client
from src.subquery_gen.prompts import SYSTEM_PROMPT
from src.subquery_gen.schemas import OutputModel

class SubqueryGenerator:
    """
    Does three things:
    1) asks for clarification if allowed AND needed. 
    2) decomposes user query to subqueries based on conversation history (if available)
    """
    def __init__(self, 
                 ask_clarifications: bool = True, 
                 conversation_history: str = ""
                 ):
        self.ask_clarifications = ask_clarifications
        self.conversation_history = conversation_history
        self.model: str = "gpt-5-mini"
        self.prompt_cache_key = "subquery_gen_prompt"
        self.output_pydantic_model = OutputModel
    
    async def arun(self, user_query: str) -> Optional[OutputModel]:
        """
        Calls OpenAI API with the given prompt and returns the response text.
        """
        async with get_openai_client() as client:
            response = await client.responses.parse(
                model=self.model,
                prompt_cache_key=self.prompt_cache_key,
                prompt_cache_retention="in-memory",
                text_format=self.output_pydantic_model,
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_query},
                    {"role": "user", "content": "Conversation history so far:\n" + self.conversation_history}
                ]
            )
            return response.output_parsed
    
    