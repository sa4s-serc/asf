"""
Memory Tools for Scenario 3 using mem0

Provides semantic memory for performance baselines, infrastructure configuration,
recent changes, operational policies, and network topology.
"""

import os
from typing import List, Optional
from mem0 import Memory
from moya.tools.tool_registry import ToolRegistry
from moya.tools.tool import Tool


class AgentMemory:
    """Memory system for RCA agents using mem0."""

    _memory_backend = None
    _query_log = []  # Track all queries for evaluation
    _user_id = "rca_session"

    @classmethod
    def get_backend(cls) -> Memory:
        """Initialize and return singleton mem0 backend."""
        if cls._memory_backend is None:
            print("Initializing mem0 memory backend...")
            config = {
                "vector_store": {
                    "provider": "chroma",
                    "config": {
                        "collection_name": "scenario3_rca_memory",
                        "path": "simulations/scenario-3/memory_db"
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

    @classmethod
    def initialize(cls):
        """Ensure backend is initialized."""
        if cls._memory_backend is None:
            cls.get_backend()

    @staticmethod
    def store_memory(content: str, category: str) -> str:
        """Store information in memory.

        Parameters:
        - content: The information to store
        - category: Category of information (baseline, infrastructure, change, policy, topology, incident)
        """
        backend = AgentMemory.get_backend()
        if not backend:
            return "Memory system unavailable"

        try:
            result = backend.add(
                content,
                user_id=AgentMemory._user_id,
                metadata={"category": category, "canonical_id": content}
            )
            print(result)
            return f"Stored {category}: {content}"
        except Exception as e:
            return f"Error storing memory: {str(e)}"

    @staticmethod
    def query_memory(query: str, limit: int = 5) -> str:
        """Query stored memory for relevant information.

        Parameters:
        - query: Natural language query
        - limit: Maximum results to return
        """
        AgentMemory.initialize()

        # Log the query for evaluation
        AgentMemory._query_log.append({
            "query": query,
            "limit": limit
        })

        backend = AgentMemory.get_backend()
        if not backend:
            if AgentMemory._query_log:
                AgentMemory._query_log[-1]["retrieved"] = []
            return "Memory system unavailable"

        try:
            search_response = backend.search(query, user_id=AgentMemory._user_id, limit=limit)

            # mem0 returns a dict with "results" key
            if not search_response or not search_response.get("results"):
                if AgentMemory._query_log:
                    AgentMemory._query_log[-1]["retrieved"] = []
                return f"No relevant memories found for: {query}"

            results = search_response["results"]

            # Log retrieved memories
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

            if AgentMemory._query_log:
                AgentMemory._query_log[-1]["retrieved"] = retrieved_memories

            # Format results for agent
            response = f"Found {len(results)} relevant memory/memories:\n\n"
            for i, result in enumerate(results, 1):
                memory_text = result.get('memory', 'N/A')
                response += f"{i}. {memory_text}\n"

            return response.strip()

        except Exception as e:
            if AgentMemory._query_log:
                AgentMemory._query_log[-1]["retrieved"] = []
                AgentMemory._query_log[-1]["error"] = str(e)
            return f"Error querying memory: {str(e)}"


def seed_memory():
    """Pre-populate memory with comprehensive context for RCA scenario.

    Seeds memory with:
    - Performance baselines (what normal looks like)
    - Infrastructure configuration (service topology, dependencies)
    - Recent changes (change history with timestamps)
    - Operational policies (troubleshooting procedures, guardrails)
    - Network topology (VPC, subnets, CIDRs, security group associations)
    - Incident response procedures
    """
    print("Seeding memory with comprehensive RCA context...")

    # ===== PERFORMANCE BASELINES =====
    print("  - Seeding performance baselines...")

    AgentMemory.store_memory(
        "payment-service baseline performance: avg_response_time=1.5s, p95_response_time=2.1s, p99_response_time=3.2s, error_rate=0.8%, cpu_avg=45%, memory_avg=65%, throughput=1000 requests/minute",
        "baseline"
    )

    AgentMemory.store_memory(
        "payment-service performance thresholds: response_time degradation > 30% triggers alert, error_rate > 2% triggers investigation, CPU > 80% requires analysis",
        "baseline"
    )

    AgentMemory.store_memory(
        "prod-payment-db baseline metrics: cpu_utilization=30-40%, active_connections=40-60, connection_utilization=8-12%, query_latency_avg=50ms",
        "baseline"
    )

    # ===== INFRASTRUCTURE CONFIGURATION =====
    print("  - Seeding infrastructure configuration...")

    AgentMemory.store_memory(
        "payment-service infrastructure: runs on 3 m5.xlarge EC2 instances (i-abc123, i-abc124, i-abc125) in subnet 10.0.2.0/24, uses security group sg-app-tier, deployed in us-east-1",
        "infrastructure"
    )

    AgentMemory.store_memory(
        "payment-service depends on prod-payment-db PostgreSQL database at endpoint prod-payment-db.cluster-xyz.us-east-1.rds.amazonaws.com port 5432 for all transaction processing",
        "infrastructure"
    )

    AgentMemory.store_memory(
        "prod-payment-db configuration: PostgreSQL RDS instance in subnet 10.0.3.0/24 (database_tier), protected by security group sg-abc123, handles all payment transaction data",
        "infrastructure"
    )

    AgentMemory.store_memory(
        "payment-service security group sg-app-tier: allows inbound HTTP (80) and HTTPS (443) from anywhere, allows all outbound traffic, located in vpc-main",
        "infrastructure"
    )

    AgentMemory.store_memory(
        "prod-payment-db security group sg-abc123: controls database access via inbound rules on port 5432, critical for database connectivity, located in vpc-main",
        "infrastructure"
    )

    AgentMemory.store_memory(
        "payment-service uses connection pooling with 3 retry attempts per database operation, timeout=10 seconds per attempt, total operation timeout=30 seconds",
        "infrastructure"
    )

    # ===== RECENT CHANGES (with precise timestamps) =====
    print("  - Seeding recent change history...")

    AgentMemory.store_memory(
        "Change CHG-2024-0115-001 at 2024-01-15T08:15:00Z: security_group_modification on sg-abc123 by admin@company.com - Modified inbound rules for RDS security group, changed from allowing 10.0.0.0/16 (entire VPC) to only allowing 10.0.1.0/24 (admin subnet) on port 5432",
        "change"
    )

    AgentMemory.store_memory(
        "Security group sg-abc123 change details: BEFORE allowed port 5432 from 10.0.0.0/16 (entire VPC including app tier), AFTER allows port 5432 from only 10.0.1.0/24 (admin subnet only), reason given: 'Tighten security - limit database access to specific subnet'",
        "change"
    )

    AgentMemory.store_memory(
        "Change CHG-2024-0110-003 at 2024-01-10T14:00:00Z: code_deployment of payment-service v2.3.1 by ci-cd-pipeline - Routine bug fixes for payment validation and updated logging configuration, no performance changes expected",
        "change"
    )

    AgentMemory.store_memory(
        "Change CHG-2024-0108-007 at 2024-01-08T16:30:00Z: infrastructure_scaling of payment-service by devops@company.com - Scaled from 2 to 3 instances (added i-abc125) for proactive capacity increase",
        "change"
    )

    AgentMemory.store_memory(
        "Timeline of recent changes: Jan 8 (scaling), Jan 10 (code deployment v2.3.1), Jan 15 08:15 AM (security group modification) - most recent change was security configuration",
        "change"
    )

    # ===== OPERATIONAL POLICIES (troubleshooting workflows) =====
    print("  - Seeding operational policies...")

    AgentMemory.store_memory(
        "Performance troubleshooting workflow: Step 1 - Check for recent configuration changes in last 24 hours, Step 2 - Verify network connectivity between components, Step 3 - Analyze resource utilization metrics, Step 4 - Review application logs for error patterns, Step 5 - Correlate timing of symptoms with change events",
        "policy"
    )

    AgentMemory.store_memory(
        "Scaling policy: Only scale infrastructure AFTER ruling out configuration issues, network problems, and application bugs. Scaling adds cost without fixing root causes. Always identify root cause before scaling.",
        "policy"
    )

    AgentMemory.store_memory(
        "Configuration change correlation rule: If symptoms started within 30 minutes of a configuration change, investigate that change first as likely root cause before exploring other hypotheses",
        "policy"
    )

    AgentMemory.store_memory(
        "Database connectivity troubleshooting: When applications show DatabaseConnectionTimeout errors, check: 1) Security group rules allow source to destination, 2) Network ACLs permit traffic, 3) Database is running and accepting connections, 4) Connection pooling configuration is correct",
        "policy"
    )

    AgentMemory.store_memory(
        "Multi-domain issue escalation policy: If performance issue involves multiple domains (performance + security + network), coordinate between specialized agents rather than acting in isolation. Performance agent should consult security agent for configuration issues.",
        "policy"
    )

    AgentMemory.store_memory(
        "Root cause analysis requirements: Must identify root cause (not just symptoms) before remediation, must correlate timing of symptoms with events, must verify hypothesis with targeted checks, must document causal chain from root cause to observed symptoms",
        "policy"
    )

    # ===== NETWORK TOPOLOGY (detailed subnet/CIDR info) =====
    print("  - Seeding network topology...")

    AgentMemory.store_memory(
        "VPC vpc-main network topology: CIDR 10.0.0.0/16 contains three subnets - admin subnet 10.0.1.0/24 (bastion, VPN), app_tier subnet 10.0.2.0/24 (application servers), database_tier subnet 10.0.3.0/24 (databases)",
        "topology"
    )

    AgentMemory.store_memory(
        "Subnet details for payment-service: application instances run in app_tier subnet 10.0.2.0/24 in availability zone us-east-1b, uses public route table for internet access",
        "topology"
    )

    AgentMemory.store_memory(
        "Subnet details for prod-payment-db: database runs in database_tier subnet 10.0.3.0/24 in availability zone us-east-1c, uses private route table, no direct internet access",
        "topology"
    )

    AgentMemory.store_memory(
        "Admin subnet 10.0.1.0/24: contains bastion hosts and VPN gateway in availability zone us-east-1a, uses public route table, typically used for administrative access to resources",
        "topology"
    )

    AgentMemory.store_memory(
        "Network path payment-service to database: source 10.0.2.0/24 (app_tier) must reach destination 10.0.3.0/24 (database_tier) on port 5432, requires security group sg-abc123 to allow 10.0.2.0/24 as source",
        "topology"
    )

    AgentMemory.store_memory(
        "Security group to subnet mapping: sg-app-tier protects resources in 10.0.2.0/24 (payment-service instances), sg-abc123 protects resources in 10.0.3.0/24 (prod-payment-db)",
        "topology"
    )

    # ===== INCIDENT RESPONSE PROCEDURES =====
    print("  - Seeding incident response procedures...")

    AgentMemory.store_memory(
        "Incident response workflow for performance degradation: 1) Gather symptoms from monitoring, 2) Check recent changes, 3) Perform temporal correlation analysis (symptom time vs change time), 4) Form hypothesis about root cause, 5) Validate hypothesis with targeted tests, 6) Apply targeted fix (not generic scaling), 7) Verify metrics return to baseline",
        "incident_response"
    )

    AgentMemory.store_memory(
        "Temporal correlation analysis: If symptom onset is within 5-10 minutes of a configuration change, high probability of causal relationship. Changes propagate within 1-5 minutes in AWS. Investigate that change as primary suspect.",
        "incident_response"
    )

    AgentMemory.store_memory(
        "Error pattern analysis: DatabaseConnectionTimeout errors indicate network connectivity or security group issues, not application load. Check security groups and network path before assuming resource constraints.",
        "incident_response"
    )

    AgentMemory.store_memory(
        "CPU spike investigation: If CPU increases but database connectivity is failing, CPU spike is likely symptom (retry overhead) not cause. Look for connection errors before concluding CPU is the problem.",
        "incident_response"
    )

    AgentMemory.store_memory(
        "Multi-agent coordination for RCA: Root Cause Analysis agent should gather findings from Performance agent (metrics) and Security agent (configuration), correlate findings, identify causal chain, then coordinate targeted remediation",
        "incident_response"
    )

    # ===== KNOWN FAILURE PATTERNS =====
    print("  - Seeding known failure patterns...")

    AgentMemory.store_memory(
        "Common failure pattern: Security group rules overly restrictive after security hardening efforts. Symptom: sudden connectivity loss. Root cause: security group rule removed legitimate source CIDR. Fix: add correct source CIDR to security group.",
        "failure_pattern"
    )

    AgentMemory.store_memory(
        "Anti-pattern: Scaling in response to high CPU without checking error logs. If errors show connection failures, scaling adds cost but does not fix connectivity issues. New instances have same connection problems.",
        "failure_pattern"
    )

    AgentMemory.store_memory(
        "Symptom vs root cause distinction: High CPU, slow response times, elevated error rates are symptoms. Root cause is the underlying issue causing symptoms (e.g., security group blocking database access causes connection retries which cause CPU spike).",
        "failure_pattern"
    )

    print("Memory seeded successfully with comprehensive RCA context.")


def create_memory_tools() -> ToolRegistry:
    """Create and register memory tools for agents.

    Returns:
        ToolRegistry with memory storage and query tools
    """
    tool_registry = ToolRegistry()

    # Store memories
    tool_registry.register_tool(Tool(
        name="store_memory",
        function=AgentMemory.store_memory,
        parameters={
            "content": {
                "type": "string",
                "description": "The information to store"
            },
            "category": {
                "type": "string",
                "description": "Category: baseline, infrastructure, change, policy, topology, incident_response, failure_pattern"
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
            "limit": {
                "type": "integer",
                "description": "Maximum results to return (default: 5)"
            }
        }
    ))

    return tool_registry
