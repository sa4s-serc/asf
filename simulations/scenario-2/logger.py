"""
Execution logger for Scenario 2: Security Incident Response.

Captures all agent actions, tool calls, and memory queries for evaluation.
"""

import json
from datetime import datetime
from typing import Dict, Any, List


class ExecutionLogger:
    """Logs execution details for evaluation."""

    def __init__(self, scenario: str):
        self.scenario = scenario
        self.execution_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.start_time = datetime.now().isoformat()
        self.tool_calls = []
        self.reasoning_steps = []
        self.final_response = None
        self.metadata = {}

    def log_tool_call(self, tool_name: str, parameters: Dict[str, Any] = None, result: str = None, timestamp: str = None):
        """Log a tool call."""
        self.tool_calls.append({
            "tool": tool_name,
            "parameters": parameters or {},
            "result": result,
            "timestamp": timestamp or datetime.now().isoformat()
        })

    def log_reasoning(self, step: str):
        """Log agent reasoning."""
        self.reasoning_steps.append({
            "step": step,
            "timestamp": datetime.now().isoformat()
        })

    def log_final_response(self, response: str):
        """Log final agent response."""
        self.final_response = response

    def add_metadata(self, key: str, value: Any):
        """Add metadata to log."""
        self.metadata[key] = value

    def save(self, output_dir: str = "logs") -> str:
        """Save log to file."""
        import os
        os.makedirs(output_dir, exist_ok=True)

        log_data = {
            "scenario": self.scenario,
            "execution_id": self.execution_id,
            "start_time": self.start_time,
            "end_time": datetime.now().isoformat(),
            "tool_calls": self.tool_calls,
            "reasoning_steps": self.reasoning_steps,
            "final_response": self.final_response,
            "metadata": self.metadata
        }

        filename = f"{output_dir}/{self.scenario}_{self.execution_id}.json"
        with open(filename, 'w') as f:
            json.dump(log_data, f, indent=2)

        return filename
