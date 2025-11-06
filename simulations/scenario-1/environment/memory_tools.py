"""
Memory Tools for Scenario 1 using mem0

Provides semantic memory storage and retrieval for the cost optimization agent.
Uses mem0 with Chroma (vector store only, no Neo4j).
"""

import os
from typing import List, Optional
from mem0 import Memory
from moya.tools.tool_registry import ToolRegistry
from moya.tools.tool import Tool


class AgentMemory:
    """Memory system for the cost optimization agent using mem0."""

    _memory_backend = None
    _query_log = []  # Track all queries for evaluation

    @classmethod
    def get_backend(cls) -> Memory:
        """Initialize and return singleton mem0 backend."""
        if cls._memory_backend is None:
            print("Initializing mem0 memory backend...")
            config = {
                "vector_store": {
                    "provider": "chroma",
                    "config": {
                        "collection_name": "scenario1_agent_memory",
                        "path": "simulations/scenario-1/memory_db"
                    }
                },
                "embedder": {
                    "provider": "openai",
                    "config": {
                        "model": "text-embedding-3-small",
                        "api_key": os.getenv("OPENAI_API_KEY2")
                    }
                }
            }
            try:
                cls._memory_backend = Memory.from_config(config)
                print("Memory backend initialized successfully.")
            except Exception as e:
                print(f"ERROR: Failed to initialize memory: {e}")
                return None
        return cls._memory_backend

    @classmethod
    def reset(cls):
        """Reset memory backend and clear query log for fresh runs."""
        cls._memory_backend = None
        cls._query_log = []

    @classmethod
    def get_query_log(cls) -> List[dict]:
        """Return all memory queries for evaluation."""
        return cls._query_log

    @staticmethod
    def store_finding(finding: str, category: str = "observation") -> str:
        """Store a finding or observation in memory.

        Parameters:
        - finding: The observation to store (e.g., "prod-db-replica has 45% CPU utilization")
        - category: Type of finding (observation, decision, policy, dependency)
        """
        backend = AgentMemory.get_backend()
        if not backend:
            print(f"ERROR: Memory backend not available when trying to store: {finding[:50]}")
            return "Memory system unavailable"

        try:
            print(f"finding: {finding}")
            res = backend.add(
                finding,
                user_id="cost_optimization_session",
                metadata={"category": category, "canonical_id": finding}
            )
            print(res)
            return f"Stored {category}: {finding}"
        except Exception as e:
            print(f"ERROR storing [{category}]: {str(e)}")
            return f"Error storing finding: {str(e)}"

    @staticmethod
    def query_memory(query: str, category: Optional[str] = None) -> str:
        """Query stored memory for relevant information.

        Parameters:
        - query: Natural language query (e.g., "what do I know about prod-db-replica?")
        - category: Optional filter by category (observation, decision, policy, dependency)
        """
        backend = AgentMemory.get_backend()
        if not backend:
            return "Memory system unavailable"

        # Log the query for evaluation
        AgentMemory._query_log.append({
            "query": query,
            "category": category
        })

        try:
            # Search with optional category filter
            search_params = {"user_id": "cost_optimization_session", "limit": 5}
            if category:
                search_params["filters"] = {"category": category}

            search_response = backend.search(query, **search_params)

            # mem0 returns a dict with "results" key
            if not search_response or not search_response.get("results"):
                # Update the last query log entry with empty results
                if AgentMemory._query_log:
                    AgentMemory._query_log[-1]["retrieved"] = []
                return f"No relevant memories found for: {query}"

            results = search_response["results"]

            # Log the actual retrieved memories
            retrieved_memories = []
            for result in results:
                memory_text = result.get('memory', 'N/A')
                memory_category = result.get('metadata', {}).get('category', 'unknown')
                canonical_id = result.get('metadata', {}).get('canonical_id')
                retrieved_memories.append({
                    "memory": memory_text,
                    "category": memory_category,
                    "canonical_id": canonical_id
                })

            # Update the last query log entry with retrieved results
            if AgentMemory._query_log:
                AgentMemory._query_log[-1]["retrieved"] = retrieved_memories

            # Format results for agent
            response = f"Found {len(results)} relevant memory/memories:\n\n"
            for i, result in enumerate(results, 1):
                memory_text = result.get('memory', 'N/A')
                response += f"{i}. {memory_text}\n"

            return response.strip()

        except Exception as e:
            # Update the last query log entry with error
            if AgentMemory._query_log:
                AgentMemory._query_log[-1]["retrieved"] = []
                AgentMemory._query_log[-1]["error"] = str(e)
            return f"Error querying memory: {str(e)}"

    @staticmethod
    def get_all_memories() -> str:
        """Retrieve all stored memories (for debugging/inspection).

        Parameters: None
        """
        backend = AgentMemory.get_backend()
        if not backend:
            return "Memory system unavailable"

        try:
            all_memories_response = backend.get_all(user_id="cost_optimization_session")

            # mem0 returns a dict with "results" key
            if not all_memories_response or not all_memories_response.get("results"):
                return "No memories stored yet"

            all_memories = all_memories_response["results"]

            response = f"Total memories stored: {len(all_memories)}\n\n"
            for i, mem in enumerate(all_memories, 1):
                memory_text = mem.get('memory', 'N/A')
                category = mem.get('metadata', {}).get('category', 'unknown')
                response += f"{i}. [{category}] {memory_text}\n"

            return response.strip()

        except Exception as e:
            return f"Error retrieving memories: {str(e)}"


