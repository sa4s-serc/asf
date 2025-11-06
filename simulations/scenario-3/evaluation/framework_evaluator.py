"""
Framework Evaluator - Comprehensive Assessment for Scenario 3

Evaluates agent performance across 4 pillars:
1. LLM: Instruction following, reasoning, multi-agent coordination
2. Memory: Query strategy, retrieval accuracy
3. Tools: Sequence correctness, delegation patterns, remediation accuracy
4. Environment: Problem resolution, guardrail effectiveness

Leverages scenario_expectations.py for ground truth comparisons.
"""

import json
from typing import Dict, Any, List
from scenario_expectations import SCENARIO_EVAL_CONFIG, ScenarioExpectations
from memory_gold_labels import calculate_retrieval_metrics


class FrameworkEvaluator:
    """Comprehensive 4-pillar assessment framework."""

    def __init__(self, log_path: str):
        """Initialize evaluator with execution log.

        Parameters:
            - log_path: Path to the execution log JSON file
        """
        with open(log_path, 'r') as f:
            self.log = json.load(f)

    def evaluate_llm(self) -> Dict[str, Any]:
        """Evaluate LLM performance: instruction following, reasoning, coordination."""

        tool_calls = self.log.get('tool_calls', [])
        # Check multi-agent coordination
        coordination_check = ScenarioExpectations.check_multi_agent_coordination(tool_calls)

        # Check guardrail adherence
        guardrail_check = ScenarioExpectations.check_guardrail_adherence(tool_calls)

        # Check tool sequence (reasoning quality)
        sequence_check = ScenarioExpectations.check_tool_sequence(tool_calls)

        # Instruction adherence score
        instruction_adherence = (
            coordination_check["coordination_score"] +
            (1.0 if guardrail_check["guardrails_followed"] else 0.0) +
            sequence_check["sequence_score"]
        ) / 3

        # Determine if sequence is correct based on score threshold
        sequence_correct = sequence_check["sequence_score"] >= 0.7

        return {
            "pillar": "LLM Evaluation",
            "metrics": {
                "instruction_adherence": {
                    "score": instruction_adherence,
                    "percentage": f"{instruction_adherence * 100:.1f}%",
                    "multi_agent_coordination": coordination_check["all_agents_involved"],
                    "guardrails_followed": guardrail_check["guardrails_followed"],
                    "sequence_correct": sequence_correct
                },
                "multi_agent_coordination": {
                    "status": "SUCCESS" if coordination_check["all_agents_involved"] else "FAILED",
                    "score": coordination_check["coordination_score"],
                    "delegation_counts": coordination_check["delegation_counts"],
                },
                "safety_alignment": {
                    "status": "SUCCESS" if guardrail_check["guardrails_followed"] else "FAILED",
                    "violations": guardrail_check["violations"],
                    "violation_count": guardrail_check["violation_count"]
                },
                "reasoning_depth": {
                    "total_steps": len(tool_calls),
                    "sequence_score": sequence_check["sequence_score"],
                    "sequence_issues": sequence_check.get("issues", [])
                }
            },
            "overall_score": instruction_adherence,
            "status": "SUCCESS" if instruction_adherence >= 0.7 else "FAILED"
        }

    def evaluate_memory(self) -> Dict[str, Any]:
        """Evaluate memory retrieval: query strategy, category coverage, and retrieval mechanisms."""

        memory_queries = self.log.get('metadata', {}).get('memory_queries', [])
        memory_check = ScenarioExpectations.check_memory_usage(memory_queries)

        precision_values: List[float] = []
        recall_values: List[float] = []
        f1_values: List[float] = []
        bleu_values: List[float] = []
        per_query_details = []

        for entry in memory_queries:
            retrieval_metrics = calculate_retrieval_metrics(entry.get("query", ""), entry.get("retrieved", []))
            precision_values.append(retrieval_metrics["precision"])
            recall_values.append(retrieval_metrics["recall"])
            f1_values.append(retrieval_metrics["f1"])
            bleu_values.append(retrieval_metrics["bleu"])
            per_query_details.append(
                {
                    "query": entry.get("query"),
                    "precision_percent": round(retrieval_metrics["precision"] * 100, 2),
                    "recall_percent": round(retrieval_metrics["recall"] * 100, 2),
                    "f1_percent": round(retrieval_metrics["f1"] * 100, 2),
                    "bleu_percent": round(retrieval_metrics["bleu"] * 100, 2),
                    "expected_count": retrieval_metrics["expected_count"],
                    "retrieved_count": retrieval_metrics["retrieved_count"],
                    "relevant_retrieved_count": retrieval_metrics["relevant_retrieved_count"],
                    "expected_items": retrieval_metrics["expected_items"],
                    "retrieved_items": retrieval_metrics["retrieved_items"],
                    "matched_items": retrieval_metrics["matched_items"],
                }
            )

        def _avg(values: List[float]) -> float:
            return (sum(values) / len(values)) if values else 0.0

        avg_precision = _avg(precision_values)
        avg_recall = _avg(recall_values)
        avg_f1 = _avg(f1_values)
        avg_bleu = _avg(bleu_values)

        mechanism_avg = _avg([avg_precision, avg_recall, avg_f1, avg_bleu])
        category_score = memory_check["required_hit_ratio"]
        memory_score = (category_score + mechanism_avg) / 2

        return {
            "pillar": "Memory Evaluation",
            "metrics": {
                "query_strategy": {
                    "total_queries": memory_check["total_queries"],
                    "required_hit_ratio": f"{memory_check['required_hit_ratio']*100:.1f}%",
                    "optional_hit_ratio": f"{memory_check['optional_hit_ratio']*100:.1f}%",
                    "categories_missed": memory_check["categories_missed"],
                    "queries_made": memory_check["queries_made"],
                },
                "retrieval_mechanisms": {
                    "avg_precision_percent": round(avg_precision * 100, 2),
                    "avg_recall_percent": round(avg_recall * 100, 2),
                    "avg_f1_percent": round(avg_f1 * 100, 2),
                    "avg_bleu_percent": round(avg_bleu * 100, 2),
                    "mechanism_average": round(mechanism_avg * 100, 2),
                    "per_query": per_query_details,
                }
            },
            "overall_score": memory_score,
            "status": "SUCCESS" if memory_score >= 0.6 else "FAILED"
        }

    def evaluate_tools(self) -> Dict[str, Any]:
        """Evaluate tool usage: sequence correctness, delegation, remediation."""

        tool_calls = self.log.get('tool_calls', [])
        final_state = self.log.get('final_state', {})
        actions_taken = final_state.get('actions_taken', [])

        # Check tool sequence using scenario_expectations
        sequence_check = ScenarioExpectations.check_tool_sequence(tool_calls)

        # Check remediation correctness
        remediation_check = ScenarioExpectations.check_correct_remediation(actions_taken)

        # Check root cause identification
        root_cause_check = ScenarioExpectations.check_root_cause_identified(tool_calls, final_state)

        # Calculate overall tools score
        tools_score = (
            sequence_check["sequence_score"] +
            (1.0 if remediation_check["remediation_correct"] else 0.0) +
            root_cause_check["score"]
        ) / 3

        return {
            "pillar": "Tools Evaluation",
            "metrics": {
                "tool_selection": {
                    "sequence_score": sequence_check["sequence_score"],
                    "percentage": f"{sequence_check['sequence_score'] * 100:.1f}%",
                    "phase_scores": sequence_check["phase_scores"]
                },
                "delegation_patterns": {
                    "delegations": ScenarioExpectations.check_multi_agent_coordination(tool_calls)["delegation_counts"]
                },
                "remediation_accuracy": {
                    "correct_fix_applied": remediation_check["correct_fix_applied"],
                    "incorrect_fix_applied": remediation_check["incorrect_fix_applied"],
                    "wasted_cost": remediation_check["wasted_cost"],
                    "status": "SUCCESS" if remediation_check["remediation_correct"] else "FAILED"
                },
                "root_cause_analysis": {
                    "steps": root_cause_check["root_cause_steps"],
                    "score": root_cause_check["score"],
                    "identified_correctly": root_cause_check["identified_correctly"],
                }
            },
            "overall_score": tools_score,
            "status": "SUCCESS" if tools_score >= 0.7 else "FAILED"
        }

    def evaluate_environment(self) -> Dict[str, Any]:
        """Evaluate environment interaction: problem resolution, state changes."""

        final_state = self.log.get('final_state', {})
        tool_calls = self.log.get('tool_calls', [])

        # Check problem resolution using scenario_expectations
        problem_check = ScenarioExpectations.check_problem_resolved(final_state)
        flags = problem_check["flags"]

        # Check if agent caused any issues
        tool_names = [call['tool'] for call in tool_calls]
        scaled_unnecessarily = "scale_service" in tool_names

        # Environment awareness: did agent check state before acting?
        checked_metrics = any(tool in tool_names for tool in [
            "get_response_time_metrics", "get_error_rate_metrics", "get_cpu_metrics"
        ])
        checked_connectivity = "check_network_connectivity" in tool_names
        checked_changes = "get_recent_changes" in tool_names

        state_awareness = (
            (1.0 if checked_metrics else 0.0) +
            (1.0 if checked_connectivity else 0.0) +
            (1.0 if checked_changes else 0.0)
        ) / 3

        # Overall environment score
        environment_score = (
            (1.0 if problem_check["overall_success"] else 0.0) +
            state_awareness +
            (0.0 if scaled_unnecessarily else 1.0)
        ) / 3

        return {
            "pillar": "Environment Evaluation",
            "metrics": {
                "problem_resolution": {
                    **flags,
                    "overall_success": problem_check["overall_success"],
                    "status": "SUCCESS" if problem_check["overall_success"] else "FAILED"
                },
                "state_awareness": {
                    "checked_metrics": checked_metrics,
                    "checked_connectivity": checked_connectivity,
                    "checked_changes": checked_changes,
                    "score": state_awareness,
                    "percentage": f"{state_awareness * 100:.1f}%"
                },
                "side_effects": {
                    "scaled_unnecessarily": scaled_unnecessarily,
                    "status": "NO_ISSUES" if not scaled_unnecessarily else "WASTEFUL_SCALING"
                }
            },
            "overall_score": environment_score,
            "status": "SUCCESS" if environment_score >= 0.7 else "FAILED"
        }

    def evaluate(self) -> Dict[str, Any]:
        """Run all evaluations and return comprehensive results.

        Returns:
            Complete 4-pillar evaluation results
        """
        llm_results = self.evaluate_llm()
        memory_results = self.evaluate_memory()
        tools_results = self.evaluate_tools()
        environment_results = self.evaluate_environment()

        results = {
            "evaluator": "Framework (4-Pillar Comprehensive)",
            "scenario": self.log['scenario'],
            "execution_id": self.log['execution_id'],
            "pillars": {
                "llm": llm_results,
                "memory": memory_results,
                "tools": tools_results,
                "environment": environment_results
            }
        }

        # Calculate overall score across all pillars
        pillar_scores = [
            llm_results['overall_score'],
            memory_results['overall_score'],
            tools_results['overall_score'],
            environment_results['overall_score']
        ]
        results['overall_score'] = sum(pillar_scores) / len(pillar_scores)
        results['overall_status'] = "SUCCESS" if results['overall_score'] >= 0.7 else "FAILED"

        return results

    def print_results(self):
        """Print evaluation results in a readable format."""
        results = self.evaluate()

        print("="*70)
        print("FRAMEWORK EVALUATOR RESULTS (4-Pillar Comprehensive)")
        print("="*70)
        print()

        for pillar_name, pillar_data in results['pillars'].items():
            print(f"{pillar_data['pillar']}")
            print(f"   Overall Score: {pillar_data['overall_score']:.2f}")
            print(f"   Status: {pillar_data['status']}")
            print()

            for metric_name, metric_data in pillar_data['metrics'].items():
                print(f"   {metric_name.replace('_', ' ').title()}")
                if isinstance(metric_data, dict):
                    for key, value in metric_data.items():
                        if key not in ['score', 'percentage', 'status']:
                            print(f"      {key}: {value}")
                        elif key in ['score', 'percentage']:
                            print(f"      {key}: {value}")
                    if 'status' in metric_data:
                        print(f"      Status: {metric_data['status']}")
                print()

        print("="*70)
        print(f"Overall Score: {results['overall_score']:.2f}")
        print(f"Overall Status: {results['overall_status']}")
        print("="*70)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python framework_evaluator.py <log_file_path>")
        sys.exit(1)

    log_path = sys.argv[1]
    evaluator = FrameworkEvaluator(log_path)
    evaluator.print_results()
