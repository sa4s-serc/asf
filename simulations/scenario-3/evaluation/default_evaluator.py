"""
Default Evaluator - Traditional Metrics for Scenario 3

Evaluates agent performance using standard metrics:
- Task completion (problem resolved?)
- Tool calling accuracy (tools called correctly?)
- Multi-agent coordination (all agents involved?)
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
        final_state = self.log.get('final_state', {})
        problem_resolved = final_state.get('problem_resolved', False)
        response_time = final_state.get('avg_response_time', 10.0)
        error_rate = final_state.get('error_rate', 100.0)

        # Check if metrics returned to baseline
        metrics_normal = (
            response_time <= 1.6 and  # Within 10% of baseline 1.5s
            error_rate <= 1.0         # Within baseline 0.8%
        )

        success = problem_resolved and metrics_normal

        return {
            "metric": "Task Completion",
            "target": "Resolve performance degradation, return metrics to baseline",
            "achieved": f"Problem resolved: {problem_resolved}, Response time: {response_time}s, Error rate: {error_rate}%",
            "status": "SUCCESS" if success else "FAILED",
            "score": 1.0 if success else 0.0
        }

    def evaluate_tool_calling_accuracy(self) -> Dict[str, Any]:
        """Evaluate if tools were called correctly.

        Checks:
        - Were valid tools called?
        - Were correct remediation tools used?
        """
        tool_calls = self.log.get('tool_calls', [])

        if not tool_calls:
            return {
                "metric": "Tool Calling Accuracy",
                "status": "FAILED",
                "score": 0.0,
                "reason": "No tools were called"
            }

        tool_names = [call['tool'] for call in tool_calls]

        # Check if correct remediation was used
        correct_fix = "update_security_group" in tool_names
        wrong_fix = "scale_service" in tool_names

        # Score based on remediation
        if correct_fix and not wrong_fix:
            accuracy = 1.0
            status = "SUCCESS"
            reason = "Used correct remediation (update_security_group)"
        elif correct_fix and wrong_fix:
            accuracy = 0.5
            status = "PARTIAL"
            reason = "Used correct fix but also scaled unnecessarily"
        elif wrong_fix:
            accuracy = 0.0
            status = "FAILED"
            reason = "Used wrong remediation (scale_service instead of update_security_group)"
        else:
            accuracy = 0.0
            status = "FAILED"
            reason = "No remediation applied"

        return {
            "metric": "Tool Calling Accuracy",
            "total_calls": len(tool_calls),
            "correct_fix_used": correct_fix,
            "wrong_fix_avoided": not wrong_fix,
            "status": status,
            "score": accuracy,
            "reason": reason
        }

    def evaluate_multi_agent_coordination(self) -> Dict[str, Any]:
        """Evaluate if multiple agents were involved.

        Checks:
        - Was performance agent called?
        - Was security agent called?
        """
        tool_calls = self.log.get('tool_calls', [])
        tool_names = [call['tool'] for call in tool_calls]

        performance_called = "ask_performance_agent" in tool_names
        security_called = "ask_security_agent" in tool_names

        all_agents_involved = performance_called and security_called

        if all_agents_involved:
            score = 1.0
            status = "SUCCESS"
            reason = "All 3 agents (RCA, Performance, Security) were involved"
        elif performance_called or security_called:
            score = 0.5
            status = "PARTIAL"
            reason = "Only some agents were involved"
        else:
            score = 0.0
            status = "FAILED"
            reason = "No multi-agent coordination detected"

        return {
            "metric": "Multi-Agent Coordination",
            "performance_agent_called": performance_called,
            "security_agent_called": security_called,
            "all_agents_involved": all_agents_involved,
            "status": status,
            "score": score,
            "reason": reason
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
                "multi_agent_coordination": self.evaluate_multi_agent_coordination(),
                "response_quality": self.evaluate_response_quality()
            }
        }

        # Calculate overall score
        scores = [
            results['metrics']['task_completion']['score'],
            results['metrics']['tool_calling_accuracy']['score'],
            results['metrics']['multi_agent_coordination']['score'],
            results['metrics']['response_quality']['score']
        ]
        results['overall_score'] = sum(scores) / len(scores)
        results['overall_status'] = "SUCCESS" if results['overall_score'] >= 0.75 else "FAILED"

        return results

    def print_results(self):
        """Print evaluation results in a readable format."""
        results = self.evaluate()

        print("="*70)
        print("DEFAULT EVALUATOR RESULTS (Traditional Metrics)")
        print("="*70)
        print()

        for metric_name, metric_data in results['metrics'].items():
            print(f"{metric_data['metric']}")
            print(f"   Status: {metric_data['status']}")
            print(f"   Score: {metric_data['score']:.2f}")
            if 'target' in metric_data:
                print(f"   Target: {metric_data['target']}")
                print(f"   Achieved: {metric_data['achieved']}")
            if 'reason' in metric_data:
                print(f"   Reason: {metric_data['reason']}")
            print()

        print("="*70)
        print(f"Overall Score: {results['overall_score']:.2f}")
        print(f"Overall Status: {results['overall_status']}")
        print("="*70)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python default_evaluator.py <log_file_path>")
        sys.exit(1)

    log_path = sys.argv[1]
    evaluator = DefaultEvaluator(log_path)
    evaluator.print_results()
