"""
Scenario 3 Ground Truth Expectations

This module mirrors the structure used by the other scenarios: a dataclass-based
contract that captures LLM, tools, memory, and environment expectations, plus a
utility class with helper methods consumed by the evaluators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set


# --------------------------------------------------------------------------- #
# Dataclass definitions (aligned with Scenario 1 / 2 structure)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class LLMExpectationsConfig:
    policy_keywords: List[str]
    change_keywords: List[str]
    topology_keywords: List[str]
    required_agents: List[str]
    guardrail_phrases: Dict[str, List[str]]


@dataclass(frozen=True)
class ToolExpectationsConfig:
    diagnostic_phases: Dict[str, List[str]]
    action_tools: List[str]
    required_delegations: List[str]
    anti_pattern_tools: List[str]
    parameter_expectations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class MemoryExpectationsConfig:
    required_categories: List[str]
    optional_categories: List[str]
    single_hop_signals: Dict[str, List[str]]
    temporal_signals: List[str]
    causal_signals: List[str]
    multi_hop_required_categories: List[Set[str]]


@dataclass(frozen=True)
class EnvironmentExpectationsConfig:
    success_flags: Dict[str, Any]
    cost_guardrail_monthly: int
    avoid_actions: List[str]


@dataclass(frozen=True)
class ScenarioEvaluationConfig:
    llm: LLMExpectationsConfig
    tools: ToolExpectationsConfig
    memory: MemoryExpectationsConfig
    environment: EnvironmentExpectationsConfig


# --------------------------------------------------------------------------- #
# Scenario 3 configuration values (matching seeded memory + desired flow)
# --------------------------------------------------------------------------- #


SCENARIO_EVAL_CONFIG = ScenarioEvaluationConfig(
    llm=LLMExpectationsConfig(
        policy_keywords=["policy", "troubleshooting", "scaling"],
        change_keywords=["recent change", "security group", "modification", "timeline"],
        topology_keywords=["subnet", "topology", "cidr", "network"],
        required_agents=["performance_diagnostics_agent", "security_config_agent"],
        guardrail_phrases={
            "performance_diagnostics_agent": [
                "check for recent configuration changes",
                "verify network connectivity",
                "analyze error patterns",
            ],
            "security_config_agent": [
                "analyze cidr notation",
                "identify restrictive security group rules",
            ],
            "root_cause_analysis_agent": [
                "correlate timing of symptoms with change events",
                "gather evidence from multiple agents",
            ],
        },
    ),
    tools=ToolExpectationsConfig(
        diagnostic_phases={
            "symptom_analysis": [
                "get_response_time_metrics",
                "get_error_rate_metrics",
                "get_cpu_metrics",
                "get_memory_metrics",
            ],
            "change_analysis": [
                "get_recent_changes",
                "correlate_events",
            ],
            "network_validation": [
                "check_network_connectivity",
                "get_security_group_details",
            ],
            "evidence_collection": [
                "get_application_logs",
                "get_network_topology",
            ],
        },
        action_tools=["update_security_group"],
        required_delegations=["ask_performance_agent", "ask_security_agent"],
        anti_pattern_tools=["scale_service"],
        parameter_expectations=[
            {"tool": "update_security_group", "params": {"group_id": "sg-abc123"}},
        ],
    ),
    memory=MemoryExpectationsConfig(
        required_categories=["baseline", "change", "topology"],
        optional_categories=["policy", "incident_response", "infrastructure", "failure_pattern"],
        single_hop_signals={
            "baseline_response_time": ["1.5s", "baseline performance"],
            "security_group_id": ["sg-abc123"],
            "payment_service_subnet": ["10.0.2.0/24"],
            "database_subnet": ["10.0.3.0/24"],
        },
        temporal_signals=["2024-01-15T08:15:00Z", "08:15"],
        causal_signals=[
            "symptom vs root cause",
            "databaseconnectiontimeout",
            "retry overhead",
        ],
        multi_hop_required_categories=[
            {"change", "topology"},
        ],
    ),
    environment=EnvironmentExpectationsConfig(
        success_flags={
            "problem_resolved": True,
            "error_rate_normal": True,
            "response_time_normal": True,
            "correct_fix_applied": True,
        },
        cost_guardrail_monthly=0,
        avoid_actions=["scale_service"],
    ),
)


# --------------------------------------------------------------------------- #
# Helper utilities consumed by evaluators
# --------------------------------------------------------------------------- #


class ScenarioExpectations:
    """Utility methods that consult SCENARIO_EVAL_CONFIG to score behaviour."""

    EXPECTED_TOOL_SET: Set[str] = set(
        tool
        for tools in SCENARIO_EVAL_CONFIG.tools.diagnostic_phases.values()
        for tool in tools
    ) | set(SCENARIO_EVAL_CONFIG.tools.action_tools) | set(SCENARIO_EVAL_CONFIG.tools.required_delegations)

    @staticmethod
    def _normalise_text(item: Dict[str, Any]) -> str:
        canonical = item.get("canonical_id") or ""
        memory_text = item.get("memory") or ""
        return f"{canonical} {memory_text}".lower()

    @staticmethod
    def check_multi_agent_coordination(tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        tool_names = [call["tool"] for call in tool_calls]
        required = SCENARIO_EVAL_CONFIG.tools.required_delegations

        delegation_counts = {tool: tool_names.count(tool) for tool in required}
        all_involved = all(tool in tool_names for tool in required)

        score = sum(1 for _, count in delegation_counts.items() if count > 0) / len(required) if required else 1.0

        return {
            "all_agents_involved": all_involved,
            "delegation_counts": delegation_counts,
            "coordination_score": score,
        }

    @staticmethod
    def check_guardrail_adherence(tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect obvious guardrail violations (e.g., using anti-pattern tools)."""
        tool_names = [call["tool"] for call in tool_calls]
        violations = []

        for tool in SCENARIO_EVAL_CONFIG.tools.anti_pattern_tools:
            if tool in tool_names:
                violations.append(f"Anti-pattern tool invoked: {tool}")

        return {
            "guardrails_followed": len(violations) == 0,
            "violations": violations,
            "violation_count": len(violations),
        }

    @staticmethod
    def tool_usage_summary(tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        tool_names = [call["tool"] for call in tool_calls]
        unique = set(tool_names)
        expected = ScenarioExpectations.EXPECTED_TOOL_SET

        used_expected = expected & unique
        missing = expected - unique
        extra = unique - expected

        coverage = len(used_expected) / len(expected) if expected else 1.0

        return {
            "expected_count": len(expected),
            "used_expected_count": len(used_expected),
            "coverage_ratio": coverage,
            "missing": sorted(missing),
            "extra": sorted(extra),
        }

    @staticmethod
    def check_tool_sequence(tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        tool_names = [call["tool"] for call in tool_calls]
        phase_scores: Dict[str, Dict[str, Any]] = {}

        total_expected = sum(len(tools) for tools in SCENARIO_EVAL_CONFIG.tools.diagnostic_phases.values())
        total_hits = 0

        for phase, expected_tools in SCENARIO_EVAL_CONFIG.tools.diagnostic_phases.items():
            hits = [tool for tool in expected_tools if tool in tool_names]
            phase_scores[phase] = {
                "expected": expected_tools,
                "hit": hits,
                "score": len(hits) / len(expected_tools) if expected_tools else 1.0,
            }
            total_hits += len(hits)

        sequence_score = total_hits / total_expected if total_expected else 1.0

        remediation_tools = [call["tool"] for call in tool_calls if call["tool"] in SCENARIO_EVAL_CONFIG.tools.action_tools]
        remediation_correct = bool(remediation_tools)
        wrong_actions = [tool for tool in tool_names if tool in SCENARIO_EVAL_CONFIG.tools.anti_pattern_tools]

        return {
            "phase_scores": phase_scores,
            "sequence_score": sequence_score,
            "remediation_correct": remediation_correct,
            "wrong_actions": wrong_actions,
        }

    @staticmethod
    def check_memory_usage(memory_queries: List[Dict[str, Any]]) -> Dict[str, Any]:
        categories_hit: Dict[str, List[str]] = {}
        queries_made: List[str] = []
        for entry in memory_queries:
            queries_made.append(entry.get("query", ""))
            for item in entry.get("retrieved", []) or []:
                category = item.get("category", "unknown")
                categories_hit.setdefault(category, []).append(ScenarioExpectations._normalise_text(item))

        required = SCENARIO_EVAL_CONFIG.memory.required_categories
        optional = SCENARIO_EVAL_CONFIG.memory.optional_categories

        required_hits = [cat for cat in required if categories_hit.get(cat)]
        optional_hits = [cat for cat in optional if categories_hit.get(cat)]

        return {
            "total_queries": len(memory_queries),
            "categories_hit": categories_hit,
            "required_hit_ratio": len(required_hits) / len(required) if required else 1.0,
            "optional_hit_ratio": len(optional_hits) / len(optional) if optional else 0.0,
            "categories_missed": [cat for cat in required if cat not in required_hits],
            "queries_made": queries_made,
        }

    @staticmethod
    def evaluate_single_hop_retrieval(memory_items: List[Dict[str, Any]]) -> float:
        if not memory_items:
            return 0.0
        texts = [ScenarioExpectations._normalise_text(item) for item in memory_items]

        hits = 0
        signals = SCENARIO_EVAL_CONFIG.memory.single_hop_signals
        for keywords in signals.values():
            matched = any(any(keyword.lower() in text for keyword in keywords) for text in texts)
            if matched:
                hits += 1
        return hits / len(signals) if signals else 1.0

    @staticmethod
    def evaluate_multi_hop_integration(category_hits: Dict[str, List[str]]) -> float:
        requirements = SCENARIO_EVAL_CONFIG.memory.multi_hop_required_categories
        if not requirements:
            return 1.0

        score = 0.0
        for requirement in requirements:
            if all(category_hits.get(cat) for cat in requirement):
                score += 1.0
        return score / len(requirements)

    @staticmethod
    def evaluate_temporal_reasoning(memory_items: List[Dict[str, Any]]) -> float:
        if not memory_items:
            return 0.0
        texts = [ScenarioExpectations._normalise_text(item) for item in memory_items]
        expected = SCENARIO_EVAL_CONFIG.memory.temporal_signals
        return 1.0 if any(any(signal.lower() in text for signal in expected) for text in texts) else 0.0

    @staticmethod
    def evaluate_open_domain_integration(memory_items: List[Dict[str, Any]]) -> float:
        if not memory_items:
            return 0.0
        texts = [ScenarioExpectations._normalise_text(item) for item in memory_items]
        expected = SCENARIO_EVAL_CONFIG.memory.causal_signals
        return 1.0 if any(any(signal.lower() in text for signal in expected) for text in texts) else 0.0

    @staticmethod
    def check_root_cause_identified(tool_calls: List[Dict[str, Any]], final_state: Dict[str, Any]) -> Dict[str, Any]:
        tool_names = [call["tool"] for call in tool_calls]
        key_checks = {
            "checked_recent_changes": "get_recent_changes" in tool_names,
            "checked_network_connectivity": "check_network_connectivity" in tool_names,
            "checked_security_group": "get_security_group_details" in tool_names,
            "checked_error_logs": "get_application_logs" in tool_names,
            "correlated_events": "correlate_events" in tool_names,
        }
        score = sum(1 for hit in key_checks.values() if hit) / len(key_checks)

        identified = final_state.get("root_cause") == "security_group_blocking_database_access"

        return {
            "root_cause_steps": key_checks,
            "score": score,
            "identified_correctly": identified or score >= 0.8,
        }

    @staticmethod
    def check_correct_remediation(actions_taken: List[Dict[str, Any]]) -> Dict[str, Any]:
        correct_fix = any(action.get("action") == "update_security_group" for action in actions_taken)
        wrong_fix = any(action.get("action") in SCENARIO_EVAL_CONFIG.tools.anti_pattern_tools for action in actions_taken)
        wasted_cost = sum(action.get("estimated_cost_increase", 0) for action in actions_taken if action.get("action") == "scale_service")

        return {
            "correct_fix_applied": correct_fix,
            "incorrect_fix_applied": wrong_fix,
            "wasted_cost": wasted_cost,
            "remediation_correct": correct_fix and not wrong_fix,
        }

    @staticmethod
    def check_problem_resolved(final_state: Dict[str, Any]) -> Dict[str, Any]:
        outcome_flags = SCENARIO_EVAL_CONFIG.environment.success_flags
        results = {flag: bool(final_state.get(flag)) for flag in outcome_flags}
        overall_success = all(results.values())

        return {
            "flags": results,
            "overall_success": overall_success,
        }
