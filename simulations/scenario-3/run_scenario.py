"""
Run Scenario 3: Performance Degradation Root Cause Analysis

Executes multi-agent RCA investigation and captures all interactions for evaluation.
"""

from environment import PerformanceAPI, create_performance_tools, create_security_tools, create_rca_tools
from environment.memory_tools import create_memory_tools, AgentMemory, seed_memory
from agents import create_performance_agent, create_security_agent, create_rca_agent, create_classifier_agent
from logger import ExecutionLogger
from cost_tracker import CostTracker
from moya.registry.agent_registry import AgentRegistry
from moya.orchestrators.multi_agent_orchestrator import MultiAgentOrchestrator
from moya.classifiers.llm_classifier import LLMClassifier
import shutil
from pathlib import Path
import time


def main():
    """Execute Scenario 3 and log everything."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--reset-memory", action="store_true",
                       help="Reset memory database (delete existing and recreate)")
    args = parser.parse_args()

    # Initialize logger and cost tracker
    logger = ExecutionLogger(scenario_name="scenario-3")
    cost_tracker = CostTracker()
    cost_tracker.start_execution()

    print("="*80)
    print("SCENARIO 3: Performance Degradation Root Cause Analysis")
    print("="*80)
    print()

    # Initialize environment
    print("Initializing performance monitoring environment...")
    api = PerformanceAPI()

    initial_state = api.get_current_state()
    logger.log_initial_state({
        "service_status": initial_state["services"]["payment-service"]["status"],
        "avg_response_time": initial_state["metrics"]["payment-service"]["avg_response_time"],
        "error_rate": initial_state["metrics"]["payment-service"]["error_rate"],
        "cpu_utilization": initial_state["metrics"]["payment-service"]["cpu_utilization"]
    })

    print("Initial state:")
    print(f"  Service: payment-service - Status: {initial_state['services']['payment-service']['status']}")
    print(f"  Response time: {initial_state['metrics']['payment-service']['avg_response_time']}s (degraded)")
    print(f"  Error rate: {initial_state['metrics']['payment-service']['error_rate']}%")
    print(f"  CPU: {initial_state['metrics']['payment-service']['cpu_utilization']}%")
    print()

    # Setup memory
    print("Setting up memory system...")
    memory_db_path = Path("simulations/scenario-3/memory_db")

    if args.reset_memory:
        if memory_db_path.exists():
            shutil.rmtree(memory_db_path)
            print("Cleared previous memory database")
        AgentMemory.reset()

    # Initialize memory backend
    AgentMemory.initialize()

    # Check if memory is already populated
    test_result = AgentMemory.query_memory("performance baseline", limit=1)
    if "No relevant" in test_result or args.reset_memory:
        print("Populating memory with RCA context (baselines, policies, topology, changes)...")
        seed_memory()
        print("Memory populated successfully")
    else:
        print("Using existing memory (use --reset-memory to clear and repopulate)")
    print()

    # Create tool registries and agents
    print("Creating specialized tool sets and agents...")

    # Memory tools shared by all
    memory_tools = create_memory_tools()

    # Step 1: Create Performance and Security agents first (they don't delegate)
    performance_tools = create_performance_tools(api)
    for tool in memory_tools.get_tools():
        performance_tools.register_tool(tool)
    performance_agent = create_performance_agent(performance_tools)

    security_tools = create_security_tools(api)
    for tool in memory_tools.get_tools():
        security_tools.register_tool(tool)
    security_agent = create_security_agent(security_tools)

    # Step 2: Create RCA tools including agent delegation
    from environment.agent_delegation_tools import create_agent_delegation_tools

    rca_tools = create_rca_tools(api)
    for tool in memory_tools.get_tools():
        rca_tools.register_tool(tool)

    # Add agent delegation tools to RCA
    agent_delegation_tools = create_agent_delegation_tools(
        performance_agent=performance_agent,
        security_agent=security_agent,
        api=api
    )
    for tool in agent_delegation_tools.get_tools():
        rca_tools.register_tool(tool)

    # Step 3: Create RCA agent with all tools
    rca_agent = create_rca_agent(rca_tools)

    # Classifier
    classifier_agent = create_classifier_agent()

    print(f"  ✓ Performance Agent ({len(list(performance_tools.get_tools()))} tools)")
    print(f"  ✓ Security Agent ({len(list(security_tools.get_tools()))} tools)")
    print(f"  ✓ RCA Agent ({len(list(rca_tools.get_tools()))} tools - includes agent delegation)")
    print(f"  ✓ Classifier Agent")
    print()

    # Setup agent registry
    print("Setting up multi-agent orchestrator...")
    agent_registry = AgentRegistry()
    agent_registry.register_agent(performance_agent)
    agent_registry.register_agent(security_agent)
    agent_registry.register_agent(rca_agent)

    # Create classifier
    classifier = LLMClassifier(classifier_agent, default_agent="rca_agent")

    # Create orchestrator
    orchestrator = MultiAgentOrchestrator(
        agent_registry=agent_registry,
        classifier=classifier,
        default_agent_name="rca_agent"
    )
    print("  ✓ Multi-agent orchestrator configured")
    print()

    # Log metadata
    logger.add_metadata("agents", ["performance_agent", "security_agent", "rca_agent"])
    logger.add_metadata("orchestrator_type", "MultiAgentOrchestrator")

    # Comprehensive task that naturally requires multiple specialized agents
    task = """CRITICAL INCIDENT: Production payment-service experiencing severe performance degradation.

