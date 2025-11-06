"""
Default Evaluator - Traditional Metrics

Evaluates agent performance using standard metrics:
- Task completion (goal achieved?)
- Tool calling accuracy (tools called correctly?)
- Response quality
"""

import json
from typing import Dict, Any


class DefaultEvaluator:
    """Traditional evaluation metrics for agent performance."""

    def __init__(self, log_path: str):
        """Initialize evaluator with execution log.

        Parameters:
            - log_path: Path to the execution log JSON file
        """
        with open(log_path, 'r') as f:
            self.log = json.load(f)

    def evaluate_task_completion(self) -> Dict[str, Any]:
        """Evaluate if the task was completed successfully.

        Returns:
            Dictionary with completion metrics
        """
        # Check if metadata exists as a key, otherwise look at root level
        metadata = self.log.get('metadata', self.log)
        target_percentage = metadata.get('target_percentage', 30)
        actual_percentage = metadata.get('savings_percentage', 0)
        target_met = metadata.get('target_met', False)

        return {
            "metric": "Task Completion",
            "target": f"{target_percentage}% cost reduction",
            "achieved": f"{actual_percentage:.1f}% cost reduction",
            "status": "SUCCESS" if target_met else "FAILED",
            "score": 1.0 if target_met else 0.0
        }

    def evaluate_tool_calling_accuracy(self) -> Dict[str, Any]:
        """Evaluate if tools were called correctly.

        Checks:
        - Were valid tools called?
        - Were parameters provided correctly?
        """
        tool_calls = self.log.get('tool_calls', [])
        metadata = self.log.get('metadata', self.log)
        available_tools = metadata.get('available_tools', [])

        if not tool_calls:
            return {
                "metric": "Tool Calling Accuracy",
                "status": "FAILED",
                "score": 0.0,
                "reason": "No tools were called"
            }

        # Check if all called tools are valid
        invalid_tools = []
        for call in tool_calls:
            if call['tool'] not in available_tools:
                invalid_tools.append(call['tool'])

        accuracy = 1.0 - (len(invalid_tools) / len(tool_calls))

        return {
            "metric": "Tool Calling Accuracy",
            "total_calls": len(tool_calls),
            "invalid_calls": len(invalid_tools),
            "accuracy": f"{accuracy * 100:.1f}%",
            "status": "SUCCESS" if accuracy == 1.0 else "PARTIAL",
            "score": accuracy
        }

    def evaluate_response_quality(self) -> Dict[str, Any]:
        """Evaluate if agent provided a response.

        Basic check: Did agent provide output?
        """
        response = self.log.get('agent_response')

        if not response or len(response.strip()) == 0:
            return {
                "metric": "Response Quality",
                "status": "FAILED",
                "score": 0.0,
                "reason": "No response provided"
            }

        return {
            "metric": "Response Quality",
            "status": "SUCCESS",
            "score": 1.0,
            "response_length": len(response)
        }

    def evaluate(self) -> Dict[str, Any]:
        """Run all evaluations and return results.

        Returns:
            Complete evaluation results
        """
        results = {
            "evaluator": "Default (Traditional Metrics)",
            "scenario": self.log['scenario'],
            "execution_id": self.log['execution_id'],
            "metrics": {
                "task_completion": self.evaluate_task_completion(),
                "tool_calling_accuracy": self.evaluate_tool_calling_accuracy(),
                "response_quality": self.evaluate_response_quality()
            }
        }

        # Calculate overall score
        scores = [
            results['metrics']['task_completion']['score'],
            results['metrics']['tool_calling_accuracy']['score'],
            results['metrics']['response_quality']['score']
        ]
        results['overall_score'] = sum(scores) / len(scores)
        results['overall_status'] = "SUCCESS" if results['overall_score'] >= 0.8 else "FAILED"

        return results

    def print_results(self):
        """Print evaluation results in a readable format."""
        results = self.evaluate()

        print("="*70)
        print("DEFAULT EVALUATOR RESULTS (Traditional Metrics)")
        print("="*70)
        print()

        for metric_name, metric_data in results['metrics'].items():
            print(f"📊 {metric_data['metric']}")
            print(f"   Status: {metric_data['status']}")
            print(f"   Score: {metric_data['score']:.2f}")
            if 'target' in metric_data:
                print(f"   Target: {metric_data['target']}")
                print(f"   Achieved: {metric_data['achieved']}")
            if 'accuracy' in metric_data:
                print(f"   Accuracy: {metric_data['accuracy']}")
            if 'reason' in metric_data:
                print(f"   Reason: {metric_data['reason']}")
            print()

        print("-"*70)
        print(f"Overall Score: {results['overall_score']:.2f}")
        print(f"Overall Status: {results['overall_status']}")
        print("="*70)


def main():
    """Run default evaluator on the most recent log."""
    import glob
    import os

    # Find most recent log
    log_files = glob.glob("logs/scenario-1_*.json")
    if not log_files:
        print("No log files found in logs/ directory")
        return

    latest_log = max(log_files, key=os.path.getctime)
    print(f"Evaluating: {latest_log}\n")

    evaluator = DefaultEvaluator(latest_log)
    evaluator.print_results()


if __name__ == "__main__":
    main()
