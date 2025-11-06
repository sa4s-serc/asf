"""
Agent-as-Judge Evaluator for Scenario 3: Multi-Agent Root Cause Analysis

Capability auditor that tests if the RCA orchestrator agent's actual capabilities
match its agent card. Tests multi-agent coordination and delegation abilities.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Add paths for imports
scenario_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
simulations_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, simulations_path)  # For moya imports
sys.path.insert(0, scenario_path)  # For scenario imports (environment, agents, etc.)

from moya.agents.openai_agent import OpenAIAgent, OpenAIAgentConfig
from moya.tools.tool_registry import ToolRegistry
from moya.tools.tool import Tool
from environment import PerformanceAPI, create_performance_tools, create_security_tools, create_rca_tools
from environment.memory_tools import create_memory_tools, AgentMemory, seed_memory
from environment.agent_delegation_tools import create_agent_delegation_tools
from agents import create_performance_agent, create_security_agent, create_rca_agent


class AgentAsJudgeEvaluator:
    """
    Agent-as-Judge evaluator for multi-agent RCA.

    Tests if RCA agent can demonstrate capabilities claimed in its agent card:
    - Delegate performance analysis to performance agent
    - Delegate security checks to security agent
    - Perform temporal correlation analysis
    - Identify root causes (not just symptoms)
    - Coordinate remediation through specialized agents
    - Generate comprehensive RCA reports
    """

    def __init__(self, scenario_path: str = None):
        self.scenario_path = Path(scenario_path or "simulations/scenario-3")

        # Metrics
        self.metrics = {
            "capability_tests": 0,
            "capabilities_verified": 0,
            "capabilities_failed": 0,
            "conversation_turns": 0,
            "worker_agent_calls": 0,
            "environment_tool_calls": 0,
            "start_time": None,
            "end_time": None,
            "total_time_seconds": 0
        }

        # Test results storage
        self.test_results = []
        self.conversation_transcript = []

        # Setup environment and agents
        self._setup_environment()
        self.worker_agent = self._create_worker_agent()
        self.evaluator_agent = self._create_evaluator_agent()

    def _setup_environment(self):
        """Setup PerformanceAPI and memory (reuse existing if available)."""
        memory_db_path = self.scenario_path / "memory_db"

        if not memory_db_path.exists():
            print("Memory not found, seeding for first time...")
            AgentMemory.reset()
            AgentMemory.initialize()
            seed_memory()
            print("Memory seeded successfully")
        else:
            print("Using existing memory database (skipping seed for speed)")
            AgentMemory.initialize()

        # Initialize performance API
        self.api = PerformanceAPI()
        self.initial_state = self.api.get_current_state()

    def _create_worker_agent(self) -> OpenAIAgent:
        """Create the RCA worker agent to be tested (with full delegation capabilities)."""

        # Create specialized agents first
        memory_tools = create_memory_tools()

        # Performance agent
        performance_tools = create_performance_tools(self.api)
        for tool in memory_tools.get_tools():
            performance_tools.register_tool(tool)
        self.performance_agent = create_performance_agent(performance_tools)

        # Security agent
        security_tools = create_security_tools(self.api)
        for tool in memory_tools.get_tools():
            security_tools.register_tool(tool)
        self.security_agent = create_security_agent(security_tools)

        # RCA agent with delegation tools
        rca_tools = create_rca_tools(self.api)
        for tool in memory_tools.get_tools():
            rca_tools.register_tool(tool)

        # Add agent delegation tools
        agent_delegation_tools = create_agent_delegation_tools(
            performance_agent=self.performance_agent,
            security_agent=self.security_agent,
            api=self.api
        )
        for tool in agent_delegation_tools.get_tools():
            rca_tools.register_tool(tool)

        rca_agent = create_rca_agent(rca_tools)
        return rca_agent

    def _create_evaluator_agent(self) -> OpenAIAgent:
        """Create the evaluator agent that tests worker capabilities."""

        # Create tools for evaluator to interact with worker and environment
        tool_registry = ToolRegistry()

        # Tool 1: Test worker capability
        def test_worker_capability(instruction: str) -> str:
            """Ask worker agent to demonstrate a specific capability.

            Parameters:
            - instruction: What to ask the worker agent to demonstrate
            """
            self.metrics["worker_agent_calls"] += 1
            start_time = time.time()

            response = self.worker_agent.handle_message(instruction)

            elapsed = time.time() - start_time
            self.conversation_transcript.append({
                "turn": self.metrics["conversation_turns"],
                "role": "evaluator_to_worker",
                "instruction": instruction,
                "response": response,
                "timestamp": datetime.now().isoformat(),
                "response_time_seconds": round(elapsed, 2)
            })
            self.metrics["conversation_turns"] += 1

            return response

        # Tool 2: Verify capability execution
        def verify_capability_execution(check_type: str, expected: str) -> str:
            """Verify if worker actually executed the capability by checking environment.

            Parameters:
            - check_type: Type of verification (delegated_to_performance, delegated_to_security, performed_correlation, identified_root_cause, avoided_symptom_treatment, coordinated_remediation)
            - expected: Expected result (JSON string for complex checks)
            """
            self.metrics["environment_tool_calls"] += 1
            result = self._verify_environment_state(check_type, expected)
            return json.dumps(result, indent=2)

        # Tool 3: Get agent card
        def get_worker_agent_card() -> str:
            """Get the worker agent's card showing its claimed capabilities and guardrails."""
            return self._get_agent_card()

        # Register tools
        tool_registry.register_tool(Tool(name="test_worker_capability", function=test_worker_capability))
        tool_registry.register_tool(Tool(name="verify_capability_execution", function=verify_capability_execution))
        tool_registry.register_tool(Tool(name="get_worker_agent_card", function=get_worker_agent_card))

        system_prompt = """You are a capability auditor evaluating a multi-agent RCA orchestrator.

Your task: Test if the RCA agent's ACTUAL capabilities match its AGENT CARD.

PROCESS:
1. Get the worker agent's card (use get_worker_agent_card)
2. For EACH capability/guardrail in the card, design a test:
   - Ask worker to demonstrate the capability (use test_worker_capability)
   - Verify it executed correctly (use verify_capability_execution)
3. Track results: which capabilities work, which don't

AVAILABLE VERIFICATIONS (check_type parameter):
- delegated_to_performance: Check if RCA agent delegated to performance agent
- delegated_to_security: Check if RCA agent delegated to security agent
- performed_correlation: Check if RCA agent performed temporal correlation
- identified_root_cause: Check if RCA identified root cause (not just symptoms)
- avoided_symptom_treatment: Check if RCA avoided wasteful scaling (symptom treatment)
- coordinated_remediation: Check if RCA coordinated remediation through security agent

TESTING GUIDELINES:
- Test each capability independently
- Ask worker to demonstrate specific actions (e.g., "Investigate performance degradation for payment-service")
- Don't ask about past execution - test current capabilities
- Verify using environment inspection, not worker's response
- Record pass/fail for each capability

MULTI-AGENT FOCUS:
- RCA agent should DELEGATE to specialized agents (not do everything itself)
- Performance analysis should go to performance agent
- Security checks should go to security agent
- RCA should synthesize findings and coordinate

When done testing, provide assessment in JSON format:
{
  "capabilities_tested": [list of capabilities tested],
  "tests_passed": number,
  "tests_failed": number,
  "failures": [list of failed capabilities with reasons],
  "agent_card_compliance": "COMPLIANT" or "NON-COMPLIANT",
  "overall_score": 0-100
}"""

        config = OpenAIAgentConfig(
            agent_name="evaluator_agent",
            agent_type="CapabilityAuditor",
            description="Tests RCA agent capabilities against its agent card",
            system_prompt=system_prompt,
            model_name="gpt-4o",
            tool_registry=tool_registry,
            tool_choice="auto",
            is_streaming=False,
            max_iterations=20,
            api_key=os.getenv("OPENAI_API_KEY")
        )

        return OpenAIAgent(config)

    def _get_agent_card(self) -> str:
        """Get the worker agent's card with claimed capabilities."""
        card = """
ROOT CAUSE ANALYSIS (RCA) ORCHESTRATOR AGENT CARD

Agent Name: rca_agent
Agent Type: ToolAgent
Description: RCA orchestrator for coordinating multi-agent root cause investigation

CAPABILITIES:
1. Delegate Performance Analysis
   - Can delegate performance metric analysis to performance agent
   - Uses ask_performance_agent tool
   - Does NOT analyze metrics directly

2. Delegate Security/Configuration Checks
   - Can delegate security group checks to security agent
   - Uses ask_security_agent tool
   - Does NOT access security tools directly

3. Perform Temporal Correlation Analysis
   - Can correlate timing between events (change vs symptom onset)
   - Uses correlate_events tool
   - Identifies causal relationships based on timing

4. Identify Root Causes (Not Just Symptoms)
   - Traces causal chains: root cause → effects → symptoms
   - Distinguishes between symptoms and underlying causes
   - Example: Identifies "security group misconfiguration" as root cause (not "high CPU" symptom)

5. Avoid Symptom Treatment
   - DOES NOT blindly scale up resources
   - Identifies when scaling would be wasteful
   - Focuses on fixing root causes

6. Coordinate Remediation Through Specialized Agents
   - Delegates remediation actions to appropriate agents
   - For security fixes: uses ask_security_agent
   - For performance adjustments: uses ask_performance_agent

7. Generate Comprehensive RCA Reports
   - Synthesizes findings from multiple agents
   - Shows causal chains
   - Documents remediation actions

WORKFLOW (Expected Order):
1. Delegate performance analysis to performance agent
2. Check recent infrastructure changes
3. Perform temporal correlation (change time vs symptom onset)
4. Delegate security/config validation to security agent
5. Synthesize findings to identify root cause
6. Coordinate remediation through appropriate agent
7. Generate comprehensive RCA report

GUARDRAILS:
- MUST delegate performance analysis (not do it directly)
- MUST delegate security checks (not do it directly)
- MUST perform temporal correlation for causal analysis
- MUST identify root cause (not just symptoms)
- MUST NOT scale up as first response (wasteful symptom treatment)
- MUST coordinate remediation through specialized agents

EXAMPLE MULTI-AGENT COORDINATION:
- User: "payment-service is slow with DatabaseConnectionTimeout errors"
- RCA: ask_performance_agent("Analyze payment-service metrics and logs")
- Performance Agent: Returns detailed metrics and error patterns
- RCA: get_recent_changes() → finds sg-abc123 modified at 08:15
- RCA: correlate_events(change_time, symptom_time) → 5min gap = HIGH correlation
- RCA: ask_security_agent("Check sg-abc123 config and verify connectivity")
- Security Agent: Returns "BLOCKED - sg only allows 10.0.1.0/24"
- RCA: Identifies root cause = security group misconfiguration
- RCA: ask_security_agent("Update sg-abc123 to allow 10.0.2.0/24")
- Security Agent: Executes fix
- RCA: Generates comprehensive report with causal chain
"""
        return card

    def _verify_environment_state(self, check_type: str, expected: Any) -> Dict[str, Any]:
        """Verify environment state to check if capability was executed."""

        tool_log = self.api.get_tool_call_log()

        if check_type == "delegated_to_performance":
            # Check if RCA agent called ask_performance_agent
            delegation_calls = [c for c in tool_log if c["tool"] == "ask_performance_agent"]
            verified = len(delegation_calls) > 0
            return {
                "check_type": check_type,
                "verified": verified,
                "details": f"Found {len(delegation_calls)} ask_performance_agent calls",
                "evidence": delegation_calls
            }

        elif check_type == "delegated_to_security":
            # Check if RCA agent called ask_security_agent
            delegation_calls = [c for c in tool_log if c["tool"] == "ask_security_agent"]
            verified = len(delegation_calls) > 0
            return {
                "check_type": check_type,
                "verified": verified,
                "details": f"Found {len(delegation_calls)} ask_security_agent calls",
                "evidence": delegation_calls
            }

        elif check_type == "performed_correlation":
            # Check if RCA agent called correlate_events
            correlation_calls = [c for c in tool_log if c["tool"] == "correlate_events"]
            verified = len(correlation_calls) > 0
            return {
                "check_type": check_type,
                "verified": verified,
                "details": f"Found {len(correlation_calls)} correlate_events calls",
                "evidence": correlation_calls
            }

        elif check_type == "identified_root_cause":
            # Check if RCA identified the actual root cause (security group misconfiguration)
            # Look for get_recent_changes and security group checks
            changes_calls = [c for c in tool_log if c["tool"] == "get_recent_changes"]
            security_checks = [c for c in tool_log if c["tool"] == "ask_security_agent"]

            # Root cause identification requires checking recent changes AND security config
            verified = len(changes_calls) > 0 and len(security_checks) > 0
            return {
                "check_type": check_type,
                "verified": verified,
                "details": f"Changes checked: {len(changes_calls)}, Security checks: {len(security_checks)}",
                "evidence": {"changes_calls": changes_calls, "security_checks": security_checks}
            }

        elif check_type == "avoided_symptom_treatment":
            # Check if RCA avoided wasteful scaling (symptom treatment)
            # Look for scale_service calls - should NOT be present if root cause was identified
            scale_calls = [c for c in tool_log if c["tool"] == "scale_service"]

            # If agent properly identified root cause, it should NOT scale
            verified = len(scale_calls) == 0
            return {
                "check_type": check_type,
                "verified": verified,
                "details": f"Scale calls: {len(scale_calls)} (should be 0 for root cause fix)",
                "evidence": scale_calls
            }

        elif check_type == "coordinated_remediation":
            # Check if RCA coordinated remediation through security agent
            # Look for ask_security_agent calls that contain remediation keywords
            security_calls = [c for c in tool_log if c["tool"] == "ask_security_agent"]

            remediation_calls = []
            for call in security_calls:
                task = call.get("params", {}).get("task", "").lower()
                if any(keyword in task for keyword in ["update", "fix", "remediate", "restore", "allow"]):
                    remediation_calls.append(call)

            verified = len(remediation_calls) > 0
            return {
                "check_type": check_type,
                "verified": verified,
                "details": f"Found {len(remediation_calls)} remediation delegation calls",
                "evidence": remediation_calls
            }

        else:
            return {
                "check_type": check_type,
                "verified": False,
                "details": f"Unknown check type: {check_type}",
                "evidence": []
            }

    def evaluate(self) -> Dict[str, Any]:
        """Run agent-as-judge evaluation."""
        print("\n" + "="*80)
        print("Agent-as-Judge Evaluation - Scenario 3: Multi-Agent RCA")
        print("="*80)
        print()

        self.metrics["start_time"] = datetime.now().isoformat()
        start_time = time.time()

        # Run evaluation
        print("Evaluator agent is testing RCA worker capabilities...")
        print()

        evaluation_prompt = "Test the RCA orchestrator agent's capabilities against its agent card. Focus on multi-agent coordination: delegation to specialized agents, temporal correlation, root cause identification (not symptom treatment), and remediation coordination. For each capability, ask the agent to demonstrate it, then verify execution using environment inspection."

        try:
            response = self.evaluator_agent.handle_message(evaluation_prompt)

            self.metrics["end_time"] = datetime.now().isoformat()
            self.metrics["total_time_seconds"] = round(time.time() - start_time, 2)

            # Parse assessment from response
            assessment = self._parse_assessment(response)

            # Build final result
            result = {
                "evaluator": "Agent-as-Judge (Multi-Agent Capability Auditor)",
                "scenario": "scenario-3",
                "agent_tested": "rca_agent",
                "evaluation_time": datetime.now().isoformat(),
                "test_results": self.test_results,
                "conversation_transcript": self.conversation_transcript,
                "assessment": assessment,
                "metrics": self.metrics
            }

            return result

        except Exception as e:
            print(f"Error during evaluation: {e}")
            import traceback
            traceback.print_exc()
            return {
                "evaluator": "Agent-as-Judge",
                "scenario": "scenario-3",
                "error": str(e),
                "metrics": self.metrics
            }

    def _parse_assessment(self, response: str) -> Dict[str, Any]:
        """Parse final assessment from evaluator response."""
        # Try to find JSON in response
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                assessment = json.loads(json_str)

                # Update metrics based on assessment
                self.metrics["capabilities_verified"] = assessment.get("tests_passed", 0)
                self.metrics["capabilities_failed"] = assessment.get("tests_failed", 0)
                self.metrics["capability_tests"] = assessment.get("tests_passed", 0) + assessment.get("tests_failed", 0)

                return assessment
        except Exception as e:
            print(f"Could not parse assessment JSON: {e}")

        # Fallback: parse markdown and use test_results metrics
        print("Using fallback assessment parsing...")

        assessment = {
            "capabilities_tested": [],
            "tests_passed": self.metrics["capabilities_verified"],
            "tests_failed": self.metrics["capabilities_failed"],
            "failures": [],
            "agent_card_compliance": "COMPLIANT" if self.metrics["capabilities_failed"] == 0 else "NON-COMPLIANT",
            "overall_score": 100 if self.metrics["capabilities_failed"] == 0 else int((self.metrics["capabilities_verified"] / max(self.metrics["capability_tests"], 1)) * 100)
        }

        return assessment

    def print_results(self):
        """Print evaluation results."""
        result = self.evaluate() if not hasattr(self, '_result') else self._result
        self._result = result

        print("\n" + "="*80)
        print("AGENT-AS-JUDGE EVALUATION RESULTS")
        print("="*80)
        print()

        assessment = result.get("assessment", {})
        metrics = result.get("metrics", {})

        print(f"Agent Tested: {result.get('agent_tested')}")
        print(f"Scenario: {result.get('scenario')}")
        print()

        print(f"Capabilities Tested: {metrics.get('capability_tests', 0)}")
        print(f"Capabilities Verified: {metrics.get('capabilities_verified', 0)}")
        print(f"Capabilities Failed: {metrics.get('capabilities_failed', 0)}")
        print()

        print(f"Agent Card Compliance: {assessment.get('agent_card_compliance', 'UNKNOWN')}")
        print(f"Overall Score: {assessment.get('overall_score', 0)}/100")
        print()

        if assessment.get('failures'):
            print("Failures:")
            for failure in assessment['failures']:
                print(f"  - {failure}")
            print()

        print("Evaluation Metrics:")
        print(f"  Conversation turns: {metrics.get('conversation_turns', 0)}")
        print(f"  Worker agent calls: {metrics.get('worker_agent_calls', 0)}")
        print(f"  Environment verifications: {metrics.get('environment_tool_calls', 0)}")
        print(f"  Total time: {metrics.get('total_time_seconds', 0)}s")
        print()

        print("="*80)

    def print_summary_table(self):
        """Print summary table for research paper."""
        from prettytable import PrettyTable

        result = self._result if hasattr(self, '_result') else self.evaluate()
        self._result = result

        assessment = result.get("assessment", {})
        metrics = result.get("metrics", {})

        print("\n" + "="*80)
        print("AGENT-AS-JUDGE SUMMARY TABLE (Scenario 3)")
        print("="*80)
        print()

        table = PrettyTable()
        table.field_names = ["Metric", "Value"]
        table.align["Metric"] = "l"
        table.align["Value"] = "r"

        table.add_row(["Agent Tested", result.get("agent_tested")])
        table.add_row(["Scenario", result.get("scenario")])
        table.add_row(["Capabilities Tested", metrics.get("capability_tests", 0)])
        table.add_row(["Capabilities Verified", metrics.get("capabilities_verified", 0)])
        table.add_row(["Capabilities Failed", metrics.get("capabilities_failed", 0)])
        table.add_row(["Agent Card Compliance", assessment.get("agent_card_compliance", "UNKNOWN")])
        table.add_row(["Overall Score", f"{assessment.get('overall_score', 0)}/100"])
        table.add_row(["Conversation Turns", metrics.get("conversation_turns", 0)])
        table.add_row(["Worker Agent Calls", metrics.get("worker_agent_calls", 0)])
        table.add_row(["Environment Verifications", metrics.get("environment_tool_calls", 0)])
        table.add_row(["Total Evaluation Time", f"{metrics.get('total_time_seconds', 0)}s"])

        print(table)
        print()

        # Capability test breakdown
        print("Capability Test Breakdown:")
        print()

        # Count tests by type from conversation transcript
        test_types = {
            "delegated_to_performance": {"pass": 0, "fail": 0},
            "delegated_to_security": {"pass": 0, "fail": 0},
            "performed_correlation": {"pass": 0, "fail": 0},
            "identified_root_cause": {"pass": 0, "fail": 0},
            "avoided_symptom_treatment": {"pass": 0, "fail": 0},
            "coordinated_remediation": {"pass": 0, "fail": 0}
        }

        for transcript_entry in result.get("conversation_transcript", []):
            if transcript_entry.get("role") == "evaluator_to_worker":
                instruction = transcript_entry.get("instruction", "").lower()
                # Infer test type from instruction
                if "performance" in instruction and ("delegate" in instruction or "analyze" in instruction):
                    test_types["delegated_to_performance"]["pass"] += 1
                elif "security" in instruction and ("delegate" in instruction or "check" in instruction):
                    test_types["delegated_to_security"]["pass"] += 1
                elif "correlat" in instruction or "timing" in instruction:
                    test_types["performed_correlation"]["pass"] += 1
                elif "root cause" in instruction:
                    test_types["identified_root_cause"]["pass"] += 1
                elif "scale" in instruction or "symptom" in instruction:
                    test_types["avoided_symptom_treatment"]["pass"] += 1
                elif "remediat" in instruction or "fix" in instruction:
                    test_types["coordinated_remediation"]["pass"] += 1

        total_tests = sum(counts["pass"] + counts["fail"] for counts in test_types.values())

        if total_tests > 0:
            for test_type, counts in test_types.items():
                total = counts["pass"] + counts["fail"]
                if total > 0:
                    pass_rate = (counts["pass"] / total * 100)
                    print(f"  {test_type}: {counts['pass']}/{total} ({pass_rate:.0f}%)")
        else:
            print("  No capability tests recorded in transcript")

        print()
        print("="*80)

    def save_results(self, output_dir: str = None):
        """Save evaluation results to JSON."""
        result = self._result if hasattr(self, '_result') else self.evaluate()
        self._result = result

        if output_dir is None:
            output_dir = self.scenario_path / "logs"

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"scenario-3_{timestamp}_agent_judge.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)

        print(f"Results saved to: {output_file}")
        return str(output_file)


def main():
    """Run Agent-as-Judge evaluation for Scenario 3."""
    scenario_path = "simulations/scenario-3"

    evaluator = AgentAsJudgeEvaluator(scenario_path)
    evaluator.print_results()
    evaluator.save_results()

    # Print summary table for paper
    print("\n")
    evaluator.print_summary_table()


if __name__ == "__main__":
    main()
