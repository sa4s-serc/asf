"""
Ablation Study for Scenario 1.

Aggregates failing checks across recent runs and summarises how many failures
would be missed if each evaluation pillar were removed. Provides an example
for each pillar and renders the results using PrettyTable.
"""

from __future__ import annotations

import glob
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from prettytable import PrettyTable

from framework_evaluator import FrameworkEvaluator

PILLARS = ["llm", "memory", "tools", "environment"]


def _load_logs(limit: int = 3) -> List[str]:
    logs = sorted(glob.glob("logs/scenario-1_*.json"))
    return logs[-limit:] if limit else logs


def _collect_failing_checks(log_path: str) -> List[Dict[str, str]]:
    result = FrameworkEvaluator(log_path).evaluate()
    return [check for check in result["checks"] if check["status"] == "fail"]


def run_ablation_study(log_paths: List[str]):
    pillar_failure_counts: Dict[str, List[int]] = defaultdict(list)
    pillar_examples: Dict[str, str] = {}

    for log_path in log_paths:
        failures = _collect_failing_checks(log_path)
        failures_by_pillar: Dict[str, List[Dict[str, str]]] = defaultdict(list)

        for check in failures:
            pillar = check["pillar"]
            failures_by_pillar[pillar].append(check)
            if pillar not in pillar_examples:
                example_text = check.get("evidence") or check["description"]
                pillar_examples[pillar] = f"{check['id']}: {example_text}"

        # ensure every pillar has a count entry for this run
        all_pillars = set(PILLARS) | set(failures_by_pillar.keys())
        for pillar in all_pillars:
            count = len(failures_by_pillar.get(pillar, []))
            pillar_failure_counts[pillar].append(count)

    table = PrettyTable()
    table.field_names = ["Pillar", "Avg misses/run", "Example failure"]
    table.align["Pillar"] = "l"
    table.align["Avg misses/run"] = "r"
    table.align["Example failure"] = "l"

    def pillar_sort_key(name: str) -> Tuple[int, str]:
        return (PILLARS.index(name) if name in PILLARS else len(PILLARS), name)

    for pillar in sorted(pillar_failure_counts.keys(), key=pillar_sort_key):
        counts = pillar_failure_counts.get(pillar, [])
        average = sum(counts) / len(counts) if counts else 0.0
        example = pillar_examples.get(pillar, "—")
        table.add_row([pillar.upper(), f"{average:.2f}", example])

    print("=" * 90)
    print("SCENARIO 1 – Pillar Ablation Summary")
    print("=" * 90)
    print(f"Logs analysed: {len(log_paths)}")
    for path in log_paths:
        print(f"  - {Path(path).name}")
    print()
    print(table)
    print("=" * 90)


def main():
    logs = _load_logs(limit=3)
    if not logs:
        print("No Scenario 1 logs found in logs/ directory")
        return
    run_ablation_study(logs)


if __name__ == "__main__":
    main()
