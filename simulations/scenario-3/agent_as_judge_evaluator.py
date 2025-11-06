"""
Agent-as-Judge Evaluator for Scenario 3: Multi-Agent Root Cause Analysis

Evaluates the three primary agents in Scenario 3 (performance diagnostics,
security configuration, and RCA orchestrator) against their agent cards.
The evaluator uses the agent cards to design capability tests, verifies
execution via the simulated environment, and reports detailed metrics,
including GPT-4o cost estimates.
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

# Ensure repository and scenario modules resolve
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCENARIO_PATH = Path(__file__).resolve().parent
if str(SCENARIO_PATH) not in sys.path:
    sys.path.insert(0, str(SCENARIO_PATH))

from moya.agents.openai_agent import OpenAIAgent, OpenAIAgentConfig
from moya.tools.tool import Tool
from moya.tools.tool_registry import ToolRegistry

from environment.performance_api import PerformanceAPI
from environment.memory_tools import AgentMemory, create_memory_tools, seed_memory
from environment.tools import (
    create_performance_tools,
    create_security_tools,
    create_rca_tools,
)
from environment.agent_delegation_tools import create_agent_delegation_tools

from agents.performance_agent import create_performance_agent
from agents.security_agent import create_security_agent
from agents.rca_agent import create_rca_agent

INPUT_COST_PER_TOKEN = 2.50 / 1_000_000
OUTPUT_COST_PER_TOKEN = 10.00 / 1_000_000


def ensure_memory_ready():
    """Initialize or reset the scenario memory for a fresh evaluation run."""
    memory_db_path = SCENARIO_PATH / "memory_db"
    if not memory_db_path.exists():
        AgentMemory.reset()
        seed_memory()
    else:
        AgentMemory.initialize()
    # Clear query log so each audit captures only its own lookups
    AgentMemory._query_log = []  # pylint: disable=protected-access


def build_performance_worker(api: PerformanceAPI) -> Tuple[OpenAIAgent, Dict[str, Any]]:
    """Instantiate the performance diagnostics agent with required tools."""
    performance_tools = create_performance_tools(api)
    memory_tools = create_memory_tools()
    for tool in memory_tools.get_tools():
        performance_tools.register_tool(tool)
    agent = create_performance_agent(performance_tools)
    return agent, {"memory": AgentMemory}


def build_security_worker(api: PerformanceAPI) -> Tuple[OpenAIAgent, Dict[str, Any]]:
    """Instantiate the security configuration agent with required tools."""
    security_tools = create_security_tools(api)
    memory_tools = create_memory_tools()
    for tool in memory_tools.get_tools():
        security_tools.register_tool(tool)
    agent = create_security_agent(security_tools)
    return agent, {"memory": AgentMemory}


def build_rca_worker(api: PerformanceAPI) -> Tuple[OpenAIAgent, Dict[str, Any]]:
    """Instantiate the RCA orchestrator along with delegated agents."""
    memory_tools = create_memory_tools()

    # Performance agent (used for delegation)
    perf_tools = create_performance_tools(api)
    for tool in memory_tools.get_tools():
        perf_tools.register_tool(tool)
    performance_agent = create_performance_agent(perf_tools)

    # Security agent (used for delegation)
    sec_tools = create_security_tools(api)
    for tool in memory_tools.get_tools():
        sec_tools.register_tool(tool)
    security_agent = create_security_agent(sec_tools)

    # RCA agent with correlation + memory + delegation tools
    rca_tools = create_rca_tools(api)
    for tool in memory_tools.get_tools():
        rca_tools.register_tool(tool)
    delegation_registry = create_agent_delegation_tools(performance_agent, security_agent, api)
    for tool in delegation_registry.get_tools():
        rca_tools.register_tool(tool)

    rca_agent = create_rca_agent(rca_tools)
    return rca_agent, {
        "memory": AgentMemory,
        "performance_agent": performance_agent,
        "security_agent": security_agent,
    }


def verify_performance_agent(check_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Verification logic for the performance diagnostics agent."""
    api: PerformanceAPI = context["api"]
    memory: AgentMemory = context["memory"]

    tool_log = api.get_tool_call_log()
    memory_queries = memory.get_query_log()

    if check_type == "metrics_gathered":
        response_calls = [
            call for call in tool_log
            if call["tool"] == "get_service_metrics"
            and call["params"].get("metric_type") == "response_time"
        ]
        error_calls = [
            call for call in tool_log
            if call["tool"] == "get_service_metrics"
            and call["params"].get("metric_type") == "error_rate"
        ]
        verified = bool(response_calls) and bool(error_calls)
        return {
            "check_type": check_type,
            "verified": verified,
            "details": f"Response metrics: {len(response_calls)}, Error metrics: {len(error_calls)}",
            "evidence": {"response_metrics": response_calls, "error_metrics": error_calls},
        }

    if check_type == "baselines_consulted":
        baseline_queries = [
            q for q in memory_queries
            if "baseline" in q.get("query", "").lower()
            or any(
                mem.get("category") == "baseline"
                for mem in q.get("retrieved", [])
            )
        ]
        verified = bool(baseline_queries)
        return {
            "check_type": check_type,
            "verified": verified,
            "details": f"Baseline-related memory queries: {len(baseline_queries)}",
            "evidence": baseline_queries[-1] if baseline_queries else [],
        }

    if check_type == "logs_reviewed":
        log_calls = [call for call in tool_log if call["tool"] == "get_application_logs"]
        verified = bool(log_calls)
        return {
            "check_type": check_type,
            "verified": verified,
            "details": f"Application log pulls: {len(log_calls)}",
            "evidence": log_calls[-1] if log_calls else [],
        }

    if check_type == "recent_changes_checked":
        change_calls = [call for call in tool_log if call["tool"] == "get_recent_changes"]
        verified = bool(change_calls)
        return {
            "check_type": check_type,
            "verified": verified,
            "details": f"Recent change lookups: {len(change_calls)}",
            "evidence": change_calls[-1] if change_calls else [],
        }

    if check_type == "avoid_premature_scaling":
        scale_calls = [call for call in tool_log if call["tool"] == "scale_service"]
        verified = len(scale_calls) == 0
        return {
            "check_type": check_type,
            "verified": verified,
            "details": f"Scale attempts detected: {len(scale_calls)}",
            "evidence": scale_calls,
        }

    return {
        "check_type": check_type,
        "verified": False,
        "details": f"Unknown verification '{check_type}'",
        "evidence": [],
    }


