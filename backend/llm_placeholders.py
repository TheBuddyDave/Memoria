"""
Placeholder LLM functions for Query Generator and Memory Updater.
In production, these would call actual LLM APIs (OpenAI, Anthropic, etc.).
"""
from typing import List, Dict
from models import Message, Memory, SubQuery, MemoryUpdate


def query_generator_llm(
    user_question: str,
    conversation_history: List[Message],
    iteration: int = 0,
    previous_memories: List[Memory] = None
) -> Dict:
    """
    Placeholder for Query Generator LLM.
    
    This LLM analyzes the user's question and conversation history to generate
    sub-queries for memory retrieval. It can iterate multiple times.
    
    Args:
        user_question: The user's current question
        conversation_history: Full conversation history
        iteration: Current iteration number (0 = first call)
        previous_memories: Memories retrieved in previous iterations
    
    Returns:
        Dict with 'sub_queries' (list of SubQuery) and 'continue' (bool)
    """
    
    # Placeholder logic: Generate relevant sub-queries based on keywords
    sub_queries = []
    
    if iteration == 0:
        # First iteration: Generate broad queries
        if "performance" in user_question.lower() or "accuracy" in user_question.lower() or "benchmark" in user_question.lower():
            sub_queries.append(SubQuery(
                query="Model performance evaluation methodology and best practices",
                purpose="Retrieve established methodologies and analytical frameworks for model performance assessment"
            ))
            sub_queries.append(SubQuery(
                query="historical benchmark results and performance trends",
                purpose="Identify previous performance analyses and their conclusions"
            ))
        
        if "training" in user_question.lower() or "dataset" in user_question.lower():
            sub_queries.append(SubQuery(
                query="Training data quality and dataset characteristics",
                purpose="Retrieve information about dataset composition, quality issues, and data collection practices"
            ))
        
        if "model" in user_question.lower() or "architecture" in user_question.lower():
            sub_queries.append(SubQuery(
                query="Model architecture and implementation details",
                purpose="Locate model-specific technical details and architectural decisions"
            ))
        
        # If no specific keywords, generate a general query
        if not sub_queries:
            sub_queries.append(SubQuery(
                query=user_question,
                purpose="Perform semantic search across memory database for relevant information"
            ))
        
        # For demo, we'll do a second iteration if we found relevant terms
        should_continue = len(sub_queries) > 1
        
    else:
        # Second iteration: Refine based on previous results
        if previous_memories and len(previous_memories) > 0:
            # Check if we found data sources, if so, query for related analyses
            has_datasource = any(mem.id.startswith("N1005") for mem in previous_memories)
            if has_datasource:
                sub_queries.append(SubQuery(
                    query="analyses using benchmark datasets",
                    purpose="Identify related analytical work utilizing comparable data sources"
                ))
        
        # Stop after second iteration for demo
        should_continue = False
    
    return {
        "sub_queries": sub_queries,
        "continue": should_continue
    }


def memory_updater_llm(
    user_question: str,
    agent_response: str,
    agent_reasoning: str,
    memories_used: List[Memory],
    conversation_history: List[Message]
) -> List[MemoryUpdate]:
    """
    Placeholder for Memory Updater LLM.
    
    This LLM analyzes the interaction and decides what memory updates to make.
    
    Args:
        user_question: The user's question
        agent_response: The agent's response
        agent_reasoning: The agent's reasoning process
        memories_used: Memories that were used
        conversation_history: Full conversation history
    
    Returns:
        List of MemoryUpdate objects
    """
    
    updates = []
    
    # Placeholder logic: Create different types of updates based on the interaction
    
    # 1. Always save the user's question as a UserRequest node
    updates.append(MemoryUpdate(
        action="add",
        memory_type="node",
        content=f"UserRequest: {user_question}",
        metadata={
            "node_label": "UserRequest",
            "conv_id": "demo_conversation",
            "tags": extract_keywords(user_question)
        }
    ))
    
    # 2. Save the agent's answer as an AgentAnswer node
    updates.append(MemoryUpdate(
        action="add",
        memory_type="node",
        content=f"AgentAnswer: {agent_response}",
        metadata={
            "node_label": "AgentAnswer",
            "conv_id": "demo_conversation",
            "tags": extract_keywords(agent_response)
        }
    ))
    
    # 3. If reasoning revealed a new insight, consider adding to ReasoningBank
    if "important" in agent_reasoning.lower() or "consideration" in agent_reasoning.lower() or "insight" in agent_reasoning.lower():
        updates.append(MemoryUpdate(
            action="add",
            memory_type="reasoning",
            content=f"Analytical insight: {agent_reasoning[:200]}",
            metadata={
                "context": user_question,
                "tags": extract_keywords(agent_reasoning)
            }
        ))
    
    # 4. Create edges between related memories
    if len(memories_used) > 0:
        updates.append(MemoryUpdate(
            action="add",
            memory_type="edge",
            content=f"Query context linked to relevant historical data",
            metadata={
                "from_node": "current_request",
                "to_nodes": [mem.id for mem in memories_used],
                "weight": 0.8,
                "tags": ["retrieval", "context"]
            }
        ))
    
    return updates


def extract_keywords(text: str) -> List[str]:
    """
    Simple keyword extraction for demonstration.
    In production, this would use NLP techniques.
    """
    # Common words to exclude
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", 
                  "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
                  "be", "have", "has", "had", "do", "does", "did", "will", "would", "could",
                  "should", "may", "might", "can", "this", "that", "these", "those"}
    
    words = text.lower().split()
    keywords = [w.strip(".,!?;:") for w in words if len(w) > 3 and w not in stop_words]
    
    # Return unique keywords
    return list(set(keywords[:10]))  # Limit to 10 keywords

