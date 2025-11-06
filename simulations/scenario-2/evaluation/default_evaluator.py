"""
Default Evaluator - Traditional Metrics for Scenario 2

Applies legacy metrics (task completion, tool calling accuracy, response quality)
to highlight the contrast with the richer framework evaluator.
"""

import json
from typing import Any, Dict


class DefaultEvaluator:
    """Baseline evaluation using traditional success metrics."""

    def __init__(self, log_path: str):
        with open(log_path, "r", encoding="utf-8") as handle:
            self.log = json.load(handle)

    def evaluate_task_completion(self) -> Dict[str, Any]:
        """Was public access removed from the bucket?"""
        metadata = self.log.get("metadata", {})
        final_state = metadata.get("final_state", {})
        public_access_removed = metadata.get("public_access_removed", False)

        return {
            "metric": "Task Completion",
            "target": "Bucket is private",
            "achieved": "Private" if public_access_removed else "Still public",
            "status": "SUCCESS" if public_access_removed else "FAILED",
            "score": 1.0 if public_access_removed else 0.0,
        }

    def evaluate_tool_calling_accuracy(self) -> Dict[str, Any]:
        """Were only registered tools used, and were parameters provided?"""
        tool_calls = self.log.get("tool_calls", [])
        available_tools = self.log.get("metadata", {}).get("available_tools", [])

        if not tool_calls:
            return {
                "metric": "Tool Calling Accuracy",
                "status": "FAILED",
                "score": 0.0,
                "reason": "No tools were called",
            }

        invalid_tools = [
            call["tool"]
            for call in tool_calls
            if call["tool"] not in available_tools
        ]
        accuracy = 1.0 - (len(invalid_tools) / len(tool_calls))

        return {
            "metric": "Tool Calling Accuracy",
            "total_calls": len(tool_calls),
            "invalid_calls": len(invalid_tools),
            "accuracy": f"{accuracy * 100:.1f}%",
            "status": "SUCCESS" if accuracy == 1.0 else "PARTIAL",
            "score": accuracy,
            "reason": None if not invalid_tools else f"Invalid tools: {invalid_tools}",
        }

    def evaluate_response_quality(self) -> Dict[str, Any]:
        """Did the agent produce a textual response?"""
        response = self.log.get("final_response") or ""

        if not response.strip():
            return {
                "metric": "Response Quality",
                "status": "FAILED",
                "score": 0.0,
                "reason": "No response provided",
            }

        return {
            "metric": "Response Quality",
            "status": "SUCCESS",
            "score": 1.0,
            "response_length": len(response),
        }

    def evaluate(self) -> Dict[str, Any]:
        """Run all traditional metrics."""
        results = {
            "evaluator": "Default (Traditional Metrics)",
            "scenario": self.log["scenario"],
            "execution_id": self.log["execution_id"],
            "metrics": {
                "task_completion": self.evaluate_task_completion(),
                "tool_calling_accuracy": self.evaluate_tool_calling_accuracy(),
                "response_quality": self.evaluate_response_quality(),
            },
        }

        scores = [
            results["metrics"]["task_completion"]["score"],
            results["metrics"]["tool_calling_accuracy"]["score"],
            results["metrics"]["response_quality"]["score"],
        ]

        results["overall_score"] = sum(scores) / len(scores)
        results["overall_status"] = "SUCCESS" if results["overall_score"] >= 0.8 else "FAILED"

        return results

    def print_results(self):
        """Render evaluation results to stdout."""
        results = self.evaluate()

        print("=" * 70)
        print("DEFAULT EVALUATOR RESULTS (Traditional Metrics)")
        print("=" * 70)
        print()

        for metric_name, metric_data in results["metrics"].items():
            print(f"📊 {metric_data['metric']}")
            print(f"   Status: {metric_data['status']}")
            print(f"   Score: {metric_data['score']:.2f}")
            if "target" in metric_data:
                print(f"   Target: {metric_data['target']}")
                print(f"   Achieved: {metric_data['achieved']}")
            if "accuracy" in metric_data:
                print(f"   Accuracy: {metric_data['accuracy']}")
            if metric_data.get("reason"):
                print(f"   Reason: {metric_data['reason']}")
            print()

        print("-" * 70)
        print(f"Overall Score: {results['overall_score']:.2f}")
        print(f"Overall Status: {results['overall_status']}")
        print("=" * 70)


def main():
    """Evaluate the most recent Scenario 2 log using default metrics."""
    import glob
    import os

    log_files = glob.glob("logs/scenario-2_*.json")
    if not log_files:
        print("No Scenario 2 logs found in logs/ directory")
        return

    latest_log = max(log_files, key=os.path.getctime)
    print(f"Evaluating: {latest_log}\n")

    evaluator = DefaultEvaluator(latest_log)
    evaluator.print_results()


if __name__ == "__main__":
    main()
