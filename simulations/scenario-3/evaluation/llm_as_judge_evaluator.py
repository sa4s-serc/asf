"""
LLM-as-Judge Evaluator for Scenario 3

Direct OpenAI API evaluation with comprehensive cost tracking.
Evaluates multi-agent root cause analysis performance.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any
from openai import OpenAI
import os

from llm_judge_prompts import build_evaluation_prompt


class LLMAsJudgeEvaluator:
    """LLM-as-Judge evaluator with cost tracking for Scenario 3."""

    def __init__(self, log_path: str, model: str = "gpt-4o"):
        """Initialize evaluator with execution log.

        Parameters:
            log_path: Path to the execution log JSON file
            model: OpenAI model to use for evaluation (default: gpt-4o)
        """
        self.log_path = Path(log_path)
        self.log = self._load_log()
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Cost tracking
        self.metrics = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "evaluation_time_seconds": 0.0,
            "total_cost_usd": 0.0,
            "model": model,
        }

    def _load_log(self) -> Dict[str, Any]:
        """Load execution log from file."""
        with open(self.log_path, "r") as f:
            return json.load(f)

    def _calculate_cost(self, usage) -> float:
        """Calculate cost using GPT-4o pricing.

        GPT-4o pricing:
        - Input: $2.50 per 1M tokens
        - Output: $10.00 per 1M tokens
        """
        prompt_cost = (usage.prompt_tokens / 1_000_000) * 2.50
        completion_cost = (usage.completion_tokens / 1_000_000) * 10.00
        return round(prompt_cost + completion_cost, 6)

    def evaluate(self) -> Dict[str, Any]:
        """Run LLM-as-Judge evaluation with cost tracking.

        Returns:
            Dictionary containing evaluation results and cost metrics
        """
        prompt = build_evaluation_prompt(self.log)

        start_time = time.time()

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert multi-agent system evaluator specializing in CloudOps root cause analysis. Provide detailed, evidence-based evaluations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            end_time = time.time()

            # Track cost metrics
            self.metrics["prompt_tokens"] = response.usage.prompt_tokens
            self.metrics["completion_tokens"] = response.usage.completion_tokens
            self.metrics["total_tokens"] = response.usage.total_tokens
            self.metrics["evaluation_time_seconds"] = round(end_time - start_time, 2)
            self.metrics["total_cost_usd"] = self._calculate_cost(response.usage)

            evaluation = json.loads(response.choices[0].message.content)

            return {
                "evaluator": "LLM-as-Judge",
                "model": self.model,
                "scenario": self.log.get("scenario", "scenario-3"),
                "execution_id": self.log.get("execution_id", "unknown"),
                "evaluation": evaluation,
                "cost_metrics": self.metrics
            }

        except json.JSONDecodeError as e:
            end_time = time.time()
            self.metrics["evaluation_time_seconds"] = round(end_time - start_time, 2)

            return {
                "evaluator": "LLM-as-Judge",
                "model": self.model,
                "scenario": self.log.get("scenario", "scenario-3"),
                "execution_id": self.log.get("execution_id", "unknown"),
                "error": f"Failed to parse evaluation JSON: {str(e)}",
                "raw_response": response.choices[0].message.content,
                "cost_metrics": self.metrics
            }

        except Exception as e:
            end_time = time.time()
            self.metrics["evaluation_time_seconds"] = round(end_time - start_time, 2)

            return {
                "evaluator": "LLM-as-Judge",
                "model": self.model,
                "scenario": self.log.get("scenario", "scenario-3"),
                "execution_id": self.log.get("execution_id", "unknown"),
                "error": f"Evaluation failed: {str(e)}",
                "cost_metrics": self.metrics
            }

    def print_results(self):
        """Print evaluation results in a readable format."""
        results = self.evaluate()

        print("=" * 80)
        print(f"LLM-AS-JUDGE EVALUATION ({results['model']})")
        print("=" * 80)
        print(f"Scenario: {results['scenario']}")
        print(f"Execution ID: {results['execution_id']}")
        print()

        if "error" in results:
            print(f"ERROR: {results['error']}")
            if "raw_response" in results:
                print("\nRaw Response:")
                print(results['raw_response'])
            print()
            print("Cost Metrics:")
            for key, value in results['cost_metrics'].items():
                print(f"  {key}: {value}")
            print("=" * 80)
            return

        eval_data = results["evaluation"]

        # Print dimension scores
        dimensions = [
            ("problem_resolution", "Problem Resolution"),
            ("multi_agent_coordination", "Multi-Agent Coordination"),
            ("diagnostic_workflow", "Diagnostic Workflow"),
            ("memory_usage", "Memory Usage"),
            ("remediation_correctness", "Remediation Correctness")
        ]

        for key, name in dimensions:
            if key in eval_data:
                print(f"{name}")
                print(f"  Score: {eval_data[key]['score']}/100")
                print(f"  Justification: {eval_data[key]['justification']}")

                # Print additional details
                if key == "problem_resolution":
                    print(f"  Root Cause Identified: {eval_data[key].get('root_cause_identified', 'N/A')}")
                    print(f"  Correct Fix Applied: {eval_data[key].get('correct_fix_applied', 'N/A')}")
                    print(f"  Problem Resolved: {eval_data[key].get('problem_resolved', 'N/A')}")
                elif key == "multi_agent_coordination":
                    print(f"  Performance Agent Used: {eval_data[key].get('performance_agent_used', 'N/A')}")
                    print(f"  Security Agent Used: {eval_data[key].get('security_agent_used', 'N/A')}")
                    print(f"  Both Coordinated: {eval_data[key].get('both_agents_coordinated', 'N/A')}")
                elif key == "diagnostic_workflow":
                    print(f"  Phases Completed: {eval_data[key].get('phases_completed', 'N/A')}/5")
                    print(f"  Sequence Correct: {eval_data[key].get('workflow_sequence_correct', 'N/A')}")
                elif key == "memory_usage":
                    categories = eval_data[key].get('categories_queried', [])
                    print(f"  Categories Queried: {', '.join(categories) if categories else 'None'}")
                elif key == "remediation_correctness":
                    print(f"  Correct Fix Called: {eval_data[key].get('correct_fix_called', 'N/A')}")
                    print(f"  Wasteful Scaling: {eval_data[key].get('wasteful_scaling', 'N/A')}")

                print()

        # Print overall assessment
        if "overall" in eval_data:
            print("Overall Assessment")
            print(f"  Overall Score: {eval_data['overall']['score']}/100")

            critical = eval_data['overall'].get('critical_failures', [])
            if critical:
                print(f"  Critical Failures:")
                for failure in critical:
                    print(f"    - {failure}")
            else:
                print(f"  Critical Failures: None")

            strengths = eval_data['overall'].get('strengths', [])
            if strengths:
                print(f"  Strengths:")
                for strength in strengths:
                    print(f"    - {strength}")

            weaknesses = eval_data['overall'].get('weaknesses', [])
            if weaknesses:
                print(f"  Weaknesses:")
                for weakness in weaknesses:
                    print(f"    - {weakness}")
            print()

        # Print cost metrics
        print("Cost Metrics")
        print(f"  Model: {results['cost_metrics']['model']}")
        print(f"  Prompt Tokens: {results['cost_metrics']['prompt_tokens']:,}")
        print(f"  Completion Tokens: {results['cost_metrics']['completion_tokens']:,}")
        print(f"  Total Tokens: {results['cost_metrics']['total_tokens']:,}")
        print(f"  Evaluation Time: {results['cost_metrics']['evaluation_time_seconds']}s")
        print(f"  Total Cost: ${results['cost_metrics']['total_cost_usd']}")
        print("=" * 80)

    def save_results(self, output_path: str = None):
        """Save evaluation results to JSON file.

        Parameters:
            output_path: Path to save results (default: same dir as log with _llm_judge suffix)
        """
        results = self.evaluate()

        if output_path is None:
            log_name = self.log_path.stem
            output_path = self.log_path.parent / f"{log_name}_llm_judge.json"

        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

        print(f"Results saved to: {output_path}")


def main():
    """Run LLM-as-Judge evaluator on the most recent Scenario 3 log."""
    import glob

    log_files = glob.glob("logs/scenario-3_*.json")
    if not log_files:
        print("No Scenario 3 logs found in logs/ directory")
        print("Usage: python llm_as_judge_evaluator.py [log_file_path]")
        return

    import os
    latest_log = max(log_files, key=os.path.getctime)
    print(f"Evaluating: {latest_log}\n")

    evaluator = LLMAsJudgeEvaluator(latest_log)
    evaluator.print_results()
    evaluator.save_results()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        log_path = sys.argv[1]
        evaluator = LLMAsJudgeEvaluator(log_path)
        evaluator.print_results()
        evaluator.save_results()
    else:
        main()
