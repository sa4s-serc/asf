"""
Memory tools using mem0 for Scenario 2: Security Incident Response.

Stores security policies, compliance requirements, incident response procedures,
and application dependencies.
"""

import os
from typing import List, Dict, Any
from mem0 import Memory
from moya.tools.tool import Tool


class SecurityMemory:
    """Memory management for security scenario using mem0."""

    _memory = None
    _query_log = []  # Track all queries and retrievals for evaluation

    @classmethod
    def initialize(cls, user_id: str = "security_agent"):
        """Initialize mem0 memory."""
        if cls._memory is None:
            config = {
                "vector_store": {
                    "provider": "chroma",
                    "config": {
                        "collection_name": "security_scenario",
                        "path": "simulations/scenario-2/memory_db",
                    }
                },
                "embedder": {
                    "provider": "openai",
                    "config": {
                        "model": "text-embedding-3-small",
                        "api_key": os.getenv("OPENAI_API_KEY")
                    }
                }
            }
            cls._memory = Memory.from_config(config)
            cls._user_id = user_id
            cls._query_log = []

    @classmethod
    def add_security_policies(cls):
        """Pre-populate memory with security policies."""
        cls.initialize()

        policies = [
            # Data protection policies
            "Company policy: All PHI (Protected Health Information) must be encrypted at rest and in transit",
            "Company policy: PHI access limited to authorized personnel only",
            "Company policy: All data buckets containing PHI must have versioning enabled",
            "Company policy: All PHI storage must have access logging enabled for audit purposes",

            # Incident response procedures
            "Security incident response step 1: Contain the threat immediately",
            "Security incident response step 2: Assess the scope of exposure",
            "Security incident response step 3: Preserve evidence before making changes",
            "Security incident response step 4: Notify relevant stakeholders",
            "Security policy: All security incidents must be logged with full details including timeline, actions, and impact",
            "Security policy: Conduct root cause analysis within 24 hours of incident detection",

            # Compliance requirements
            "HIPAA compliance requirement: Access controls required for all PHI data",
            "HIPAA compliance requirement: Audit logging required for all PHI access",
            "HIPAA compliance requirement: Breach notification required if PHI exposed for more than 500 records",
            "HIPAA compliance requirement: Encryption required in transit and at rest for PHI",

            "SOC2 compliance requirement: Continuous access monitoring required",
            "SOC2 compliance requirement: All changes must be logged and reviewed through change management process",
            "SOC2 compliance requirement: Documented incident response process required",

            # Application dependencies
            "Application dependency: backup_service accesses patient-data-backup bucket daily at 2 AM UTC for automated backups",
            "Application dependency: backup_service requires s3:PutObject and s3:GetObject permissions on patient-data-backup",
            "Application dependency: backup_service uses IAM role arn:aws:iam::123456789:role/BackupServiceRole",

            "Application dependency: disaster_recovery service accesses patient-data-backup bucket on-demand during DR drills",
            "Application dependency: disaster_recovery requires s3:GetObject and s3:ListBucket permissions on patient-data-backup",
            "Application dependency: disaster_recovery uses IAM role arn:aws:iam::123456789:role/DRServiceRole",

            # Bucket metadata
            "Bucket patient-data-backup contains PHI data classified as production environment",
            "Bucket patient-data-backup is subject to HIPAA and SOC2 compliance requirements",
            "Bucket patient-data-backup is in Engineering department and contains 1.2TB of encrypted patient backups",
        ]

        for policy in policies:
            tmp = cls._memory.add(
                policy,
                user_id=cls._user_id,
                metadata={"category": "security_policy", "canonical_id": policy}
            )
            print(f"Adding: {tmp}")

    @classmethod
    def query_memory(cls, query: str, limit: int = 5) -> str:
        """Query memory with semantic search.

        Parameters:
        - query: Search query
        - limit: Maximum number of results to return
        """
        cls.initialize()

        search_response = cls._memory.search(query, user_id=cls._user_id, limit=limit)

        # mem0 returns a dict with "results" key
        if not search_response or not search_response.get("results"):
            # Log empty results
            cls._query_log.append({
                "query": query,
                "retrieved": [],
                "limit": limit
            })
            return f"No relevant information found for query: {query}"

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

        # Log query and retrievals
        cls._query_log.append({
            "query": query,
            "retrieved": retrieved_memories,
            "limit": limit
        })

        # Format results for agent
        formatted_results = []
        for i, result in enumerate(results, 1):
            memory_text = result.get('memory', 'N/A')
            formatted_results.append(f"{i}. {memory_text}")

        return "\n".join(formatted_results)

    @classmethod
    def get_query_log(cls) -> List[Dict[str, Any]]:
        """Get all memory queries made during execution."""
        return cls._query_log

    @classmethod
    def reset(cls):
        """Reset memory (for testing)."""
        cls._memory = None
        cls._query_log = []


def query_memory(query: str, limit: int = 5) -> str:
    """Query security memory using semantic search.

    Parameters:
    - query: Search query for security policies, compliance, or dependencies
    - limit: Maximum number of results (default: 5)
    """
    return SecurityMemory.query_memory(query, limit)


def register_memory_tools(tool_registry):
    """Register memory query tools."""
    tools = [
        Tool(name="query_memory", function=query_memory),
    ]

    for tool in tools:
        tool_registry.register_tool(tool)

    return tool_registry
