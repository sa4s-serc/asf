"""
Aggregated evaluation report for Scenario 2.

Runs both the traditional default evaluator and the framework evaluator across
recent logs, then prints a side-by-side comparison using the same table
structure as Scenario 1.
"""

from __future__ import annotations

import glob
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from prettytable import PrettyTable

from default_evaluator import DefaultEvaluator
from framework_evaluator import FrameworkEvaluator
from scenario_expectations import SCENARIO_EVAL_CONFIG


def _load_logs(limit: int = 3) -> List[str]:
    log_files = sorted(glob.glob("logs/scenario-2_*.json"))
    return log_files[-limit:] if limit else log_files


def _aggregate_default_metrics(log_path: str, log_data: Dict) -> Dict[str, bool]:
    """Evaluate default metrics for a single log."""
    default_eval = DefaultEvaluator(log_path).evaluate()

    task_met = default_eval["metrics"]["task_completion"]["status"] == "SUCCESS"
    tool_superset = default_eval["metrics"]["tool_calling_accuracy"]["status"] == "SUCCESS"

    final_state = log_data.get("metadata", {}).get("final_state", {})
    required = SCENARIO_EVAL_CONFIG.required_outcomes
    outcomes_met = all(final_state.get(key) == value for key, value in required.items())

    tool_names = [call["tool"] for call in log_data.get("tool_calls", [])]
    total_required = len(SCENARIO_EVAL_CONFIG.tools.required_tools)
    matched_required = sum(1 for tool in SCENARIO_EVAL_CONFIG.tools.required_tools if tool in tool_names)
    tool_usage_ratio = (matched_required / total_required * 100) if total_required else 100.0

    return {
        "task_met": task_met,
        "tool_superset": tool_superset,
        "outcomes_met": outcomes_met,
        "tools_used": matched_required,
        "tools_expected": total_required,
        "tool_usage_ratio": tool_usage_ratio,
    }


def _extract_framework_checks(framework_result: Dict) -> Dict[str, bool]:
    return {check["id"]: check["status"] == "pass" for check in framework_result["checks"]}


def _aggregate_framework_metrics(framework_result: Dict) -> Dict[str, float]:
    checks = _extract_framework_checks(framework_result)
    memory_metrics = framework_result["metrics"].get("memory", {})
    llm_metrics = framework_result["metrics"].get("llm", {})

    aggregated = {
        "task_met": framework_result["task_completion"]["met"],
        "tool_superset": checks.get("tools.selection.required_tools", False),
        "tool_sequence": checks.get("tools.sequence.order", False),
        "expected_tool_calls": checks.get("tools.parameters.expected_calls", False),
        "policy_safety": checks.get("tools.parameters.policy_safety", False),
        "policy_query": checks.get("llm.guardrail.policy_query", False),
        "dependency_query": checks.get("llm.guardrail.dependency_query", False),
        "memory_precision": memory_metrics.get("avg_precision_percent"),
        "memory_recall": memory_metrics.get("avg_recall_percent"),
        "memory_f1": memory_metrics.get("avg_f1_percent"),
        "memory_bleu": memory_metrics.get("avg_bleu_percent"),
        "incident_logged": llm_metrics.get("incident_logged"),
    }

    tools_metrics = framework_result["metrics"].get("tools", {})
    if "tool_usage_ratio" in tools_metrics:
        ratio = tools_metrics["tool_usage_ratio"]
        aggregated["tool_usage_ratio"] = ratio * 100 if ratio is not None else None
    if "tools_used" in tools_metrics:
        aggregated["tools_used"] = tools_metrics["tools_used"]
    if "tools_expected" in tools_metrics:
        aggregated["tools_expected"] = tools_metrics["tools_expected"]
    if llm_metrics.get("permission_question") is not None:
        aggregated["permission_question"] = llm_metrics["permission_question"]

    return aggregated


def _percentage(values: List[bool]) -> float:
    clean = [value for value in values if value is not None]
    return round((sum(clean) / len(clean)) * 100, 2) if clean else 0.0


