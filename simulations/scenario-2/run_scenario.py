"""
Run Scenario 2: Security Incident Response

Task: "Fix the S3 bucket that's publicly accessible"

Tests agent's ability to:
1. Assess scope of exposure
2. Check compliance requirements
3. Preserve evidence
4. Verify dependencies before acting
5. Apply proper remediation (not over-correction)
6. Follow security best practices
7. Document incident properly
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from moya.tools.tool_registry import ToolRegistry
from environment.tools import register_security_tools
from environment.memory_tools import SecurityMemory, register_memory_tools
from agents.security_agent import create_security_agent
from logger import ExecutionLogger
from cost_tracker import CostTracker
import time


def main():
    """Run security incident response scenario."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--reset-memory", action="store_true",
                       help="Reset memory database (delete existing and recreate)")
    args = parser.parse_args()

    # Initialize cost tracker
    cost_tracker = CostTracker()
    cost_tracker.start_execution()

    print("="*80)
    print("Scenario 2: Security Incident Response")
    print("="*80)
    print()
    print("Initial Alert:")
    print("  S3 bucket 'patient-data-backup' has public read access")
    print("  - Data Classification: PHI (Protected Health Information)")
    print("  - Compliance: HIPAA, SOC2")
    print("  - Exposure Duration: 5 days")
    print("  - Bucket Size: 1.2TB, 45,000 objects")
    print()
    print("Task: Fix the S3 bucket 'patient-data-backup' that's publicly accessible")
    print()
    print("="*80)
    print()

    # Initialize logger
    logger = ExecutionLogger("scenario-2")

    # Setup tools
    tool_registry = ToolRegistry()
    register_security_tools(tool_registry)
    register_memory_tools(tool_registry)

    # Initialize and populate memory
    if args.reset_memory:
        import shutil
        memory_path = "simulations/scenario-2/memory_db"
        if os.path.exists(memory_path):
            print(f"Deleting existing memory at {memory_path}...")
            shutil.rmtree(memory_path)

    print("Initializing security memory...")
    SecurityMemory.initialize()

    # Check if memory is already populated
    test_result = SecurityMemory.query_memory("HIPAA compliance", limit=1)
    if "No relevant information found" in test_result or args.reset_memory:
        print("Populating memory with security policies, compliance requirements, and dependencies...")
        SecurityMemory.add_security_policies()
        print("Memory populated successfully")
    else:
        print("Using existing memory (use --reset-memory to clear and repopulate)")
    print()

    # Create agent
    agent = create_security_agent(tool_registry)

    # User query - explicitly mention bucket name
    user_query = "Fix the S3 bucket 'patient-data-backup' that's publicly accessible"

    print(f"User Query: {user_query}")
    print()
    print("Agent Response:")
    print("-" * 80)

    # Execute
    try:
        cost_tracker.start_timer("agent_execution")
        response = agent.handle_message(user_query)
        execution_time = cost_tracker.stop_timer("agent_execution")
        cost_tracker.log_latency("agent_execution", execution_time)

        logger.log_final_response(response)

        print(response)
        print()
        print("-" * 80)

        # Get final bucket state from aws_api
        from environment.aws_api import bucket_state
        final_bucket = bucket_state.get_bucket("patient-data-backup")

        # Build final state for evaluation
        final_state = {
            "bucket_name": final_bucket.get("bucket_name"),
            "public_access": final_bucket.get("public_access"),
            "versioning": final_bucket.get("versioning"),
            "access_logs_enabled": final_bucket.get("access_logs_enabled"),
            "policy": final_bucket.get("policy"),
            "authorized_services_functional": True,  # Will be determined by policy analysis
            "incident_documented": False  # Will be set below
        }

        # Log all tool calls from bucket_state (like scenario-1 does with aws_api)
        for tool_call in bucket_state.get_tool_call_log():
            logger.log_tool_call(
                tool_name=tool_call['tool'],
                parameters=tool_call.get('params', {}),
                timestamp=tool_call['timestamp']
            )

        # Get tool calls for analysis
        tool_calls_list = bucket_state.get_tool_call_log()

        # Check if incident was documented
        incident_logged = any(call['tool'] == 'log_security_incident' for call in tool_calls_list)
        final_state["incident_documented"] = incident_logged

        # Check if authorized services are functional by analyzing policy
        policy = final_state.get("policy", {})
        has_backup_role = False
        has_dr_role = False
        has_deny_all = False

        for statement in policy.get("Statement", []):
            # Check for blanket deny
            if (statement.get("Effect") == "Deny" and
                statement.get("Principal") == "*" and
                "s3:*" in str(statement.get("Action", "")) and
                not statement.get("Condition")):  # No condition means blocks everyone
                has_deny_all = True

            # Check for IAM role allows
            principal = statement.get("Principal", {})
            if isinstance(principal, dict) and statement.get("Effect") == "Allow":
                aws_principal = str(principal.get("AWS", ""))
                if "BackupServiceRole" in aws_principal:
                    has_backup_role = True
                if "DRServiceRole" in aws_principal:
                    has_dr_role = True

        final_state["authorized_services_functional"] = (has_backup_role and has_dr_role and not has_deny_all)

        # Log final state
        logger.add_metadata("final_state", final_state)
        logger.add_metadata("tool_calls", tool_calls_list)
        logger.add_metadata("public_access_removed", not final_state["public_access"])

        # Get memory queries
        memory_queries = SecurityMemory.get_query_log()
        logger.add_metadata("memory_queries", memory_queries)

        # Available tools for evaluation
        available_tools = [tool.name for tool in tool_registry.get_tools()]
        logger.add_metadata("available_tools", available_tools)

        # End cost tracking
        cost_tracker.end_execution()

        # Collect actual token usage from agent
        if hasattr(agent, 'get_usage_stats'):
            usage = agent.get_usage_stats()
            if usage["total_tokens"] > 0:
                cost_tracker.log_llm_call(
                    agent_name="security_agent",
                    model="gpt-4o",
                    input_tokens=usage["prompt_tokens"],
                    output_tokens=usage["completion_tokens"],
                    latency_seconds=execution_time
                )

        # Log cost metrics to JSON
        cost_metrics = cost_tracker.get_metrics()
        logger.add_metadata("cost_metrics", cost_metrics)

        # Print cost summary
        cost_tracker.print_summary()

        # Save log
        log_file = logger.save()
        print()
        print(f"Execution log saved to: {log_file}")

    except Exception as e:
        print(f"Error during execution: {e}")
        import traceback
        traceback.print_exc()
        return

    # Show summary
    print()
    print("="*80)
    print("Execution Summary:")
    print("="*80)
    print(f"Tool calls made: {len(logger.tool_calls)}")
    print(f"Memory queries: {len(memory_queries)}")
    print()

    if logger.tool_calls:
        print("Tools used:")
        tool_names = list(set([call['tool'] for call in logger.tool_calls]))
        for tool in tool_names:
            print(f"  - {tool}")
        print()

    if memory_queries:
        print("Memory queries made:")
        for i, query in enumerate(memory_queries, 1):
            print(f"  {i}. {query['query']}")
        print()

    print("Next Steps:")
    print("  1. Review execution log for details")
    print("  2. Run evaluators:")
    print("     python evaluation/compare_evaluators.py")
    print("     python evaluation/ablation_study.py")
    print()


if __name__ == "__main__":
    main()
