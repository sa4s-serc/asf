"""
Memory Evaluator for Scenario 3

This script focuses solely on assessing memory usage for Scenario 3 logs.
It inspects the memory queries captured in each execution, checks whether the
key seeded memories were retrieved, and provides lightweight scores for the
retrieval mechanisms (single-hop, multi-hop, temporal, causal chain).

The intent is to surface signal quality without being overly punitive—if the
agent retrieved the important facts somewhere in the run, it receives credit.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from prettytable import PrettyTable

from scenario_expectations import SCENARIO_EVAL_CONFIG
from memory_gold_labels import calculate_retrieval_metrics, get_expected_retrieval

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
MAX_LOGS = 3

CATEGORY_DESCRIPTIONS = {
    "baseline": "Performance baselines and thresholds",
    "change": "Recent configuration changes",
    "topology": "Network topology and CIDRs",
    "policy": "Troubleshooting / scaling guardrails",
    "incident_response": "Incident response workflows",
    "infrastructure": "Service-to-database dependencies",
    "failure_pattern": "Known failure patterns / symptom vs root cause",
}


def _load_log(log_path: str) -> Dict:
    with open(log_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _normalise_text(item: Dict[str, str]) -> str:
    """Combine canonical_id and memory text for keyword matching."""
    canonical = item.get("canonical_id") or ""
    memory_text = item.get("memory") or ""
    return f"{canonical} {memory_text}".lower()


def _collect_retrievals(memory_queries: List[Dict]) -> Tuple[Dict[str, List[Dict]], List[Dict]]:
    category_hits: Dict[str, List[Dict]] = defaultdict(list)
    all_items: List[Dict] = []

    for entry in memory_queries:
        for item in entry.get("retrieved", []) or []:
            category = item.get("category", "unknown")
            category_hits[category].append(item)
            all_items.append(item)

    return category_hits, all_items


def _score_single_hop(all_items: List[Dict]) -> float:
    text_blobs = [_normalise_text(item) for item in all_items]
    if not text_blobs:
        return 0.0

    signals = SCENARIO_EVAL_CONFIG.memory.single_hop_signals
    hits = 0
    for keywords in signals.values():
        match_found = any(
            any(keyword in blob for keyword in keywords)
            for blob in text_blobs
        )
        if match_found:
            hits += 1
    return hits / len(signals) if signals else 1.0


def _score_temporal(all_items: List[Dict]) -> float:
    if not all_items:
        return 0.0
    text_blobs = [_normalise_text(item) for item in all_items]
    signals = SCENARIO_EVAL_CONFIG.memory.temporal_signals
    found = any(any(keyword.lower() in blob for keyword in signals) for blob in text_blobs)
    return 1.0 if found else 0.0


def _score_causal(all_items: List[Dict]) -> float:
    if not all_items:
        return 0.0
    text_blobs = [_normalise_text(item) for item in all_items]
    signals = SCENARIO_EVAL_CONFIG.memory.causal_signals
    hits = any(any(keyword.lower() in blob for keyword in signals) for blob in text_blobs)
    return 1.0 if hits else 0.0


def _score_multi_hop(category_hits: Dict[str, List[Dict]]) -> float:
    """
    interpretation:
    - Full credit if both change and topology categories were retrieved.
    - Half credit if only change was retrieved (agent at least inspected change history).
    """
    requirements = SCENARIO_EVAL_CONFIG.memory.multi_hop_required_categories
    if not requirements:
        return 1.0

    satisfied = 0
    for requirement in requirements:
        if all(category_hits.get(category) for category in requirement):
            satisfied += 1
    return satisfied / len(requirements)


def evaluate_memory_usage(log_path: str) -> Dict[str, Any]:
    log = _load_log(log_path)
    memory_queries = log.get("metadata", {}).get("memory_queries", [])

    category_hits, all_items = _collect_retrievals(memory_queries)

    required_categories = SCENARIO_EVAL_CONFIG.memory.required_categories
    optional_categories = SCENARIO_EVAL_CONFIG.memory.optional_categories

    required_coverage = {
        category: {
            "description": CATEGORY_DESCRIPTIONS.get(category, category),
            "hit": bool(category_hits.get(category)),
            "examples": [
                (_normalise_text(item))[:120]
                for item in category_hits.get(category, [])[:2]
            ],
        }
        for category in required_categories
    }

    optional_coverage = {
        category: {
            "description": CATEGORY_DESCRIPTIONS.get(category, category),
            "hit": bool(category_hits.get(category)),
            "examples": [
                (_normalise_text(item))[:120]
                for item in category_hits.get(category, [])[:2]
            ],
        }
        for category in optional_categories
    }

    required_ratio = (
        sum(1 for entry in required_coverage.values() if entry["hit"]) / len(required_coverage)
        if required_coverage else 0.0
    )
    optional_ratio = (
        sum(1 for entry in optional_coverage.values() if entry["hit"]) / len(optional_coverage)
        if optional_coverage else 0.0
    )

    single_hop_score = _score_single_hop(all_items)
    multi_hop_score = _score_multi_hop(category_hits)
    temporal_score = _score_temporal(all_items)
    causal_score = _score_causal(all_items)

    mechanism_average = (single_hop_score + multi_hop_score + temporal_score + causal_score) / 4

    precision_values: List[float] = []
    recall_values: List[float] = []
    f1_values: List[float] = []
    bleu_values: List[float] = []
    mechanism_buckets: Dict[str, Dict[str, List[float]]] = {
        "overall": {"precision": [], "recall": [], "f1": [], "bleu": []},
        "single_hop": {"precision": [], "recall": [], "f1": [], "bleu": []},
        "multi_hop": {"precision": [], "recall": [], "f1": [], "bleu": []},
        "temporal": {"precision": [], "recall": [], "f1": [], "bleu": []},
        "causal_chain": {"precision": [], "recall": [], "f1": [], "bleu": []},
    }

    for entry in memory_queries:
        query = entry.get("query", "")
        retrieved = entry.get("retrieved", [])
        retrieval = calculate_retrieval_metrics(query, retrieved)
        precision_values.append(retrieval["precision"])
        recall_values.append(retrieval["recall"])
        f1_values.append(retrieval["f1"])
        bleu_values.append(retrieval["bleu"])
        for metric, bucket in mechanism_buckets["overall"].items():
            bucket.append(retrieval[metric])

        expected = get_expected_retrieval(query)
        expected_categories = set(expected.get("expected_categories", []))
        expected_memories = expected.get("expected_memories", [])

        mechanisms = set()
        if len(expected_categories) <= 1:
            mechanisms.add("single_hop")

        for requirement in SCENARIO_EVAL_CONFIG.memory.multi_hop_required_categories:
            if requirement.issubset(expected_categories):
                mechanisms.add("multi_hop")

        if any(signal.lower() in " ".join(expected_memories).lower() for signal in SCENARIO_EVAL_CONFIG.memory.temporal_signals):
            mechanisms.add("temporal")

        if any(signal.lower() in " ".join(expected_memories).lower() for signal in SCENARIO_EVAL_CONFIG.memory.causal_signals):
            mechanisms.add("causal_chain")

        for mechanism in mechanisms:
            for metric, bucket in mechanism_buckets[mechanism].items():
                bucket.append(retrieval[metric])

    def _avg(values: List[float]) -> float:
        return (sum(values) / len(values)) if values else 0.0

    avg_precision = _avg(precision_values)
    avg_recall = _avg(recall_values)
    avg_f1 = _avg(f1_values)
    avg_bleu = _avg(bleu_values)

    overall_score = (required_ratio + _avg([avg_precision, avg_recall, avg_f1, avg_bleu])) / 2

    mechanism_metrics = {}
    for mechanism, buckets in mechanism_buckets.items():
        if not buckets["precision"]:
            continue
        mechanism_metrics[mechanism] = {
            "count": len(buckets["precision"]),
            "precision_percent": _avg(buckets["precision"]) * 100,
            "recall_percent": _avg(buckets["recall"]) * 100,
            "f1_percent": _avg(buckets["f1"]) * 100,
            "bleu_percent": _avg(buckets["bleu"]) * 100,
        }

    return {
        "log_path": log_path,
        "required_coverage": required_coverage,
        "optional_coverage": optional_coverage,
        "mechanism_metrics": mechanism_metrics,
        "overall_score": overall_score,
        "summary": {
            "queries_made": len(memory_queries),
            "required_hit_ratio": required_ratio,
            "optional_hit_ratio": optional_ratio,
            "mechanism_average": mechanism_average,
            "avg_precision_percent": avg_precision * 100,
            "avg_recall_percent": avg_recall * 100,
            "avg_f1_percent": avg_f1 * 100,
            "avg_bleu_percent": avg_bleu * 100,
        },
    }


def evaluate_logs(log_paths: List[Path], limit: int = 3) -> Dict[str, Any]:
    selected = sorted(log_paths)[-limit:]
    runs = [evaluate_memory_usage(str(path)) for path in selected]
    if not runs:
        return {}

    count = len(runs)

    def _avg(getter):
        return sum(getter(run) for run in runs) / count

    aggregate = {
        "overall_score": _avg(lambda r: r["overall_score"]),
        "avg_required_hit_ratio": _avg(lambda r: r["summary"]["required_hit_ratio"]),
        "avg_optional_hit_ratio": _avg(lambda r: r["summary"]["optional_hit_ratio"]),
        "avg_mechanism_average": _avg(lambda r: r["summary"]["mechanism_average"]),
        "avg_precision_percent": _avg(lambda r: r["summary"]["avg_precision_percent"]),
        "avg_recall_percent": _avg(lambda r: r["summary"]["avg_recall_percent"]),
        "avg_f1_percent": _avg(lambda r: r["summary"]["avg_f1_percent"]),
        "avg_bleu_percent": _avg(lambda r: r["summary"]["avg_bleu_percent"]),
        "total_queries": sum(r["summary"]["queries_made"] for r in runs),
    }

    def _coverage_average(categories: List[str], key: str) -> Dict[str, Dict[str, Any]]:
        coverage = {}
        for category in categories:
            hits = sum(1 for run in runs if run[key].get(category, {}).get("hit"))
            coverage[category] = {
                "description": CATEGORY_DESCRIPTIONS.get(category, category),
                "hit_ratio": hits / count,
            }
        return coverage

    aggregate["required_coverage"] = _coverage_average(
        SCENARIO_EVAL_CONFIG.memory.required_categories, "required_coverage"
    )
    aggregate["optional_coverage"] = _coverage_average(
        SCENARIO_EVAL_CONFIG.memory.optional_categories, "optional_coverage"
    )

    mechanism_names = set()
    for run in runs:
        mechanism_names.update(run["mechanism_metrics"].keys())

    mechanism_aggregate: Dict[str, Dict[str, float]] = {}
    for mechanism in mechanism_names:
        precision = []
        recall = []
        f1 = []
        bleu = []
        counts = []
        for run in runs:
            metrics = run["mechanism_metrics"].get(mechanism)
            if not metrics:
                continue
            precision.append(metrics["precision_percent"])
            recall.append(metrics["recall_percent"])
            f1.append(metrics["f1_percent"])
            bleu.append(metrics["bleu_percent"])
            counts.append(metrics["count"])
        if precision:
            mechanism_aggregate[mechanism] = {
                "precision_percent": sum(precision) / len(precision),
                "recall_percent": sum(recall) / len(recall),
                "f1_percent": sum(f1) / len(f1),
                "bleu_percent": sum(bleu) / len(bleu),
                "average_queries": sum(counts) / len(counts),
            }

    aggregate["mechanism_metrics"] = mechanism_aggregate

    return {
        "logs": selected,
        "runs": runs,
        "aggregate": aggregate,
    }


def _render_tables(result: Dict[str, any]) -> None:
    print("=" * 100)
    print(f"MEMORY EVALUATION – {Path(result['log_path']).name}")
    print("=" * 100)

    summary = result["summary"]
    print(f"Total memory queries: {summary['queries_made']}")
    print(f"Required coverage hit ratio: {summary['required_hit_ratio']:.2f}")
    print(f"Optional coverage hit ratio: {summary['optional_hit_ratio']:.2f}")
    print(f"Mechanism average score: {summary['mechanism_average']:.2f}")
    print(f"Average precision: {summary['avg_precision_percent']:.2f}%")
    print(f"Average recall: {summary['avg_recall_percent']:.2f}%")
    print(f"Average F1: {summary['avg_f1_percent']:.2f}%")
    print(f"Average BLEU: {summary['avg_bleu_percent']:.2f}%")
    print(f"Overall memory score: {result['overall_score']:.2f}")
    print()

    def _build_table(title: str, coverage: Dict[str, Dict]) -> None:
        table = PrettyTable()
        table.field_names = ["Category", "Hit", "Description", "Sample memories"]
        table.align["Category"] = "l"
        table.align["Description"] = "l"
        table.align["Sample memories"] = "l"

        for category, data in coverage.items():
            sample = "; ".join(data["examples"]) if data["examples"] else "—"
            table.add_row([
                category,
                "✓" if data["hit"] else "✗",
                data["description"],
                sample,
            ])

        print(f"{title}")
        print(table)
        print()

    _build_table("Required Categories", result["required_coverage"])
    _build_table("Optional Categories (bonus credit)", result["optional_coverage"])

    mech_metrics = result["mechanism_metrics"]
    if mech_metrics:
        mech_table = PrettyTable()
        mech_table.field_names = ["Mechanism", "Queries", "Precision %", "Recall %", "F1 %", "BLEU %"]
        mech_table.align["Mechanism"] = "l"
        mech_table.align["Queries"] = "r"
        mech_table.align["Precision %"] = "r"
        mech_table.align["Recall %"] = "r"
        mech_table.align["F1 %"] = "r"
        mech_table.align["BLEU %"] = "r"

        for mechanism, metrics in mech_metrics.items():
            mech_table.add_row([
                mechanism,
                f"{metrics['count']}",
                f"{metrics['precision_percent']:.2f}",
                f"{metrics['recall_percent']:.2f}",
                f"{metrics['f1_percent']:.2f}",
                f"{metrics['bleu_percent']:.2f}",
            ])

        print("Retrieval Mechanisms (per-query metrics)")
        print(mech_table)
        print()

    metric_table = PrettyTable()
    metric_table.field_names = ["Metric", "Average %"]
    metric_table.align["Metric"] = "l"
    metric_table.align["Average %"] = "r"

    metric_table.add_row(["Precision", f"{summary['avg_precision_percent']:.2f}"])
    metric_table.add_row(["Recall", f"{summary['avg_recall_percent']:.2f}"])
    metric_table.add_row(["F1", f"{summary['avg_f1_percent']:.2f}"])
    metric_table.add_row(["BLEU-1", f"{summary['avg_bleu_percent']:.2f}"])

    print("Retrieval Quality Metrics")
    print(metric_table)
    print("=" * 100)


def _render_aggregate(aggregate_result: Dict[str, Any]) -> None:
    aggregate = aggregate_result["aggregate"]
    logs = aggregate_result["logs"]

    print("=" * 100)
    print("MEMORY EVALUATION – Aggregated Results")
    print("=" * 100)
    print(f"Logs aggregated: {len(logs)}")
    for path in logs:
        print(f"  - {path.name}")
    print()

    print(f"Total memory queries: {aggregate['total_queries']}")
    print(f"Average required coverage ratio: {aggregate['avg_required_hit_ratio']:.2f}")
    print(f"Average optional coverage ratio: {aggregate['avg_optional_hit_ratio']:.2f}")
    print(f"Average mechanism score: {aggregate['avg_mechanism_average']:.2f}")
    print(f"Average precision: {aggregate['avg_precision_percent']:.2f}%")
    print(f"Average recall: {aggregate['avg_recall_percent']:.2f}%")
    print(f"Average F1: {aggregate['avg_f1_percent']:.2f}%")
    print(f"Average BLEU: {aggregate['avg_bleu_percent']:.2f}%")
    print(f"Overall memory score: {aggregate['overall_score']:.2f}")
    print()

    def _coverage_table(title: str, coverage: Dict[str, Dict[str, Any]]) -> None:
        table = PrettyTable()
        table.field_names = ["Category", "Hit %", "Description"]
        table.align["Category"] = "l"
        table.align["Hit %"] = "r"
        table.align["Description"] = "l"

        for category, data in coverage.items():
            table.add_row([
                category,
                f"{data['hit_ratio'] * 100:.1f}",
                data["description"],
            ])
        print(title)
        print(table)
        print()

    _coverage_table("Required Categories (average hit %)", aggregate["required_coverage"])
    _coverage_table("Optional Categories (average hit %)", aggregate["optional_coverage"])

    mech_metrics = aggregate.get("mechanism_metrics", {})
    if mech_metrics:
        mech_table = PrettyTable()
        mech_table.field_names = ["Mechanism", "Avg queries", "Precision %", "Recall %", "F1 %", "BLEU %"]
        mech_table.align["Mechanism"] = "l"
        mech_table.align["Avg queries"] = "r"
        mech_table.align["Precision %"] = "r"
        mech_table.align["Recall %"] = "r"
        mech_table.align["F1 %"] = "r"
        mech_table.align["BLEU %"] = "r"

        for mechanism, metrics in mech_metrics.items():
            mech_table.add_row([
                mechanism,
                f"{metrics['average_queries']:.2f}",
                f"{metrics['precision_percent']:.2f}",
                f"{metrics['recall_percent']:.2f}",
                f"{metrics['f1_percent']:.2f}",
                f"{metrics['bleu_percent']:.2f}",
            ])

        print("Per-mechanism Averages")
        print(mech_table)
        print()

        expected_reference = {
            "single_hop": list(SCENARIO_EVAL_CONFIG.memory.single_hop_signals.keys()),
            "multi_hop": [
                ", ".join(sorted(req)) for req in SCENARIO_EVAL_CONFIG.memory.multi_hop_required_categories
            ],
            "temporal": SCENARIO_EVAL_CONFIG.memory.temporal_signals,
            "causal_chain": SCENARIO_EVAL_CONFIG.memory.causal_signals,
        }

        print("Reference signals seeded for each mechanism:")
        for mechanism, signals in expected_reference.items():
            items = signals if isinstance(signals, list) else [signals]
            print(f"  - {mechanism}: {', '.join(str(item) for item in items)}")
        print()
    print("=" * 100)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate memory usage for Scenario 3 logs.")
    parser.add_argument(
        "log_path",
        nargs="?",
        help="Path to a specific Scenario 3 log. If omitted, evaluates the most recent log.",
    )
    args = parser.parse_args()

    if args.log_path:
        log_path = Path(args.log_path)
        if not log_path.exists():
            print(f"Log file not found: {log_path}")
            return
        result = evaluate_memory_usage(str(log_path))
        _render_tables(result)
    else:
        if not LOG_DIR.exists():
            print(f"No Scenario 3 logs directory found at {LOG_DIR}")
            return
        log_paths = sorted(LOG_DIR.glob("scenario-3_*.json"))
        if not log_paths:
            print("No Scenario 3 logs found in logs/ directory")
            return
        aggregate_result = evaluate_logs(log_paths)
        _render_aggregate(aggregate_result)
        for run in aggregate_result["runs"]:
            _render_tables(run)


if __name__ == "__main__":
    main()
CATEGORY_DESCRIPTIONS = {
    "baseline": "Performance baseline / thresholds",
    "change": "Recent configuration changes",
    "topology": "Network topology / subnet context",
    "policy": "Troubleshooting / scaling guardrails",
    "incident_response": "Incident workflows / temporal guidance",
    "infrastructure": "Service-to-database dependency details",
    "failure_pattern": "Known symptom vs root-cause patterns",
}