OBSERVED SYMPTOMS (starting 08:20 UTC):
- Response time: 2.4s (baseline: 1.5s) - 60% degradation
- Error rate: 5.2% (baseline: 0.8%)
- CPU utilization: 85% (baseline: 45%)
- DatabaseConnectionTimeout errors in application logs

RECENT CHANGES:
- Security group sg-abc123 modified at 08:15 UTC (5 min before symptoms)
- Change made by: admin@company.com

SYSTEM CONTEXT:
- Application tier: subnet 10.0.2.0/24
- Database: prod-payment-db (requires port 5432 connectivity)
- Service deployment: 3 instances in auto-scaling group

INVESTIGATION REQUIREMENTS:
1. Analyze performance metrics to quantify impact and identify error patterns
2. Investigate security group configuration and verify network connectivity paths
3. Perform temporal correlation between the configuration change and symptom onset
4. Identify the root cause through causal chain analysis (not just symptoms)
5. Apply targeted remediation to restore baseline performance

CRITICAL: Do NOT just scale up instances - that treats symptoms and wastes $800/month. Find and fix the root cause."""

    logger.log_task(task)

    print(f"TASK:\n{task}")
    print()
    print("-"*80)
    print()

    # Execute with multi-agent orchestrator
    print("Starting multi-agent investigation...")
    print()

    def stream_callback(chunk):
        print(chunk, end="", flush=True)

    print("\nInvestigation:\n")

    # Track orchestration latency
    cost_tracker.start_timer("orchestration")
    response = orchestrator.orchestrate(
        thread_id="rca_session",
        user_message=task,
        stream_callback=stream_callback
    )
    orchestration_time = cost_tracker.stop_timer("orchestration")
    cost_tracker.log_latency("orchestration", orchestration_time)

    print()
    print()
    print("-"*80)
    print()
    print("INVESTIGATION RESULTS:")
    print(response)
    print()

    # Log agent response
    logger.log_agent_response(response)

    # Get final state
    final_state = api.get_current_state()
    logger.log_final_state({
        "service_status": final_state["services"]["payment-service"]["status"],
        "avg_response_time": final_state["metrics"]["payment-service"]["avg_response_time"],
        "error_rate": final_state["metrics"]["payment-service"]["error_rate"],
        "cpu_utilization": final_state["metrics"]["payment-service"]["cpu_utilization"],
        "problem_resolved": final_state["problem_resolved"],
        "actions_taken": final_state["actions_taken"],
        "security_groups": final_state["security_groups"]
    })

    # Log all tool calls from API
    for tool_call in api.get_tool_call_log():
        logger.log_tool_call(
            tool_name=tool_call['tool'],
            parameters=tool_call.get('params', {}),
            timestamp=tool_call['timestamp']
        )

    # Log memory queries and results
    memory_queries = AgentMemory.get_query_log()
    logger.add_metadata("memory_queries", memory_queries)
    logger.add_metadata("memory_queries_count", len(memory_queries))

    # Extract memory results for evaluation (flatten retrieved memories)
    memory_results = []
    for query_entry in memory_queries:
        retrieved = query_entry.get("retrieved", [])
        for memory_item in retrieved:
            memory_results.append({
                "query": query_entry["query"],
                "result": memory_item.get("memory", ""),
                "category": memory_item.get("category", "unknown")
            })
    logger.add_metadata("memory_results", memory_results)

    # Log which agent was selected
    logger.add_metadata("selected_agent", "rca_agent")  # From orchestrator

    # Show final state
    print("="*80)
    print("FINAL STATE:")
    print("="*80)
    print(f"Service status: {final_state['services']['payment-service']['status']}")
    print(f"Response time: {final_state['metrics']['payment-service']['avg_response_time']}s")
    print(f"Error rate: {final_state['metrics']['payment-service']['error_rate']}%")
    print(f"CPU: {final_state['metrics']['payment-service']['cpu_utilization']}%")
    print(f"Problem resolved: {final_state['problem_resolved']}")
    print(f"Actions taken: {len(final_state['actions_taken'])}")
    for action in final_state['actions_taken']:
        print(f"  - {action['action']}: {action.get('service', action.get('security_group_id', 'N/A'))}")
    print()

    # Show tool call summary
    print("="*80)
    print("TOOL CALL SUMMARY:")
    print("="*80)
    tool_calls = api.get_tool_call_log()
    print(f"Total tool calls: {len(tool_calls)}")
    tool_counts = {}
    for call in tool_calls:
        tool_counts[call['tool']] = tool_counts.get(call['tool'], 0) + 1
    for tool_name, count in sorted(tool_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {tool_name}: {count}")
    print()

    # Show memory query summary
    print("="*80)
    print("MEMORY QUERY SUMMARY:")
    print("="*80)
    print(f"Total memory queries: {len(memory_queries)}")
    for i, query in enumerate(memory_queries, 1):
        retrieved_count = len(query.get('retrieved', []))
        print(f"  {i}. \"{query['query'][:60]}...\" - Retrieved: {retrieved_count}")
    print()

    # End cost tracking
    cost_tracker.end_execution()

    # Collect actual token usage from agents
    all_agents = {
        "rca_agent": rca_agent,
        "performance_agent": performance_agent,
        "security_agent": security_agent,
        "classifier_agent": classifier_agent
    }

    for agent_name, agent_instance in all_agents.items():
        if hasattr(agent_instance, 'get_usage_stats'):
            usage = agent_instance.get_usage_stats()
            if usage["total_tokens"] > 0:  # Only log if agent was actually used
                cost_tracker.log_llm_call(
                    agent_name=agent_name,
                    model="gpt-4o",
                    input_tokens=usage["prompt_tokens"],
                    output_tokens=usage["completion_tokens"],
                    latency_seconds=orchestration_time if agent_name == "rca_agent" else None
                )


    # Log cost metrics to JSON
    cost_metrics = cost_tracker.get_metrics()
    logger.add_metadata("cost_metrics", cost_metrics)

    # Print cost summary
    cost_tracker.print_summary()

    # Save log
    print("="*80)
    log_path = logger.save()
    print(f"Execution log saved to: {log_path}")
    print("="*80)
    print()

    return log_path


if __name__ == "__main__":
    main()
