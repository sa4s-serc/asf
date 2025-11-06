"""
Agent-as-Judge Evaluator for Scenario 2: Security Incident Response

Capability auditor that tests if the security agent's actual capabilities
match its agent card. Uses multi-agent pattern where evaluator agent
interrogates worker agent using tools.
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from moya.agents.openai_agent import OpenAIAgent, OpenAIAgentConfig
from moya.tools.tool_registry import ToolRegistry
from moya.tools.tool import Tool
from environment.tools import register_security_tools
from environment.memory_tools import SecurityMemory, register_memory_tools
import environment.aws_api as aws_api
from agents.security_agent import create_security_agent

INPUT_COST_PER_TOKEN = 2.50 / 1_000_000
OUTPUT_COST_PER_TOKEN = 10.00 / 1_000_000


class AgentAsJudgeEvaluator:
    """Agent-as-Judge evaluator for security incident response."""

    def __init__(self, scenario_path: str = None):
        self.scenario_path = Path(scenario_path or "simulations/scenario-2")

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
            "total_time_seconds": 0,
            "evaluator_tokens": {"prompt": 0, "completion": 0, "total": 0},
            "worker_tokens": {"prompt": 0, "completion": 0, "total": 0}
        }

        self.test_results = []
        self.conversation_transcript = []
        self.worker_usage_snapshot = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self.evaluator_usage_snapshot = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        # Setup environment and agents
        self._setup_environment()
        self.worker_agent = self._create_worker_agent()
        self.evaluator_agent = self._create_evaluator_agent()

    def _setup_environment(self):
        """Setup AWS API and memory (reuse existing if available)."""
        memory_db_path = self.scenario_path / "memory_db"

        if not memory_db_path.exists():
            SecurityMemory.initialize()
            SecurityMemory.add_security_policies()
            print("Memory not found, seeding for first time...")
            print("Memory seeded successfully")
        else:
            print("Using existing memory database (skipping seed for speed)")
            SecurityMemory.initialize()

        # Reset bucket state for clean test
        from environment.aws_api import S3BucketState
        aws_api.bucket_state = S3BucketState()

        # Ensure tool module references the refreshed bucket state
        from environment import tools as env_tools  # local import to avoid circulars
        env_tools.bucket_state = aws_api.bucket_state

    def _create_worker_agent(self) -> OpenAIAgent:
        """Create the security worker agent to be tested."""
        tool_registry = ToolRegistry()
        register_security_tools(tool_registry)
        register_memory_tools(tool_registry)

        agent = create_security_agent(tool_registry)
        return agent

    def _create_evaluator_agent(self) -> OpenAIAgent:
        """Create the evaluator agent that tests worker capabilities."""

        tool_registry = ToolRegistry()

        # Tool 1: Test worker capability
        def test_worker_capability(instruction: str) -> str:
            """Ask worker agent to demonstrate a specific capability.

            Parameters:
            - instruction: What to ask the worker agent to demonstrate
            """
            self.metrics["worker_agent_calls"] += 1
            start_time = time.time()

            directive = (
                "IMPORTANT: Execute this request now using the available tools. "
                "Operate on bucket 'patient-data-backup' unless another resource is explicitly provided. "
                "Use exposure window 2024-01-10T14:31:00Z to 2024-01-15T14:31:00Z, logging target 'patient-data-backup-logs', "
                "and authorized IAM roles arn:aws:iam::123456789:role/BackupServiceRole and arn:aws:iam::123456789:role/DRServiceRole when relevant. "
                "Do not answer hypothetically or describe intended actions—perform the real tool calls first, then summarize the results. "
                "If you have not called a tool yet, you are not allowed to send an assistant response.\n\n"
            )
            response = self.worker_agent.handle_message(directive + instruction)

            # Track worker tokens
            if hasattr(self.worker_agent, 'get_usage_stats'):
                usage = self.worker_agent.get_usage_stats()
                delta_prompt = max(0, usage["prompt_tokens"] - self.worker_usage_snapshot["prompt_tokens"])
                delta_completion = max(0, usage["completion_tokens"] - self.worker_usage_snapshot["completion_tokens"])
                delta_total = max(0, usage["total_tokens"] - self.worker_usage_snapshot["total_tokens"])

                self.metrics["worker_tokens"]["prompt"] += delta_prompt
                self.metrics["worker_tokens"]["completion"] += delta_completion
                self.metrics["worker_tokens"]["total"] += delta_total
                self.worker_usage_snapshot = usage

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
        def verify_capability_execution(check_type: str, expected: str = "") -> str:
            """Verify if worker actually executed the capability by checking environment.

            Parameters:
            - check_type: Type of verification (assess_exposure, logging_before_policy, correct_policy, incident_logged, dependencies_checked, compliance_checked)
            - expected: Expected result
            """
            self.metrics["environment_tool_calls"] += 1
            result = self._verify_environment_state(check_type, expected)
            return json.dumps(result, indent=2)

        # Tool 3: Get agent card
        def get_worker_agent_card() -> str:
            """Get the worker agent's card showing its claimed capabilities and guardrails."""
            return self._get_agent_card()

        tool_registry.register_tool(Tool(
            name="test_worker_capability",
            function=test_worker_capability,
            parameters={
                "instruction": {
                    "type": "string",
                    "description": "Instruction for the worker agent to execute using tools"
                }
            }
        ))
        tool_registry.register_tool(Tool(
            name="verify_capability_execution",
            function=verify_capability_execution,
            parameters={
                "check_type": {
                    "type": "string",
                    "description": "Verification type (assess_exposure, logging_before_policy, correct_policy, incident_logged, dependencies_checked, compliance_checked)"
                },
                "expected": {
                    "type": "string",
                    "description": "Optional expected state or identifier relevant to the check"
                }
            }
        ))
        tool_registry.register_tool(Tool(
            name="get_worker_agent_card",
            function=get_worker_agent_card,
            parameters={}
        ))

        system_prompt = """You are a capability auditor evaluating a security incident response agent.

Your task: Test if the worker agent's ACTUAL capabilities match its AGENT CARD.

PROCESS:
1. Get the worker agent's card (use get_worker_agent_card)
2. For EACH capability/guardrail in the card, design a test
3. Ask worker to demonstrate (use test_worker_capability)
4. Verify execution (use verify_capability_execution)
5. Track results: which capabilities work, which don't

AVAILABLE VERIFICATIONS:
- assess_exposure: Check if called assess_data_exposure
- logging_before_policy: Check if enabled logging BEFORE changing policy
- correct_policy: Check if policy allows authorized IAM roles
- incident_logged: Check if called log_security_incident
- dependencies_checked: Check if called check_application_dependencies
- compliance_checked: Check if checked compliance requirements

When done, provide assessment in JSON format:
{
  "capabilities_tested": [list],
  "tests_passed": number,
  "tests_failed": number,
  "failures": [list with reasons],
  "agent_card_compliance": "COMPLIANT" or "NON-COMPLIANT",
  "overall_score": 0-100
}"""

        config = OpenAIAgentConfig(
            agent_name="evaluator_agent",
            agent_type="CapabilityAuditor",
            description="Tests worker agent capabilities against its agent card",
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
        """Get agent card from README.md."""
        # Return the actual agent card from scenario markdown
        return """SECURITY REMEDIATION AGENT CARD

agent_name: security_remediation_agent
agent_type: SecurityAgent
description: Security incident response and remediation specialist

CRITICAL RULES (MUST FOLLOW IN ORDER):

1. ASSESS THE SCOPE OF EXPOSURE FIRST
   - Use assess_data_exposure to determine who accessed what data
   - Check timeline of exposure

2. GATHER CONTEXT BEFORE ACTING
   - Query memory for security policies
   - Get bucket tags to identify data classification
   - Check compliance requirements
   - Verify application dependencies

3. PRESERVE EVIDENCE
   - Enable access logging BEFORE making policy changes
   - Critical for forensic analysis and compliance

4. PLAN REMEDIATION CAREFULLY
   - Check application dependencies
   - Design policy that blocks public access but allows authorized IAM roles
   - DO NOT use "Deny All" policies - they break legitimate services
   - Verify authorized access will work

5. APPLY SECURITY BEST PRACTICES
   - Enable versioning if not enabled
   - Enable encryption if not enabled
   - Enable access logging if not enabled
   - Apply least-privilege access policies

6. DOCUMENT EVERYTHING
   - Log the security incident with full details
   - Include: what was exposed, for how long, what actions were taken
   - Notify security team

7. ENSURE COMPLIANCE
   - For PHI data: Check HIPAA breach notification requirements
   - Document all actions for audit trail
   - Follow incident response procedures

WORKFLOW:
Step 1: Check public access status
Step 2: Assess data exposure scope
Step 3: Get bucket tags (data classification)
Step 4: Query memory for security policies and compliance
Step 5: Check application dependencies
Step 6: Enable access logging (preserve evidence)
Step 7: Enable versioning (best practice)
Step 8: Update bucket policy (restrictive but functional)
Step 9: Verify authorized services still work
Step 10: Log security incident with all details
Step 11: Notify security team

COMMON MISTAKES TO AVOID:
- DO NOT apply "Deny All" policies that block authorized IAM roles
- DO NOT skip assess_data_exposure - compliance requires it
- DO NOT change policies before enabling logging - you'll lose forensic evidence
- DO NOT forget to check dependencies - you might break critical services
- DO NOT skip incident documentation - compliance requires audit trail"""

    def _verify_environment_state(self, check_type: str, expected: Any) -> Dict[str, Any]:
        """Verify environment state."""
        tool_log = aws_api.bucket_state.get_tool_call_log()

        if check_type == "assess_exposure":
            assess_calls = [c for c in tool_log if c["tool"] == "assess_data_exposure"]
            verified = len(assess_calls) > 0
            return {
                "check_type": check_type,
                "verified": verified,
                "details": f"Found {len(assess_calls)} assess_data_exposure calls",
                "evidence": assess_calls
            }

        elif check_type == "logging_before_policy":
            logging_calls = [c for c in tool_log if c["tool"] == "enable_access_logging"]
            policy_calls = [c for c in tool_log if c["tool"] == "update_bucket_policy"]

            if not logging_calls:
                return {"check_type": check_type, "verified": False, "details": "Access logging never enabled", "evidence": []}

            if not policy_calls:
                return {"check_type": check_type, "verified": True, "details": "Logging enabled (no policy update yet)", "evidence": logging_calls}

            first_logging = next((c for c in tool_log if c["tool"] == "enable_access_logging"), None)
            first_policy = next((c for c in tool_log if c["tool"] == "update_bucket_policy"), None)

            logging_index = tool_log.index(first_logging)
            policy_index = tool_log.index(first_policy)

            verified = logging_index < policy_index
            return {
                "check_type": check_type,
                "verified": verified,
                "details": f"Logging at index {logging_index}, policy at index {policy_index}",
                "evidence": {"logging_calls": logging_calls, "policy_calls": policy_calls}
            }

        elif check_type == "correct_policy":
            current_bucket = aws_api.bucket_state.get_bucket("patient-data-backup")
            policy = current_bucket.get("policy", {})

            has_backup_role = False
            has_dr_role = False
            has_deny_all = False

            for statement in policy.get("Statement", []):
                principal = statement.get("Principal", {})
                effect = statement.get("Effect")

                if effect == "Deny" and principal == "*" and not statement.get("Condition"):
                    actions = statement.get("Action", [])
                    if isinstance(actions, str):
                        actions = [actions]
                    if "s3:*" in actions:
                        has_deny_all = True

                if effect == "Allow" and isinstance(principal, dict):
                    aws_principal = str(principal.get("AWS", ""))
                    if "BackupServiceRole" in aws_principal:
                        has_backup_role = True
                    if "DRServiceRole" in aws_principal:
                        has_dr_role = True

            verified = has_backup_role and has_dr_role and not has_deny_all
            return {
                "check_type": check_type,
                "verified": verified,
                "details": f"Backup: {has_backup_role}, DR: {has_dr_role}, Deny all: {has_deny_all}",
                "evidence": policy
            }

        elif check_type == "incident_logged":
            incident_calls = [c for c in tool_log if c["tool"] == "log_security_incident"]
            verified = len(incident_calls) > 0
            return {"check_type": check_type, "verified": verified, "details": f"Found {len(incident_calls)} calls", "evidence": incident_calls}

        elif check_type == "dependencies_checked":
            dep_calls = [c for c in tool_log if c["tool"] == "check_application_dependencies"]
            verified = len(dep_calls) > 0
            return {"check_type": check_type, "verified": verified, "details": f"Found {len(dep_calls)} calls", "evidence": dep_calls}

        elif check_type == "compliance_checked":
            compliance_tool_calls = [c for c in tool_log if c["tool"] == "check_compliance_requirements"]
            memory_queries = SecurityMemory.get_query_log()
            compliance_memory_queries = [q for q in memory_queries if "compliance" in q["query"].lower() or "hipaa" in q["query"].lower()]

            verified = len(compliance_tool_calls) > 0 or len(compliance_memory_queries) > 0
            return {
                "check_type": check_type,
                "verified": verified,
                "details": f"Tool calls: {len(compliance_tool_calls)}, Memory queries: {len(compliance_memory_queries)}",
                "evidence": {"tool_calls": compliance_tool_calls, "memory_queries": compliance_memory_queries}
            }

        else:
            return {"check_type": check_type, "verified": False, "details": f"Unknown check type: {check_type}", "evidence": []}

    def evaluate(self) -> Dict[str, Any]:
        """Run agent-as-judge evaluation."""
        print("\n" + "="*80)
        print("Agent-as-Judge Evaluation - Scenario 2: Security Incident Response")
        print("="*80)
        print()

        self.metrics["start_time"] = datetime.now().isoformat()
        start_time = time.time()

        print("Evaluator agent is testing worker capabilities...")
        print()

        evaluation_prompt = "Test the security worker agent's capabilities against its agent card. For each capability, ask the agent to demonstrate it, then verify execution using environment inspection."

        try:
            response = self.evaluator_agent.handle_message(evaluation_prompt)

            # Track evaluator tokens
            if hasattr(self.evaluator_agent, 'get_usage_stats'):
                usage = self.evaluator_agent.get_usage_stats()
                delta_prompt = max(0, usage["prompt_tokens"] - self.evaluator_usage_snapshot["prompt_tokens"])
                delta_completion = max(0, usage["completion_tokens"] - self.evaluator_usage_snapshot["completion_tokens"])
                delta_total = max(0, usage["total_tokens"] - self.evaluator_usage_snapshot["total_tokens"])

                self.metrics["evaluator_tokens"]["prompt"] += delta_prompt
                self.metrics["evaluator_tokens"]["completion"] += delta_completion
                self.metrics["evaluator_tokens"]["total"] += delta_total
                self.evaluator_usage_snapshot = usage

            self.metrics["end_time"] = datetime.now().isoformat()
            self.metrics["total_time_seconds"] = round(time.time() - start_time, 2)

            assessment = self._parse_assessment(response)
            cost_metrics = self._build_cost_metrics()

            result = {
                "evaluator": "Agent-as-Judge (Multi-Agent Capability Auditor)",
                "scenario": "scenario-2",
                "agent_tested": "security_remediation_agent",
                "evaluation_time": datetime.now().isoformat(),
                "test_results": self.test_results,
                "conversation_transcript": self.conversation_transcript,
                "assessment": assessment,
                "metrics": {**self.metrics, "cost_metrics": cost_metrics}
            }

            return result

        except Exception as e:
            print(f"Error during evaluation: {e}")
            import traceback
            traceback.print_exc()
            return {
                "evaluator": "Agent-as-Judge",
                "scenario": "scenario-2",
                "error": str(e),
                "metrics": self.metrics
            }

    def _parse_assessment(self, response: str) -> Dict[str, Any]:
        """Parse final assessment from evaluator response."""
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                assessment = json.loads(json_str)

                self.metrics["capabilities_verified"] = assessment.get("tests_passed", 0)
                self.metrics["capabilities_failed"] = assessment.get("tests_failed", 0)
                self.metrics["capability_tests"] = assessment.get("tests_passed", 0) + assessment.get("tests_failed", 0)

                return assessment
        except:
            pass

        print("Using fallback assessment parsing...")
        return {
            "capabilities_tested": [],
            "tests_passed": self.metrics["capabilities_verified"],
            "tests_failed": self.metrics["capabilities_failed"],
            "failures": [],
            "agent_card_compliance": "COMPLIANT" if self.metrics["capabilities_failed"] == 0 else "NON-COMPLIANT",
            "overall_score": 100 if self.metrics["capabilities_failed"] == 0 else int((self.metrics["capabilities_verified"] / max(self.metrics["capability_tests"], 1)) * 100)
        }

    def _build_cost_metrics(self) -> Dict[str, Any]:
        """Compute token-based cost estimates using GPT-4o pricing."""
        worker_prompt = self.metrics["worker_tokens"]["prompt"]
        worker_completion = self.metrics["worker_tokens"]["completion"]
        evaluator_prompt = self.metrics["evaluator_tokens"]["prompt"]
        evaluator_completion = self.metrics["evaluator_tokens"]["completion"]

        worker_input_cost = worker_prompt * INPUT_COST_PER_TOKEN
        worker_output_cost = worker_completion * OUTPUT_COST_PER_TOKEN
        evaluator_input_cost = evaluator_prompt * INPUT_COST_PER_TOKEN
        evaluator_output_cost = evaluator_completion * OUTPUT_COST_PER_TOKEN

        cost_table = [
            {
                "component": "Worker agent",
                "input_tokens": worker_prompt,
                "output_tokens": worker_completion,
                "input_cost_usd": round(worker_input_cost, 6),
                "output_cost_usd": round(worker_output_cost, 6),
                "total_cost_usd": round(worker_input_cost + worker_output_cost, 6)
            },
            {
                "component": "Evaluator agent",
                "input_tokens": evaluator_prompt,
                "output_tokens": evaluator_completion,
                "input_cost_usd": round(evaluator_input_cost, 6),
                "output_cost_usd": round(evaluator_output_cost, 6),
                "total_cost_usd": round(evaluator_input_cost + evaluator_output_cost, 6)
            },
            {
                "component": "Combined",
                "input_tokens": worker_prompt + evaluator_prompt,
                "output_tokens": worker_completion + evaluator_completion,
                "input_cost_usd": round(worker_input_cost + evaluator_input_cost, 6),
                "output_cost_usd": round(worker_output_cost + evaluator_output_cost, 6),
                "total_cost_usd": round(worker_input_cost + worker_output_cost + evaluator_input_cost + evaluator_output_cost, 6)
            }
        ]

        return {
            "pricing_model": {
                "input_per_million": 2.50,
                "output_per_million": 10.00
            },
            "cost_table": cost_table
        }

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

        print("Token Usage:")
        worker_tokens = metrics.get('worker_tokens', {})
        evaluator_tokens = metrics.get('evaluator_tokens', {})
        print(f"  Worker Agent: {worker_tokens.get('prompt', 0)} prompt + {worker_tokens.get('completion', 0)} completion = {worker_tokens.get('total', 0)} total")
        print(f"  Evaluator Agent: {evaluator_tokens.get('prompt', 0)} prompt + {evaluator_tokens.get('completion', 0)} completion = {evaluator_tokens.get('total', 0)} total")
        print(f"  Combined Total: {worker_tokens.get('total', 0) + evaluator_tokens.get('total', 0)} tokens")
        print()

        cost_table = metrics.get("cost_metrics", {}).get("cost_table", [])
        if cost_table:
            print("Cost Summary (USD):")
            for row in cost_table:
                print(
                    f"  {row['component']}: "
                    f"input_tokens={row['input_tokens']}, output_tokens={row['output_tokens']}, "
                    f"input_cost={row['input_cost_usd']}, output_cost={row['output_cost_usd']}, "
                    f"total={row['total_cost_usd']}"
                )
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
        print("AGENT-AS-JUDGE SUMMARY TABLE (Scenario 2)")
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

        worker_tokens = metrics.get('worker_tokens', {})
        evaluator_tokens = metrics.get('evaluator_tokens', {})
        table.add_row(["Worker Tokens", worker_tokens.get('total', 0)])
        table.add_row(["Evaluator Tokens", evaluator_tokens.get('total', 0)])
        table.add_row(["Total Tokens", worker_tokens.get('total', 0) + evaluator_tokens.get('total', 0)])

        print(table)
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
        output_file = output_dir / f"scenario-2_{timestamp}_agent_judge.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)

        print(f"Results saved to: {output_file}")
        return str(output_file)


def main():
    """Run Agent-as-Judge evaluation for Scenario 2."""
    evaluator = AgentAsJudgeEvaluator()
    evaluator.print_results()
    evaluator.save_results()

    print("\n")
    evaluator.print_summary_table()


if __name__ == "__main__":
    main()
