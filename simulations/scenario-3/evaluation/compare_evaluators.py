"""
Scenario 3 – Aggregate default vs framework comparison.

Scans the Scenario 3 logs directory, processes the three most recent runs,
and prints an averaged comparison table that mirrors the Scenario 2 report.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from prettytable import PrettyTable

from default_evaluator import DefaultEvaluator
from framework_evaluator import FrameworkEvaluator
from scenario_expectations import ScenarioExpectations

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
MAX_LOGS = 3


def _load_logs() -> List[Path]:
    logs = sorted(LOG_DIR.glob("scenario-3_*.json"))
    return logs[-MAX_LOGS:]


def _compute_metrics(log_path: Path) -> Dict[str, float]:
    with log_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    tool_calls = data.get("tool_calls", [])
    memory_queries = data.get("metadata", {}).get("memory_queries", [])

    default_results = DefaultEvaluator(str(log_path)).evaluate()
    framework_results = FrameworkEvaluator(str(log_path)).evaluate()

    env = framework_results["pillars"]["environment"]
    tools = framework_results["pillars"]["tools"]
    memory = framework_results["pillars"]["memory"]

    task_default = 1.0 if default_results["metrics"]["task_completion"]["status"] == "SUCCESS" else 0.0
    task_framework = 1.0 if env["metrics"]["problem_resolution"]["status"] == "SUCCESS" else 0.0

    tool_usage = ScenarioExpectations.tool_usage_summary(tool_calls)
    sequence_pct = tools["metrics"]["tool_selection"]["sequence_score"]
    expected_pct = tool_usage["coverage_ratio"]

    memory_usage = ScenarioExpectations.check_memory_usage(memory_queries)
    categories_hit = memory_usage["categories_hit"]
    policy_hit = 1.0 if categories_hit.get("policy") else 0.0
    dependency_hit = 1.0 if categories_hit.get("topology") else 0.0

    retrieval_metrics = memory["metrics"]["retrieval_mechanisms"]
    precision = retrieval_metrics["avg_precision_percent"] / 100
    recall = retrieval_metrics["avg_recall_percent"] / 100
    f1 = retrieval_metrics["avg_f1_percent"] / 100
    bleu = retrieval_metrics["avg_bleu_percent"] / 100

    return {
        "task_default": task_default,
        "task_framework": task_framework,
        "tool_used": tool_usage["used_expected_count"],
        "tool_expected": tool_usage["expected_count"],
        "tool_sequence": sequence_pct,
        "tool_expected_pct": expected_pct,
        "policy_hit": policy_hit,
        "dependency_hit": dependency_hit,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "bleu": bleu,
    }


def _average(metrics: Iterable[Dict[str, float]]) -> Dict[str, float]:
    aggregate: Dict[str, float] = {}
    count = 0
    for entry in metrics:
        count += 1
        for key, value in entry.items():
            aggregate[key] = aggregate.get(key, 0.0) + value
    for key in aggregate:
        aggregate[key] /= count
    return aggregate


def compare_evaluations() -> None:
    logs = _load_logs()
    if not logs:
        print(f"No Scenario 3 logs found in {LOG_DIR}")
        return

    metrics_per_log = [_compute_metrics(path) for path in logs]
    averaged = _average(metrics_per_log)

    tool_ratio = f"{averaged['tool_used']:.2f}/{averaged['tool_expected']:.0f}"

    table = PrettyTable()
    table.field_names = ["Metric", "Default", "Framework"]
    table.align["Metric"] = "l"
    table.align["Default"] = "r"
    table.align["Framework"] = "r"

    table.add_row([
        "Task completion",
        f"{averaged['task_default'] * 100:.0f}%",
        f"{averaged['task_framework'] * 100:.0f}%",
    ])
    table.add_row(["Tool usage (used/expected)", tool_ratio, tool_ratio])
    table.add_row(["Tool sequence", "—", f"{averaged['tool_sequence'] * 100:.0f}%"])
    table.add_row(["Expected tool calls", "—", f"{averaged['tool_expected_pct'] * 100:.0f}%"])
    table.add_row(["Policy guardrail query", "—", f"{averaged['policy_hit'] * 100:.0f}%"])
    table.add_row(["Dependency guardrail query", "—", f"{averaged['dependency_hit'] * 100:.0f}%"])
    table.add_row(["Memory precision (mean %)", "—", f"{averaged['precision'] * 100:.2f}"])
    table.add_row(["Memory recall (mean %)", "—", f"{averaged['recall'] * 100:.2f}"])
    table.add_row(["Memory F1 (mean %)", "—", f"{averaged['f1'] * 100:.2f}"])
    table.add_row(["Memory BLEU (mean %)", "—", f"{averaged['bleu'] * 100:.2f}"])
    table.add_row(["Permission question rate", "—", "—"])

    print("=" * 80)
    print("SCENARIO 3 – DEFAULT vs FRAMEWORK (Averaged)")
    print("=" * 80)
    print(f"Logs aggregated: {len(logs)}")
    for path in logs:
        print(f"  - {path.name}")
    print()
    print(table)
    print("=" * 80)


def main():
    compare_evaluations()


if __name__ == "__main__":
    main()
