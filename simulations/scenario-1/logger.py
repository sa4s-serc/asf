"""
Execution Logger for Scenario 1

Captures all agent interactions, tool calls, and responses for evaluation.
"""

import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path


class ExecutionLogger:
    """Logs all agent execution details for later evaluation."""

    def __init__(self, scenario_name: str = "scenario-1"):
        """Initialize logger.

        Parameters:
            - scenario_name: Name of the scenario being run
        """
        self.scenario_name = scenario_name
        self.execution_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log = {
            "scenario": scenario_name,
            "execution_id": self.execution_id,
            "timestamp": datetime.now().isoformat(),
            "task": None,
            "initial_state": {},
            "final_state": {},
            "tool_calls": [],
            "agent_response": None,
            "metadata": {}
        }

    def log_task(self, task: str):
        """Log the task given to the agent.

        Parameters:
            - task: The task description
        """
        self.log["task"] = task

    def log_initial_state(self, state: Dict[str, Any]):
        """Log the initial environment state.

        Parameters:
            - state: Initial state dictionary
        """
        self.log["initial_state"] = state

    def log_final_state(self, state: Dict[str, Any]):
        """Log the final environment state.

        Parameters:
            - state: Final state dictionary
        """
        self.log["final_state"] = state

    def log_tool_call(self, tool_name: str, parameters: Optional[Dict[str, Any]] = None,
                      response: Optional[str] = None, timestamp: Optional[str] = None):
        """Log a tool call made by the agent.

        Parameters:
            - tool_name: Name of the tool called
            - parameters: Parameters passed to the tool
            - response: Response from the tool
            - timestamp: When the call was made
        """
        tool_call = {
            "tool": tool_name,
            "parameters": parameters or {},
            "response": response,
            "timestamp": timestamp or datetime.now().isoformat()
        }
        self.log["tool_calls"].append(tool_call)

    def log_agent_response(self, response: str):
        """Log the final agent response.

        Parameters:
            - response: The agent's final output
        """
        self.log["agent_response"] = response

    def add_metadata(self, key: str, value: Any):
        """Add custom metadata to the log.

        Parameters:
            - key: Metadata key
            - value: Metadata value
        """
        self.log["metadata"][key] = value

    def get_log(self) -> Dict[str, Any]:
        """Get the complete log dictionary."""
        return self.log

    def save(self, output_dir: str = "logs") -> str:
        """Save the log to a JSON file.

        Parameters:
            - output_dir: Directory to save logs

        Returns:
            Path to the saved log file
        """
        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Generate filename
        filename = f"{self.scenario_name}_{self.execution_id}.json"
        filepath = Path(output_dir) / filename

        # Save log
        with open(filepath, 'w') as f:
            json.dump(self.log, f, indent=2)

        return str(filepath)

    def print_summary(self):
        """Print a summary of the execution."""
        print("="*70)
        print("EXECUTION SUMMARY")
        print("="*70)
        print(f"Scenario: {self.log['scenario']}")
        print(f"Execution ID: {self.log['execution_id']}")
        print(f"Task: {self.log['task']}")
        print()
        print(f"Initial State:")
        print(f"  Cost: ${self.log['initial_state'].get('total_monthly_cost', 'N/A')}")
        print(f"  Running Instances: {len(self.log['initial_state'].get('running_instances', []))}")
        print()
        print(f"Final State:")
        print(f"  Cost: ${self.log['final_state'].get('total_monthly_cost', 'N/A')}")
        print(f"  Running Instances: {len(self.log['final_state'].get('running_instances', []))}")
        print(f"  Terminated: {len(self.log['final_state'].get('terminated_instances', []))}")
        print()
        print(f"Tool Calls: {len(self.log['tool_calls'])}")
        for i, call in enumerate(self.log['tool_calls'], 1):
            print(f"  {i}. {call['tool']}")
        print("="*70)