def _mean(values: List[float]) -> float:
    clean = [value for value in values if value is not None]
    return round(sum(clean) / len(clean), 2) if clean else 0.0


def aggregated_report(log_paths: List[str]) -> None:
    default_metrics: Dict[str, List] = defaultdict(list)
    framework_metrics: Dict[str, List] = defaultdict(list)
    run_tool_usage: List[Tuple[str, List[str]]] = []

    for log_path in log_paths:
        with open(log_path, "r", encoding="utf-8") as handle:
            log_data = json.load(handle)

        default_agg = _aggregate_default_metrics(log_path, log_data)
        framework_result = FrameworkEvaluator(log_path).evaluate()
        framework_agg = _aggregate_framework_metrics(framework_result)

        tool_names = [call["tool"] for call in log_data.get("tool_calls", [])]
        run_tool_usage.append((Path(log_path).name, tool_names))

        for key, value in default_agg.items():
            default_metrics[key].append(value)
        for key, value in framework_agg.items():
            framework_metrics[key].append(value)

    table = PrettyTable()
    table.field_names = ["Metric", "Default", "Framework"]
    table.align["Metric"] = "l"
    table.align["Default"] = "r"
    table.align["Framework"] = "r"

    def percentage_str(metric_list: List) -> str:
        return f"{_percentage(metric_list):.0f}%" if metric_list else "—"

    def mean_str(metric_list: List) -> str:
        return f"{_mean(metric_list):.2f}" if metric_list else "—"

    def tool_usage_str(metrics: Dict[str, List]) -> str:
        used = metrics.get("tools_used")
        expected = metrics.get("tools_expected")
        if not used or not expected:
            return "—"
        avg_used = sum(used) / len(used)
        expected_val = expected[0]
        return f"{avg_used:.2f}/{expected_val}"

    def add_row(metric_name: str, default_key: str, framework_key: str, percentage: bool = True):
        default_val = default_metrics.get(default_key)
        framework_val = framework_metrics.get(framework_key)

        if percentage:
            default_str = percentage_str(default_val)
            framework_str = percentage_str(framework_val)
        else:
            default_str = mean_str(default_val)
            framework_str = mean_str(framework_val)

        table.add_row([metric_name, default_str, framework_str])

    add_row("Task completion", "task_met", "task_met")
    table.add_row([
        "Tool usage (used/expected)",
        tool_usage_str(default_metrics),
        tool_usage_str(framework_metrics),
    ])
    add_row("Tool sequence", None, "tool_sequence")
    add_row("Expected tool calls", None, "expected_tool_calls")
    add_row("Policy guardrail query", None, "policy_query")
    add_row("Dependency guardrail query", None, "dependency_query")
    add_row("Memory precision (mean %)", None, "memory_precision", percentage=False)
    add_row("Memory recall (mean %)", None, "memory_recall", percentage=False)
    add_row("Memory F1 (mean %)", None, "memory_f1", percentage=False)
    add_row("Memory BLEU (mean %)", None, "memory_bleu", percentage=False)
    add_row("Permission question rate", None, "permission_question")

    print("=" * 90)
    print("SCENARIO 2 – Aggregated Evaluation")
    print("=" * 90)
    print(f"Logs aggregated: {len(log_paths)}")
    for path in log_paths:
        print(f"  - {Path(path).name}")
    print()
    print(table)
    print()
    expected_tools = SCENARIO_EVAL_CONFIG.tools.required_tools
    print("Expected tools:")
    for tool in expected_tools:
        print(f"  - {tool}")
    print()
    print("Tools used per run:")
    for log_name, tools in run_tool_usage:
        joined = ", ".join(tools)
        print(f"  {log_name}: {joined}")
    print("=" * 90)


def main():
    logs = _load_logs(limit=3)
    if not logs:
        print("No Scenario 2 logs found in logs/ directory")
        return
    aggregated_report(logs)


if __name__ == "__main__":
    main()
