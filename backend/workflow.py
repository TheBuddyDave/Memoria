"""
Main workflow orchestration for the AI research analyst agent.
Implements the complete workflow from user query to memory updates.
"""
from typing import List, Tuple
from models import Message, Memory, SubQuery, MemoryUpdate, AgentResponse
from llm_placeholders import query_generator_llm, memory_updater_llm
from database import DatabaseRetrieval


class AIResearchAnalystWorkflow:
    """
    Orchestrates the complete workflow:
    1. User asks question
    2. Query Generator creates sub-queries
    3. Database retrieval finds relevant memories
    4. Agent reasons and responds
    5. Memory Updater decides on database modifications
    """
    
    def __init__(self):
        """Initialize the workflow with database connection."""
        self.db = DatabaseRetrieval()
        self.max_query_iterations = 3  # Prevent infinite loops
    
    def process_user_query(
        self, 
        user_question: str, 
        conversation_history: List[Message]
    ) -> Tuple[AgentResponse, List[SubQuery], List[MemoryUpdate]]:
        """
        Process a user query through the complete workflow.
        
        Args:
            user_question: The user's question
            conversation_history: Previous messages in the conversation
        
        Returns:
            Tuple of (agent_response, sub_queries_generated, memory_updates)
        """
        print("\n" + "="*80)
        print("WORKFLOW INITIATED")
        print("="*80)
        
        # Step 2 & 3: Query Generation and Memory Retrieval (iterative)
        all_memories, all_sub_queries = self._query_and_retrieve_loop(
            user_question, 
            conversation_history
        )
        
        # Step 4: Agent Reasoning and Response
        agent_response = self._agent_reasoning(
            user_question,
            all_memories,
            conversation_history
        )
        
        # Step 5: Memory Updates
        memory_updates = self._update_memories(
            user_question,
            agent_response,
            conversation_history
        )
        
        print("\n" + "="*80)
        print("WORKFLOW COMPLETE")
        print("="*80 + "\n")
        
        return agent_response, all_sub_queries, memory_updates
    
    def _query_and_retrieve_loop(
        self,
        user_question: str,
        conversation_history: List[Message]
    ) -> Tuple[List[Memory], List[SubQuery]]:
        """
        Steps 2-3: Iteratively generate queries and retrieve memories.
        
        Returns:
            Tuple of (all_memories, all_sub_queries)
        """
        print("\nPHASE 1: QUERY GENERATION & MEMORY RETRIEVAL")
        print("-" * 80)
        
        all_memories = []
        all_sub_queries = []
        iteration = 0
        should_continue = True
        
        while should_continue and iteration < self.max_query_iterations:
            print(f"\nIteration {iteration + 1}")
            
            # Step 2: Generate sub-queries
            query_result = query_generator_llm(
                user_question,
                conversation_history,
                iteration,
                all_memories if iteration > 0 else None
            )
            
            sub_queries = query_result["sub_queries"]
            should_continue = query_result["continue"]
            
            print(f"  Generated {len(sub_queries)} sub-queries:")
            for sq in sub_queries:
                print(f"     - '{sq.query}'")
                print(f"       Purpose: {sq.purpose}")
            
            all_sub_queries.extend(sub_queries)
            
            # Step 3: Retrieve memories for each sub-query
            for sub_query in sub_queries:
                memories = self.db.retrieve_memories(sub_query.query)
                all_memories.extend(memories)
            
            iteration += 1
        
        # Remove duplicates based on memory ID
        unique_memories = []
        seen_ids = set()
        for mem in all_memories:
            if mem.id not in seen_ids:
                unique_memories.append(mem)
                seen_ids.add(mem.id)
        
        print(f"\nTotal unique memories retrieved: {len(unique_memories)}")
        
        return unique_memories, all_sub_queries
    
    def _agent_reasoning(
        self,
        user_question: str,
        memories: List[Memory],
        conversation_history: List[Message]
    ) -> AgentResponse:
        """
        Step 4: Agent analyzes memories and generates response.
        
        In production, this would use an LLM with the retrieved memories as context.
        """
        print("\nPHASE 2: AGENT REASONING & RESPONSE")
        print("-" * 80)
        
        question_lower = user_question.lower()
        
        # Detect question type for customized responses
        is_model_performance = ("model" in question_lower and ("performance" in question_lower or "accuracy" in question_lower or "benchmark" in question_lower))
        is_training_data = ("training" in question_lower and "data" in question_lower) or ("dataset" in question_lower)
        is_research_paper = ("paper" in question_lower or "research" in question_lower) and ("present" in question_lower or "presentation" in question_lower)
        
        # Analyze what types of memories we have
        node_memories = [m for m in memories if m.type == "node"]
        reasoning_memories = [m for m in memories if m.type == "reasoning"]
        path_memories = [m for m in memories if m.type == "path"]
        
        # Build reasoning steps
        reasoning_steps = []
        reasoning_steps.append(
            f"Retrieved {len(node_memories)} graph nodes, "
            f"{len(reasoning_memories)} reasoning entries, "
            f"and {len(path_memories)} path relationships."
        )
        
        # Check for high-relevance memories
        high_relevance = [m for m in memories if m.relevance_score > 0.7]
        if high_relevance:
            reasoning_steps.append(
                f"Identified {len(high_relevance)} highly relevant memories (relevance score > 0.7)."
            )
        
        # Generate customized reasoning and response based on question type
        if is_model_performance:
            reasoning, response = self._generate_model_performance_response(memories, reasoning_memories, node_memories)
        elif is_training_data:
            reasoning, response = self._generate_training_data_response(memories, reasoning_memories, node_memories)
        elif is_research_paper:
            reasoning, response = self._generate_research_paper_response(memories, reasoning_memories, node_memories)
        else:
            # Generic response for other questions
            reasoning, response = self._generate_generic_response(memories, reasoning_memories, node_memories)
        
        # Combine reasoning steps
        reasoning_steps.extend(reasoning)
        reasoning_text = " → ".join(reasoning_steps)
        
        print(f"  Reasoning: {reasoning_text}")
        print(f"  Response generated ({len(response)} characters)")
        
        return AgentResponse(
            response=response,
            reasoning=reasoning_text,
            memories_used=memories
        )
    
    def _generate_model_performance_response(
        self, 
        memories: List[Memory], 
        reasoning_memories: List[Memory],
        node_memories: List[Memory]
    ) -> Tuple[List[str], str]:
        """Generate customized response for model performance question."""
        reasoning = []
        
        # Find relevant memories
        performance_memory = next((m for m in node_memories if "model" in m.content.lower() and ("performance" in m.content.lower() or "accuracy" in m.content.lower())), None)
        methodology_memory = next((m for m in node_memories if "evaluation" in m.content.lower() or "benchmark" in m.content.lower()), None)
        performance_reasoning = next((m for m in reasoning_memories if "performance" in m.content.lower() or "evaluation" in m.content.lower()), None)
        
        reasoning.append("Question requires model performance analysis, which involves both benchmark results and evaluation methodology considerations.")
        
        if performance_memory:
            reasoning.append(f"Found historical performance data: {performance_memory.content[:80]}...")
        
        if methodology_memory:
            reasoning.append("Identified relevant methodology for model evaluation and benchmarking.")
        
        if performance_reasoning:
            reasoning.append("Applying critical methodology guidance regarding evaluation best practices.")
        
        # Build response
        response_parts = []
        
        # Reasoning section (like ChatGPT's thinking)
        response_parts.append("**Reasoning:**")
        response_parts.append("")
        response_parts.append("To accurately assess model performance, I need to consider:")
        response_parts.append("1. Benchmark results from recent evaluations")
        response_parts.append("2. Methodological considerations (evaluation metrics, test sets, data leakage)")
        response_parts.append("3. Contextual factors that may impact performance comparisons")
        response_parts.append("")
        response_parts.append("Historical analysis has shown that unadjusted performance metrics can be significantly skewed by data leakage, test set contamination, and evaluation methodology differences. These considerations are critical for accurate assessment.")
        response_parts.append("")
        
        # Output section
        response_parts.append("**Analysis:**")
        response_parts.append("")
        
        if performance_memory:
            response_parts.append("Based on recent benchmark data:")
            response_parts.append("")
            response_parts.append(f"- {performance_memory.content}")
            response_parts.append("")
        
        if methodology_memory:
            response_parts.append("**Methodology Applied:**")
            response_parts.append("")
            response_parts.append(f"- {methodology_memory.content}")
            response_parts.append("")
        
        response_parts.append("**Key Takeaways:**")
        response_parts.append("")
        response_parts.append("- Model demonstrated strong performance with 15% improvement over baseline")
        response_parts.append("- Accuracy improved by 8% after adjusting for data leakage")
        response_parts.append("- Proper evaluation controls (test set isolation and accounting for data contamination) are essential for accurate performance assessment")
        
        return reasoning, "\n".join(response_parts)
    
    def _generate_training_data_response(
        self,
        memories: List[Memory],
        reasoning_memories: List[Memory],
        node_memories: List[Memory]
    ) -> Tuple[List[str], str]:
        """Generate customized response for training data question."""
        reasoning = []
        
        # Find relevant memories
        dataset_event = next((m for m in node_memories if "dataset" in m.content.lower() or "training" in m.content.lower()), None)
        data_reasoning = next((m for m in reasoning_memories if "data" in m.content.lower() or "external" in m.content.lower()), None)
        
        reasoning.append("Question seeks information about training data and dataset considerations affecting model development.")
        
        if dataset_event:
            reasoning.append(f"Found specific dataset information: {dataset_event.content[:80]}...")
        
        if data_reasoning:
            reasoning.append("Applying context about data quality and external factors.")
        
        # Build response
        response_parts = []
        
        # Reasoning section
        response_parts.append("**Reasoning:**")
        response_parts.append("")
        response_parts.append("Training data quality and composition can significantly impact model performance and generalization.")
        response_parts.append("I'll identify relevant datasets and their characteristics, including data quality issues and biases.")
        response_parts.append("")
        
        if data_reasoning:
            response_parts.append(f"Context: {data_reasoning.content}")
            response_parts.append("")
        
        # Output section
        response_parts.append("**Training Data Information:**")
        response_parts.append("")
        
        if dataset_event:
            response_parts.append("**Dataset Details:**")
            response_parts.append("")
            response_parts.append(f"{dataset_event.content}")
            response_parts.append("")
            
            # Extract dates if available
            if dataset_event.metadata:
                metadata = dataset_event.metadata
                if "start_date" in metadata and "end_date" in metadata:
                    response_parts.append(f"**Collection Period:** {metadata['start_date']} to {metadata['end_date']}")
                    response_parts.append("")
        
        response_parts.append("**Impact Analysis:**")
        response_parts.append("")
        response_parts.append("- Data quality issues reduced model accuracy by 12%")
        response_parts.append("- Affected model: Transformer-based language model")
        response_parts.append("- Duration: Approximately 3 months of data collection")
        response_parts.append("")
        response_parts.append("**Recommendation:**")
        response_parts.append("When analyzing model performance, always consider data quality issues like label noise, distribution shifts, and dataset biases, as these factors can significantly impact model accuracy and generalization capabilities.")
        
        return reasoning, "\n".join(response_parts)
    
    def _generate_research_paper_response(
        self,
        memories: List[Memory],
        reasoning_memories: List[Memory],
        node_memories: List[Memory]
    ) -> Tuple[List[str], str]:
        """Generate customized response for research paper presentation question."""
        reasoning = []
        
        # Find relevant memories
        paper_preference = next((m for m in node_memories if "paper" in m.content.lower() or "prefer" in m.content.lower()), None)
        presentation_reasoning = next((m for m in reasoning_memories if "paper" in m.content.lower() or "present" in m.content.lower()), None)
        
        reasoning.append("Question concerns research paper presentation preferences for academic stakeholders.")
        
        if paper_preference:
            reasoning.append(f"Found specific preference data: {paper_preference.content[:80]}...")
        
        if presentation_reasoning:
            reasoning.append("Applying presentation best practices for research audiences.")
        
        # Build response
        response_parts = []
        
        # Reasoning section
        response_parts.append("**Reasoning:**")
        response_parts.append("")
        response_parts.append("Effective research presentation requires understanding audience preferences and communication styles.")
        response_parts.append("I'll identify specific preferences and recommended presentation formats for research papers.")
        response_parts.append("")
        
        if presentation_reasoning:
            response_parts.append(f"Guidance: {presentation_reasoning.content}")
            response_parts.append("")
        
        # Output section
        response_parts.append("**Presentation Recommendations:**")
        response_parts.append("")
        
        if paper_preference:
            response_parts.append("**Stakeholder Preferences:**")
            response_parts.append("")
            response_parts.append(f"- {paper_preference.content}")
            response_parts.append("")
        
        response_parts.append("**Recommended Format:**")
        response_parts.append("")
        response_parts.append("1. **Use clear visualizations** for data presentation")
        response_parts.append("   - Line charts for performance trends")
        response_parts.append("   - Bar charts for comparative metrics")
        response_parts.append("   - Tables for detailed numerical results")
        response_parts.append("")
        response_parts.append("2. **Structure your presentation:**")
        response_parts.append("   - Lead with problem statement and motivation")
        response_parts.append("   - Present methodology clearly")
        response_parts.append("   - Highlight key results and contributions")
        response_parts.append("   - Discuss limitations and future work")
        response_parts.append("")
        response_parts.append("3. **Focus on reproducibility:**")
        response_parts.append("   - Include hyperparameters and experimental setup")
        response_parts.append("   - Provide code and dataset references")
        response_parts.append("   - Document evaluation metrics clearly")
        response_parts.append("")
        response_parts.append("**Best Practice:**")
        response_parts.append("For research paper presentations, use clear visualizations with detailed methodology sections. Focus on reproducibility and provide comprehensive experimental details to ensure maximum clarity and scientific rigor.")
        
        return reasoning, "\n".join(response_parts)
    
    def _generate_generic_response(
        self,
        memories: List[Memory],
        reasoning_memories: List[Memory],
        node_memories: List[Memory]
    ) -> Tuple[List[str], str]:
        """Generate generic response for other questions."""
        reasoning = []
        
        reasoning.append("Analyzing retrieved memories to synthesize a comprehensive response.")
        
        if reasoning_memories:
            reasoning.append(f"Applying historical reasoning patterns: {reasoning_memories[0].content[:80]}...")
        
        reasoning.append("Synthesizing insights from retrieved memory data.")
        
        # Build response
        response_parts = []
        
        response_parts.append("**Reasoning:**")
        response_parts.append("")
        response_parts.append("Analyzing available historical data and analytical insights to provide a comprehensive assessment.")
        response_parts.append("")
        
        if memories:
            response_parts.append("**Analysis:**")
            response_parts.append("")
            
            sorted_memories = sorted(memories, key=lambda x: x.relevance_score, reverse=True)
            for i, mem in enumerate(sorted_memories[:3]):
                response_parts.append(f"{chr(65+i)}. {mem.content}")
            
            if reasoning_memories:
                response_parts.append("")
                response_parts.append("**Additional Context:**")
                response_parts.append("")
                response_parts.append(f"{reasoning_memories[0].content}")
        else:
            response_parts.append("**Analysis:**")
            response_parts.append("")
            response_parts.append("I do not currently have sufficient historical data to provide a comprehensive analysis.")
            response_parts.append("This query has been logged for future reference and will inform subsequent analyses.")
        
        return reasoning, "\n".join(response_parts)
    
    def _update_memories(
        self,
        user_question: str,
        agent_response: AgentResponse,
        conversation_history: List[Message]
    ) -> List[MemoryUpdate]:
        """
        Step 5: Decide on memory updates.
        """
        print("\nPHASE 3: MEMORY UPDATES")
        print("-" * 80)
        
        # Call Memory Updater LLM
        updates = memory_updater_llm(
            user_question,
            agent_response.response,
            agent_response.reasoning,
            agent_response.memories_used,
            conversation_history
        )
        
        print(f"  Proposed {len(updates)} memory updates:")
        for i, update in enumerate(updates, 1):
            content_preview = update.content[:60] if update.content else update.memory_id
            print(f"     {i}. {update.action.upper()} {update.memory_type}: {content_preview}...")
        
        # Execute the updates
        for update in updates:
            if update.action == "add":
                new_id = self.db.add_memory(
                    update.memory_type,
                    update.content,
                    update.metadata
                )
                update.memory_id = new_id
            elif update.action == "update":
                self.db.update_memory(
                    update.memory_id,
                    update.content,
                    update.metadata
                )
            elif update.action == "delete":
                self.db.delete_memory(update.memory_id)
        
        print(f"  Executed {len(updates)} memory update operations")
        
        return updates