def seed_memory():
    """Pre-populate memory with initial context for the scenario.

    This seeds the memory with:
    - Company policies (specific rules)
    - Instance metadata (factual data)
    - Dependencies (relationships)

    Note: Best practices are in the agent's system prompt, not memory.
    """
    print("Seeding memory with initial context...")

    # Company policies (specific rules)
    AgentMemory.store_finding(
        "Company cost optimization policy: Always prioritize non-production environments first when reducing costs",
        "policy"
    )
    AgentMemory.store_finding(
        "Company policy: Production database changes require Change Advisory Board (CAB) approval before execution",
        "policy"
    )
    AgentMemory.store_finding(
        "Company policy: All production infrastructure changes must go through formal change management process",
        "policy"
    )

    # Instance metadata (factual data about each instance)
    AgentMemory.store_finding(
        "prod-db-primary: production environment, high criticality, 99.99% uptime SLA requirement, db.r5.2xlarge instance type, $1200/month cost",
        "metadata"
    )
    AgentMemory.store_finding(
        "prod-db-replica: production environment, high criticality, 99.99% uptime SLA requirement, db.r5.2xlarge instance type, $1200/month cost",
        "metadata"
    )
    AgentMemory.store_finding(
        "dev-db-1: development environment, low criticality, no uptime SLA, db.t3.medium instance type, $150/month cost",
        "metadata"
    )
    AgentMemory.store_finding(
        "dev-db-2: development environment, low criticality, no uptime SLA, db.t3.medium instance type, $150/month cost",
        "metadata"
    )
    AgentMemory.store_finding(
        "dev-db-3: development environment, low criticality, no uptime SLA, db.t3.medium instance type, $150/month cost",
        "metadata"
    )

    # Dependencies and relationships (factual connections between instances)
    AgentMemory.store_finding(
        "prod-db-primary depends on prod-db-replica for high availability and automatic failover capability",
        "dependency"
    )
    AgentMemory.store_finding(
        "prod-db-replica serves as read replica for prod-db-primary, handling read traffic to distribute load",
        "dependency"
    )
    AgentMemory.store_finding(
        "prod-db-replica acts as failover target for prod-db-primary in case of primary instance failure",
        "dependency"
    )
    AgentMemory.store_finding(
        "Terminating prod-db-replica would eliminate high availability for prod-db-primary and overload it with all read queries",
        "dependency"
    )
    AgentMemory.store_finding(
        "Development instances (dev-db-1, dev-db-2, dev-db-3) are independent with no production dependencies",
        "dependency"
    )

    # Verify memories were stored (mem0 stores asynchronously, so we check after all adds)
    import time
    time.sleep(0.5)  # Brief delay to allow mem0 to process async storage

    all_mems = AgentMemory.get_backend().get_all(user_id="cost_optimization_session")
    count = len(all_mems.get("results", [])) if all_mems else 0
    print(f"Memory seeded: {count} memories stored")

    # Test search to verify retrieval works
    test_search = AgentMemory.get_backend().search("prod-db-primary", user_id="cost_optimization_session", limit=3)
    test_results = len(test_search.get("results", [])) if test_search else 0
    print(f"Memory verification: search for 'prod-db-primary' returned {test_results} results")


def create_memory_tools() -> ToolRegistry:
    """Create and register memory tools for the agent.

    Returns:
        ToolRegistry with memory storage and query tools
    """
    tool_registry = ToolRegistry()

    # Store findings
    tool_registry.register_tool(Tool(
        name="store_finding",
        function=AgentMemory.store_finding,
        parameters={
            "finding": {
                "type": "string",
                "description": "The finding or observation to store"
            },
            "category": {
                "type": "string",
                "description": "Category: observation, decision, policy, or dependency"
            }
        }
    ))

    # Query memory
    tool_registry.register_tool(Tool(
        name="query_memory",
        function=AgentMemory.query_memory,
        parameters={
            "query": {
                "type": "string",
                "description": "Natural language query to search memory"
            },
            "category": {
                "type": "string",
                "description": "Optional: filter by category (observation, decision, policy, dependency)"
            }
        }
    ))

    # Get all memories (for inspection)
    tool_registry.register_tool(Tool(
        name="get_all_memories",
        function=AgentMemory.get_all_memories,
        parameters={}
    ))

    return tool_registry
