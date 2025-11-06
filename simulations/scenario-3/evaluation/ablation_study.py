"""
Scenario 3 ablation summary – average failures per pillar.

Mirrors the Scenario 2 presentation: counts how many failing checks would be
missed if each evaluation pillar were removed, averaged across the latest logs.
"""

from __future__ import annotations

import glob
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from prettytable import PrettyTable

from framework_evaluator import FrameworkEvaluator
from scenario_expectations import ScenarioExpectations
from memory_gold_labels import calculate_retrieval_metrics


def _load_log_data(log_path: str) -> Dict[str, Any]:
    with open(log_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _to_float(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip().rstrip("%")
        try:
            return float(stripped) / (100.0 if value.strip().endswith("%") else 1.0)
        except ValueError:
            return 0.0
    return 0.0

PILLARS = ["llm", "memory", "tools", "environment"]
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
MAX_LOGS = 3


def _load_logs(limit: int = MAX_LOGS) -> List[str]:
    logs = sorted(glob.glob(str(LOG_DIR / "scenario-3_*.json")))
    return logs[-limit:] if limit else logs


def _collect_failing_checks(log_path: str) -> List[Dict[str, str]]:
    result = FrameworkEvaluator(log_path).evaluate()
    log_data = _load_log_data(log_path)
    failures: List[Dict[str, str]] = []

    pillars = result.get("pillars", {})
    log_name = Path(log_path).name

    # --- LLM Pillar ---
    llm = pillars.get("llm")
    if llm:
        instruction = llm["metrics"]["instruction_adherence"]["score"]
        if instruction < 1.0:
            failures.append({
                "pillar": "llm",
                "id": "llm.instruction_adherence",
                "description": f"{log_name}: instruction adherence {instruction:.2f} (missed guardrails)",
            })

        coord_metrics = llm["metrics"]["multi_agent_coordination"]
        coord_score = coord_metrics["score"]
        if coord_score < 1.0:
            delegations = coord_metrics.get("delegations", {})
            failures.append({
                "pillar": "llm",
                "id": "llm.multi_agent_coordination",
                "description": f"{log_name}: delegations {delegations}",
            })

        guard = llm["metrics"]["safety_alignment"].get("violations", [])
        for violation in guard:
            failures.append({
                "pillar": "llm",
                "id": "llm.guardrail",
                "description": f"{log_name}: {violation}",
            })

    # --- Memory Pillar ---
    memory = pillars.get("memory")
    memory_queries = log_data.get("metadata", {}).get("memory_queries", [])
    per_query_metrics = []
    for entry in memory_queries:
        metrics = calculate_retrieval_metrics(entry.get("query", ""), entry.get("retrieved", []))
        per_query_metrics.append((entry.get("query", ""), metrics))

    if memory:
        query_strategy = memory["metrics"]["query_strategy"]
        missed = query_strategy.get("categories_missed", [])
        for category in missed:
            failures.append({
                "pillar": "memory",
                "id": f"memory.missed.{category}",
                "description": f"{log_name}: never queried required category '{category}'",
            })

        retrieval = memory["metrics"]["retrieval_mechanisms"]
        thresholds = {
            "avg_precision_percent": 80.0,
            "avg_recall_percent": 80.0,
            "avg_f1_percent": 80.0,
            "avg_bleu_percent": 70.0,
        }
        metric_map = {
            "avg_precision_percent": ("precision", "Precision"),
            "avg_recall_percent": ("recall", "Recall"),
            "avg_f1_percent": ("f1", "F1"),
            "avg_bleu_percent": ("bleu", "BLEU"),
        }
        for key, threshold in thresholds.items():
            value = retrieval.get(key)
            if value is not None and float(value) < threshold:
                metric_key, label = metric_map[key]
                if per_query_metrics:
                    worst_query, worst_metrics = min(
                        per_query_metrics,
                        key=lambda item: item[1].get(metric_key, 0.0),
                    )
                    example = (
                        f"query '{worst_query}' → precision {worst_metrics['precision']*100:.1f}%, "
                        f"recall {worst_metrics['recall']*100:.1f}%"
                    )
                else:
                    example = "no memory queries recorded"
                failures.append({
                    "pillar": "memory",
                    "id": f"memory.{label.lower()}",
                    "description": f"{log_name}: {example}",
                })

    # --- Tools Pillar ---
    tools = pillars.get("tools")
    tool_calls = log_data.get("tool_calls", [])
    if tools:
        selection_score = tools["metrics"]["tool_selection"]["sequence_score"]
        if selection_score < 1.0:
            failures.append({
                "pillar": "tools",
                "id": "tools.sequence",
                "description": f"{log_name}: diagnostic sequence score {selection_score:.2f}",
            })

        remediation = tools["metrics"]["remediation_accuracy"]
        if not remediation.get("correct_fix_applied", False):
            failures.append({
                "pillar": "tools",
                "id": "tools.correct_fix",
                "description": f"{log_name}: did not call update_security_group",
            })
        if remediation.get("incorrect_fix_applied", False):
            wrong = next((call for call in tool_calls if call.get("tool") == "scale_service"), None)
            reason = wrong.get("parameters", {}).get("reason") if wrong else "scaled service unnecessarily"
            failures.append({
                "pillar": "tools",
                "id": "tools.incorrect_fix",
                "description": f"{log_name}: {reason}",
            })

        root_cause = tools["metrics"]["root_cause_analysis"]
        if _to_float(root_cause.get("score")) < 1.0 or not root_cause.get("identified_correctly", False):
            failures.append({
                "pillar": "tools",
                "id": "tools.root_cause",
                "description": f"{log_name}: incomplete root cause steps {root_cause.get('steps')}",
            })

        usage_summary = ScenarioExpectations.tool_usage_summary(tool_calls)
        missing_tools = usage_summary.get("missing", [])
        for tool in missing_tools:
            failures.append({
                "pillar": "tools",
                "id": f"tools.missing.{tool}",
                "description": f"{log_name}: expected tool '{tool}' never called",
            })

        extra_tools = usage_summary.get("extra", [])
        for tool in extra_tools:
            failures.append({
                "pillar": "tools",
                "id": f"tools.extra.{tool}",
                "description": f"{log_name}: unexpected tool '{tool}' was invoked",
            })

    # --- Environment Pillar ---
    environment = pillars.get("environment")
    final_state = log_data.get("final_state", {})
    if environment:
        problem = environment["metrics"]["problem_resolution"]
        if not problem.get("overall_success", False):
            failures.append({
                "pillar": "environment",
                "id": "environment.problem_resolution",
                "description": f"{log_name}: final state flags {final_state}",
            })

        state_awareness = environment["metrics"]["state_awareness"]
        if _to_float(state_awareness.get("score")) < 1.0:
            failures.append({
                "pillar": "environment",
                "id": "environment.state_awareness",
                "description": f"{log_name}: checks → metrics={state_awareness.get('checked_metrics')}, connectivity={state_awareness.get('checked_connectivity')}, changes={state_awareness.get('checked_changes')}",
            })

        if environment["metrics"]["side_effects"].get("scaled_unnecessarily", False):
            failures.append({
                "pillar": "environment",
                "id": "environment.side_effects",
                "description": f"{log_name}: scaled instances without fixing root cause",
            })

    return failures


def run_ablation_study(log_paths: List[str]) -> None:
    pillar_failure_counts: Dict[str, List[int]] = defaultdict(list)

    for log_path in log_paths:
        failures_by_pillar: Dict[str, List[Dict[str, str]]] = defaultdict(list)
        for check in _collect_failing_checks(log_path):
            pillar = check["pillar"]
            failures_by_pillar[pillar].append(check)

        all_pillars = set(PILLARS) | set(failures_by_pillar.keys())
        for pillar in all_pillars:
            count = len(failures_by_pillar.get(pillar, []))
            pillar_failure_counts[pillar].append(count)

    table = PrettyTable()
    table.field_names = ["Pillar", "Avg misses/run"]
    table.align["Pillar"] = "l"
    table.align["Avg misses/run"] = "r"

    def pillar_sort_key(name: str) -> Tuple[int, str]:
        return (PILLARS.index(name) if name in PILLARS else len(PILLARS), name)

    for pillar in sorted(pillar_failure_counts.keys(), key=pillar_sort_key):
        counts = pillar_failure_counts.get(pillar, [])
        average = sum(counts) / len(counts) if counts else 0.0
        table.add_row([pillar.upper(), f"{average:.2f}"])

    print("=" * 90)
    print("SCENARIO 3 – Pillar Ablation Summary")
    print("=" * 90)
    print(f"Logs analysed: {len(log_paths)}")
    for path in log_paths:
        print(f"  - {Path(path).name}")
    print()
    print(table)
    print("=" * 90)


def main():
    logs = _load_logs(limit=MAX_LOGS)
    if not logs:
        print(f"No Scenario 3 logs found in {LOG_DIR}")
        return
    run_ablation_study(logs)


if __name__ == "__main__":
    main()