def verify_security_agent(check_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Verification logic for the security configuration agent."""
    api: PerformanceAPI = context["api"]
    memory: AgentMemory = context["memory"]

    tool_log = api.get_tool_call_log()
    memory_queries = memory.get_query_log()

    if check_type == "changes_reviewed":
        change_calls = [call for call in tool_log if call["tool"] == "get_recent_changes"]
        verified = bool(change_calls)
        return {
            "check_type": check_type,
            "verified": verified,
            "details": f"Recent change lookups: {len(change_calls)}",
            "evidence": change_calls[-1] if change_calls else [],
        }

    if check_type == "security_group_inspected":
        sg_calls = [
            call for call in tool_log
            if call["tool"] == "get_security_group_details"
            and call["params"].get("security_group_id") == "sg-abc123"
        ]
        verified = bool(sg_calls)
        return {
            "check_type": check_type,
            "verified": verified,
            "details": f"Security group detail calls: {len(sg_calls)}",
            "evidence": sg_calls[-1] if sg_calls else [],
        }

    if check_type == "connectivity_checked":
        connectivity_calls = [
            call for call in tool_log if call["tool"] == "check_network_connectivity"
        ]
        verified = bool(connectivity_calls)
        return {
            "check_type": check_type,
            "verified": verified,
            "details": f"Connectivity checks: {len(connectivity_calls)}",
            "evidence": connectivity_calls[-1] if connectivity_calls else [],
        }

    if check_type == "topology_consulted":
        topology_calls = [call for call in tool_log if call["tool"] == "get_network_topology"]
        memory_hits = [
            q for q in memory_queries
            if "topology" in q.get("query", "").lower()
            or any(mem.get("category") == "topology" for mem in q.get("retrieved", []))
        ]
        verified = bool(topology_calls or memory_hits)
        return {
            "check_type": check_type,
            "verified": verified,
            "details": f"Topology calls: {len(topology_calls)}, Memory queries: {len(memory_hits)}",
            "evidence": {
                "tool_call": topology_calls[-1] if topology_calls else None,
                "memory_query": memory_hits[-1] if memory_hits else None,
            },
        }

    if check_type == "remediation_performed":
        remediation_calls = [call for call in tool_log if call["tool"] == "update_security_group"]
        verified = bool(remediation_calls)
        return {
            "check_type": check_type,
            "verified": verified,
            "details": f"Security group updates: {len(remediation_calls)}",
            "evidence": remediation_calls[-1] if remediation_calls else [],
        }

    if check_type == "policies_consulted":
        policy_queries = [
            q for q in memory_queries
            if "policy" in q.get("query", "").lower()
            or any(mem.get("category") == "policy" for mem in q.get("retrieved", []))
        ]
        verified = bool(policy_queries)
        return {
            "check_type": check_type,
            "verified": verified,
            "details": f"Policy-related memory queries: {len(policy_queries)}",
            "evidence": policy_queries[-1] if policy_queries else [],
        }

    return {
        "check_type": check_type,
        "verified": False,
        "details": f"Unknown verification '{check_type}'",
        "evidence": [],
    }


def verify_rca_agent(check_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Verification logic for the RCA orchestrator agent."""
    api: PerformanceAPI = context["api"]

    tool_log = api.get_tool_call_log()

    if check_type == "delegated_to_performance":
        calls = [c for c in tool_log if c["tool"] == "ask_performance_agent"]
        return {
            "check_type": check_type,
            "verified": bool(calls),
            "details": f"ask_performance_agent calls: {len(calls)}",
            "evidence": calls,
        }

    if check_type == "delegated_to_security":
        calls = [c for c in tool_log if c["tool"] == "ask_security_agent"]
        return {
            "check_type": check_type,
            "verified": bool(calls),
            "details": f"ask_security_agent calls: {len(calls)}",
            "evidence": calls,
        }

    if check_type == "performed_correlation":
        correlation_calls = [c for c in tool_log if c["tool"] == "correlate_events"]
        return {
            "check_type": check_type,
            "verified": bool(correlation_calls),
            "details": f"correlate_events calls: {len(correlation_calls)}",
            "evidence": correlation_calls,
        }

    if check_type == "identified_root_cause":
        change_calls = [c for c in tool_log if c["tool"] == "get_recent_changes"]
        security_delegations = [c for c in tool_log if c["tool"] == "ask_security_agent"]
        verified = bool(change_calls) and bool(security_delegations)
        return {
            "check_type": check_type,
            "verified": verified,
            "details": f"get_recent_changes: {len(change_calls)}, ask_security_agent: {len(security_delegations)}",
            "evidence": {"changes": change_calls, "security_delegations": security_delegations},
        }

    if check_type == "avoided_symptom_treatment":
        scale_calls = [c for c in tool_log if c["tool"] == "scale_service"]
        return {
            "check_type": check_type,
            "verified": len(scale_calls) == 0,
            "details": f"Scale service calls detected: {len(scale_calls)}",
            "evidence": scale_calls,
        }

    if check_type == "coordinated_remediation":
        security_calls = [
            c for c in tool_log if c["tool"] == "ask_security_agent"
        ]
        remediation_calls = []
        for call in security_calls:
            task = call.get("params", {}).get("task", "").lower()
            if any(keyword in task for keyword in ["update", "fix", "remediate", "allow", "restore"]):
                remediation_calls.append(call)
        return {
            "check_type": check_type,
            "verified": bool(remediation_calls),
            "details": f"Remediation delegations: {len(remediation_calls)}",
            "evidence": remediation_calls,
        }

    return {
        "check_type": check_type,
        "verified": False,
        "details": f"Unknown verification '{check_type}'",
        "evidence": [],
    }


class SingleAgentAudit:
    """Runs an agent-as-judge audit for a single agent."""

    def __init__(
        self,
        agent_name: str,
        agent_card: str,
        build_worker: Callable[[PerformanceAPI], Tuple[OpenAIAgent, Dict[str, Any]]],
        verification_descriptions: Dict[str, str],
        verification_handler: Callable[[str, Dict[str, Any]], Dict[str, Any]],
        directive: str,
    ):
        self.agent_name = agent_name
        self.agent_card = agent_card
        self.build_worker = build_worker
        self.verification_descriptions = verification_descriptions
        self.verification_handler = verification_handler
        self.directive = directive

    def run(self) -> Dict[str, Any]:
        ensure_memory_ready()
        api = PerformanceAPI()
        context: Dict[str, Any] = {"api": api}

        worker_agent, extra_context = self.build_worker(api)
        context.update(extra_context or {})

        metrics: Dict[str, Any] = {
            "capability_tests": 0,
            "capabilities_verified": 0,
            "capabilities_failed": 0,
            "conversation_turns": 0,
            "worker_agent_calls": 0,
            "environment_tool_calls": 0,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "total_time_seconds": 0.0,
            "worker_tokens": {"prompt": 0, "completion": 0, "total": 0},
            "evaluator_tokens": {"prompt": 0, "completion": 0, "total": 0},
        }

        test_results: List[Dict[str, Any]] = []
        conversation_transcript: List[Dict[str, Any]] = []

        evaluator_agent = self._create_evaluator_agent(
            worker_agent,
            metrics,
            test_results,
            conversation_transcript,
            context,
        )

        evaluation_prompt = (
            "Begin the capability audit using the worker agent's card. "
            "For each listed capability and guardrail, instruct the worker to demonstrate it, "
            "then verify execution with the available checks. Provide a JSON assessment at the end."
        )

        start = time.time()
        final_response = evaluator_agent.handle_message(evaluation_prompt)
        metrics["end_time"] = datetime.now().isoformat()
        metrics["total_time_seconds"] = round(time.time() - start, 2)

        # Token usage statistics
        if hasattr(worker_agent, "get_usage_stats"):
            worker_usage = worker_agent.get_usage_stats()
            metrics["worker_tokens"] = {
                "prompt": worker_usage.get("prompt_tokens", 0),
                "completion": worker_usage.get("completion_tokens", 0),
                "total": worker_usage.get("total_tokens", 0),
            }
        if hasattr(evaluator_agent, "get_usage_stats"):
            eval_usage = evaluator_agent.get_usage_stats()
            metrics["evaluator_tokens"] = {
                "prompt": eval_usage.get("prompt_tokens", 0),
                "completion": eval_usage.get("completion_tokens", 0),
                "total": eval_usage.get("total_tokens", 0),
            }

        assessment = self._parse_assessment(final_response, metrics)
        metrics["cost_metrics"] = self._build_cost_metrics(metrics)

        return {
            "agent": self.agent_name,
            "assessment": assessment,
            "metrics": metrics,
            "test_results": test_results,
            "conversation_transcript": conversation_transcript,
        }

    def _create_evaluator_agent(
        self,
        worker_agent: OpenAIAgent,
        metrics: Dict[str, Any],
        test_results: List[Dict[str, Any]],
        conversation: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> OpenAIAgent:
        """Construct the capability auditor agent."""
        tool_registry = ToolRegistry()

        def test_worker_capability(instruction: str) -> str:
            metrics["worker_agent_calls"] += 1
            start_time = time.time()

            response = worker_agent.handle_message(self.directive + instruction)

            elapsed = round(time.time() - start_time, 2)
            conversation.append({
                "turn": metrics["conversation_turns"],
                "role": "evaluator_to_worker",
                "instruction": instruction,
                "response": response,
                "timestamp": datetime.now().isoformat(),
                "response_time_seconds": elapsed,
            })
            metrics["conversation_turns"] += 1
            return response

        def verify_capability_execution(check_type: str, expected: str = "") -> str:
            metrics["environment_tool_calls"] += 1
            result = self.verification_handler(check_type, context)
            result.setdefault("check_type", check_type)
            result.setdefault("details", "")
            result.setdefault("evidence", [])

            if result.get("verified"):
                metrics["capabilities_verified"] += 1
            else:
                metrics["capabilities_failed"] += 1
            metrics["capability_tests"] += 1
            test_results.append(result)

            return json.dumps(result, indent=2)

        def get_worker_agent_card() -> str:
            return self.agent_card

        tool_registry.register_tool(Tool(
            name="test_worker_capability",
            function=test_worker_capability,
            parameters={
                "instruction": {
                    "type": "string",
                    "description": "Capability demonstration request for the worker agent",
                }
            },
        ))
        tool_registry.register_tool(Tool(
            name="verify_capability_execution",
            function=verify_capability_execution,
            parameters={
                "check_type": {
                    "type": "string",
                    "description": "Verification key to validate execution",
                },
                "expected": {
                    "type": "string",
                    "description": "Optional expected value for the verification routine",
                },
            },
        ))
        tool_registry.register_tool(Tool(
            name="get_worker_agent_card",
            function=get_worker_agent_card,
            parameters={},
        ))

        verification_text = "\n".join(
            f"- {name}: {desc}" for name, desc in self.verification_descriptions.items()
        )

        system_prompt = f"""You are a capability auditor evaluating the agent '{self.agent_name}'.

Follow this process:
1. Retrieve the agent's card using get_worker_agent_card.
2. For every capability and guardrail in the card, design a concrete test.
3. Issue the test via test_worker_capability.
4. Confirm the action using verify_capability_execution.
5. After all tests, produce a JSON assessment with pass/fail counts and details.

AVAILABLE VERIFICATIONS:
{verification_text}

Report format:
{{
  "capabilities_tested": ["list"],
  "tests_passed": number,
  "tests_failed": number,
  "failures": ["capability: reason"],
  "agent_card_compliance": "COMPLIANT"|"NON-COMPLIANT",
  "overall_score": 0-100
}}"""

        config = OpenAIAgentConfig(
            agent_name=f"{self.agent_name}_auditor",
            agent_type="CapabilityAuditor",
            description=f"Evaluates {self.agent_name} against its agent card",
            system_prompt=system_prompt,
            model_name="gpt-4o",
            tool_registry=tool_registry,
            tool_choice="auto",
            is_streaming=False,
            max_iterations=20,
            api_key=os.getenv("OPENAI_API_KEY"),
        )

        return OpenAIAgent(config)

    @staticmethod
    def _parse_assessment(response: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the JSON assessment produced by the evaluator."""
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end > start:
                assessment = json.loads(response[start:end])
                metrics["capabilities_verified"] = assessment.get("tests_passed", metrics["capabilities_verified"])
                metrics["capabilities_failed"] = assessment.get("tests_failed", metrics["capabilities_failed"])
                metrics["capability_tests"] = assessment.get("tests_passed", 0) + assessment.get("tests_failed", 0)
                return assessment
        except json.JSONDecodeError:
            pass

        total = metrics["capabilities_verified"] + metrics["capabilities_failed"]
        score = int((metrics["capabilities_verified"] / total) * 100) if total else 0
        return {
            "capabilities_tested": [],
            "tests_passed": metrics["capabilities_verified"],
            "tests_failed": metrics["capabilities_failed"],
            "failures": [],
            "agent_card_compliance": "COMPLIANT" if metrics["capabilities_failed"] == 0 else "NON-COMPLIANT",
            "overall_score": score,
            "note": "Assessment generated via fallback parser",
        }

    @staticmethod
    def _build_cost_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Compute GPT-4o usage cost for worker and evaluator."""
        worker_prompt = metrics["worker_tokens"]["prompt"]
        worker_completion = metrics["worker_tokens"]["completion"]
        evaluator_prompt = metrics["evaluator_tokens"]["prompt"]
        evaluator_completion = metrics["evaluator_tokens"]["completion"]

        worker_input_cost = worker_prompt * INPUT_COST_PER_TOKEN
        worker_output_cost = worker_completion * OUTPUT_COST_PER_TOKEN
        evaluator_input_cost = evaluator_prompt * INPUT_COST_PER_TOKEN
        evaluator_output_cost = evaluator_completion * OUTPUT_COST_PER_TOKEN

        cost_table = [
            {
                "component": "Worker agent",
                "input_tokens": worker_prompt,
                "output_tokens": worker_completion,
                "input_cost_usd": round(worker_input_cost, 6),
                "output_cost_usd": round(worker_output_cost, 6),
                "total_cost_usd": round(worker_input_cost + worker_output_cost, 6),
            },
            {
                "component": "Evaluator agent",
                "input_tokens": evaluator_prompt,
                "output_tokens": evaluator_completion,
                "input_cost_usd": round(evaluator_input_cost, 6),
                "output_cost_usd": round(evaluator_output_cost, 6),
                "total_cost_usd": round(evaluator_input_cost + evaluator_output_cost, 6),
            },
            {
                "component": "Combined",
                "input_tokens": worker_prompt + evaluator_prompt,
                "output_tokens": worker_completion + evaluator_completion,
                "input_cost_usd": round(worker_input_cost + evaluator_input_cost, 6),
                "output_cost_usd": round(worker_output_cost + evaluator_output_cost, 6),
                "total_cost_usd": round(
                    worker_input_cost + worker_output_cost + evaluator_input_cost + evaluator_output_cost,
                    6,
                ),
            },
        ]

        return {
            "pricing_model": {
                "input_per_million": 2.50,
                "output_per_million": 10.00,
            },
            "cost_table": cost_table,
        }


PERFORMANCE_AGENT_CARD = """PERFORMANCE DIAGNOSTICS AGENT CARD

Agent Name: performance_agent
Role: Application performance analysis and diagnosis

Capabilities:
- Retrieve response time, error rate, CPU, memory, network, and connection metrics
- Compare current metrics against baselines from memory
- Analyze error patterns and application logs
- Identify whether symptoms indicate configuration or resource issues
- Recommend diagnostic next steps before remediation

Guardrails:
- Must check recent configuration changes before recommending scaling
- Must verify network/connectivity-related indicators before scaling
- Must analyze error types (especially DatabaseConnectionTimeout)
- Must consult performance policies/prior guidance from memory
- Scaling is a last resort after ruling out configuration issues
"""

SECURITY_AGENT_CARD = """SECURITY CONFIGURATION AGENT CARD

Agent Name: security_agent
Role: Security configuration analysis and audit

Capabilities:
- Review security group configurations in detail
- Track recent security-related configuration changes
- Assess network connectivity between tiers
- Validate security policies and network topology
- Recommend and apply targeted security group updates

Guardrails:
- Must verify impact before reverting security changes
- Must correlate security changes with operational symptoms
- Must coordinate remediation carefully for production assets
- Must document changes and rationale
"""

RCA_AGENT_CARD = """ROOT CAUSE ANALYSIS (RCA) ORCHESTRATOR AGENT CARD

Agent Name: rca_agent
Role: Multi-agent orchestration for incident investigation

Capabilities:
- Delegate performance analysis to the performance diagnostics agent
- Delegate security/configuration checks to the security agent
- Perform temporal correlation between changes and symptoms
- Identify true root causes (not just symptomatic effects)
- Avoid wasteful symptom treatment such as premature scaling
- Coordinate remediation through specialized agents
- Generate comprehensive RCA report summarizing causal chain

Guardrails:
- Must gather evidence from at least two specialized agents
- Must correlate symptom onset with change events
- Must verify root cause before recommending remediation
- Must execute fixes through the appropriate specialized agent
"""


def print_agent_summary(result: Dict[str, Any]):
    """Pretty-print the outcome for a single agent."""
    assessment = result["assessment"]
    metrics = result["metrics"]
    print("=" * 80)
    print(f"Agent Evaluation: {result['agent']}")
    print("=" * 80)
    print(f"Agent Card Compliance: {assessment.get('agent_card_compliance', 'UNKNOWN')}")
    print(f"Overall Score: {assessment.get('overall_score', 0)}/100")
    print(f"Tests Passed: {assessment.get('tests_passed', 0)}")
    print(f"Tests Failed: {assessment.get('tests_failed', 0)}")
    if assessment.get("failures"):
        print("Failures:")
        for failure in assessment["failures"]:
            print(f"  - {failure}")
    print("\nKey Metrics:")
    print(f"  Capability Tests: {metrics.get('capability_tests', 0)}")
    print(f"  Conversation Turns: {metrics.get('conversation_turns', 0)}")
    print(f"  Worker Agent Calls: {metrics.get('worker_agent_calls', 0)}")
    print(f"  Environment Verifications: {metrics.get('environment_tool_calls', 0)}")
    print(f"  Evaluation Time: {metrics.get('total_time_seconds', 0)}s")
    print("\nCost Summary (USD):")
    for row in metrics["cost_metrics"]["cost_table"]:
        print(
            f"  {row['component']}: input_tokens={row['input_tokens']}, "
            f"output_tokens={row['output_tokens']}, "
            f"input_cost={row['input_cost_usd']}, output_cost={row['output_cost_usd']}, "
            f"total={row['total_cost_usd']}"
        )
    print()


def aggregate_costs(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate token usage and costs across all agent evaluations."""
    total_worker_prompt = sum(r["metrics"]["worker_tokens"]["prompt"] for r in results)
    total_worker_completion = sum(r["metrics"]["worker_tokens"]["completion"] for r in results)
    total_evaluator_prompt = sum(r["metrics"]["evaluator_tokens"]["prompt"] for r in results)
    total_evaluator_completion = sum(r["metrics"]["evaluator_tokens"]["completion"] for r in results)

    worker_input_cost = total_worker_prompt * INPUT_COST_PER_TOKEN
    worker_output_cost = total_worker_completion * OUTPUT_COST_PER_TOKEN
    evaluator_input_cost = total_evaluator_prompt * INPUT_COST_PER_TOKEN
    evaluator_output_cost = total_evaluator_completion * OUTPUT_COST_PER_TOKEN

    return {
        "pricing_model": {
            "input_per_million": 2.50,
            "output_per_million": 10.00,
        },
        "cost_table": [
            {
                "component": "Worker agents (aggregate)",
                "input_tokens": total_worker_prompt,
                "output_tokens": total_worker_completion,
                "input_cost_usd": round(worker_input_cost, 6),
                "output_cost_usd": round(worker_output_cost, 6),
                "total_cost_usd": round(worker_input_cost + worker_output_cost, 6),
            },
            {
                "component": "Evaluator agents (aggregate)",
                "input_tokens": total_evaluator_prompt,
                "output_tokens": total_evaluator_completion,
                "input_cost_usd": round(evaluator_input_cost, 6),
                "output_cost_usd": round(evaluator_output_cost, 6),
                "total_cost_usd": round(evaluator_input_cost + evaluator_output_cost, 6),
            },
            {
                "component": "Combined",
                "input_tokens": total_worker_prompt + total_evaluator_prompt,
                "output_tokens": total_worker_completion + total_evaluator_completion,
                "input_cost_usd": round(worker_input_cost + evaluator_input_cost, 6),
                "output_cost_usd": round(worker_output_cost + evaluator_output_cost, 6),
                "total_cost_usd": round(
                    worker_input_cost + worker_output_cost + evaluator_input_cost + evaluator_output_cost,
                    6,
                ),
            },
        ],
    }


def main():
    audits = [
        SingleAgentAudit(
            agent_name="performance_agent",
            agent_card=PERFORMANCE_AGENT_CARD,
            build_worker=build_performance_worker,
            verification_descriptions={
                "metrics_gathered": "Verify response time and error metrics were collected.",
                "baselines_consulted": "Confirm performance baselines were retrieved from memory.",
                "logs_reviewed": "Ensure application logs were inspected for error patterns.",
                "recent_changes_checked": "Verify recent configuration changes were examined.",
                "avoid_premature_scaling": "Confirm scaling actions were not taken prematurely.",
            },
            verification_handler=verify_performance_agent,
            directive=(
                "IMPORTANT: You must operate on 'payment-service'. Gather concrete evidence via tool calls "
                "before responding. Consult memory for baselines and troubleshooting policies, inspect "
                "metrics and logs, check recent changes, and avoid scaling unless explicitly directed. "
                "Do not respond hypothetically—call the tools first, then summarize.\n\n"
            ),
        ),
        SingleAgentAudit(
            agent_name="security_agent",
            agent_card=SECURITY_AGENT_CARD,
            build_worker=build_security_worker,
            verification_descriptions={
                "changes_reviewed": "Check that recent security changes were examined.",
                "security_group_inspected": "Verify security group sg-abc123 was reviewed.",
                "connectivity_checked": "Ensure connectivity between app and database was tested.",
                "topology_consulted": "Confirm network topology or memory knowledge was leveraged.",
                "remediation_performed": "Verify targeted security group remediation was executed.",
                "policies_consulted": "Check that relevant security policies were retrieved from memory.",
            },
            verification_handler=verify_security_agent,
            directive=(
                "IMPORTANT: Focus on security group 'sg-abc123' and the payment-service database. "
                "Use the tools to inspect configurations, recent changes, network topology, and "
                "connectivity. Apply remediation via update_security_group when warranted. "
                "Execute the tool calls before responding.\n\n"
            ),
        ),
        SingleAgentAudit(
            agent_name="rca_agent",
            agent_card=RCA_AGENT_CARD,
            build_worker=build_rca_worker,
            verification_descriptions={
                "delegated_to_performance": "Confirm delegation to the performance agent.",
                "delegated_to_security": "Confirm delegation to the security agent.",
                "performed_correlation": "Check that temporal correlation was executed.",
                "identified_root_cause": "Ensure root cause identification steps were taken.",
                "avoided_symptom_treatment": "Confirm no premature scaling occurred.",
                "coordinated_remediation": "Verify remediation was coordinated via the proper agent.",
            },
            verification_handler=verify_rca_agent,
            directive=(
                "IMPORTANT: Coordinate the investigation using delegation tools. Request detailed "
                "analysis from the performance and security agents, correlate timing of changes vs "
                "symptoms, avoid treating symptoms directly, and coordinate remediation through the "
                "appropriate agent. Always perform the tool calls before summarizing findings.\n\n"
            ),
        ),
    ]

    results: List[Dict[str, Any]] = []
    for audit in audits:
        result = audit.run()
        print_agent_summary(result)
        results.append(result)

    aggregated_costs = aggregate_costs(results)

    final_payload = {
        "evaluator": "Agent-as-Judge (Scenario 3 Multi-Agent Auditor)",
        "scenario": "scenario-3",
        "evaluations": results,
        "aggregated_costs": aggregated_costs,
        "generated_at": datetime.now().isoformat(),
    }

    logs_dir = SCENARIO_PATH / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = logs_dir / f"scenario-3_{timestamp}_agent_judge.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_payload, f, indent=2)

    print("=" * 80)
    print("Overall Cost Summary (USD)")
    print("=" * 80)
    for row in aggregated_costs["cost_table"]:
        print(
            f"  {row['component']}: input_tokens={row['input_tokens']}, "
            f"output_tokens={row['output_tokens']}, "
            f"input_cost={row['input_cost_usd']}, output_cost={row['output_cost_usd']}, "
            f"total={row['total_cost_usd']}"
        )
    print("=" * 80)
    print(f"Results saved to: {output_path}")


if __name__ == "__main__":
    main()
