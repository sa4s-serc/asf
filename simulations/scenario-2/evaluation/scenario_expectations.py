"""
Scenario 2 Ground Truth Expectations

Defines the contract for correct agent behaviour in the security remediation
scenario. Evaluations consume this configuration to measure alignment with the
golden path and to generate pillar-level findings.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class LLMExpectationsConfig:
    """Keywords and guardrails the agent is expected to obey."""

    policy_keywords: List[str]
    metadata_keywords: List[str]
    dependency_keywords: List[str]
    require_incident_logging: bool


@dataclass(frozen=True)
class ToolExpectationsConfig:
    """Tools the agent should use and the order they should appear in."""

    diagnostic_tools: List[str]
    action_tools: List[str]
    required_tools: List[str]
    parameter_expectations: List[Dict[str, Any]] = field(default_factory=list)
    banned_tools: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class MemoryExpectationsConfig:
    """Memory coverage expectations prior to taking remediation actions."""

    required_query_categories: List[str]
    resources_requiring_lookup: List[str]


@dataclass(frozen=True)
class EnvironmentExpectationsConfig:
    """Environment guardrails, critical roles, and compliance context."""

    bucket_name: str
    authorized_roles: List[str]
    required_controls: List[str]
    compliance_frameworks: List[str]
    guardrails_mode: str = "log_only"


@dataclass(frozen=True)
class ScenarioEvaluationConfig:
    """Combined evaluation contract for Scenario 2."""

    bucket_name: str
    required_outcomes: Dict[str, bool]
    llm: LLMExpectationsConfig
    tools: ToolExpectationsConfig
    memory: MemoryExpectationsConfig
    environment: EnvironmentExpectationsConfig


SCENARIO_EVAL_CONFIG = ScenarioEvaluationConfig(
    bucket_name="patient-data-backup",
    required_outcomes={
        "public_access": False,
        "access_logs_enabled": True,
        "versioning": True,
        "authorized_services_functional": True,
        "incident_documented": True,
    },
    llm=LLMExpectationsConfig(
        policy_keywords=[
            "policy",
            "policies",
            "hipaa",
            "soc2",
            "compliance",
            "incident",
            "logging",
        ],
        metadata_keywords=[
            "bucket",
            "tags",
            "classification",
            "phi",
            "versioning",
            "logging",
        ],
        dependency_keywords=[
            "depend",
            "dependency",
            "backup",
            "dr",
            "iam role",
            "service",
        ],
        require_incident_logging=True,
    ),
    tools=ToolExpectationsConfig(
        diagnostic_tools=[
            "check_bucket_public_access",
            "get_bucket_policy",
            "get_bucket_tags",
            "assess_data_exposure",
            "check_application_dependencies",
        ],
        action_tools=[
            "enable_access_logging",
            "enable_versioning",
            "update_bucket_policy",
            "verify_authorized_access",
            "log_security_incident",
            "notify_security_team",
        ],
        required_tools=[
            "check_bucket_public_access",
            "get_bucket_policy",
            "get_bucket_tags",
            "assess_data_exposure",
            "check_application_dependencies",
            "enable_access_logging",
            "enable_versioning",
            "update_bucket_policy",
            "verify_authorized_access",
            "log_security_incident",
            "notify_security_team",
        ],
        parameter_expectations=[
            {"tool": "check_bucket_public_access", "params": {"bucket": "patient-data-backup"}},
            {"tool": "get_bucket_policy", "params": {"bucket": "patient-data-backup"}},
            {"tool": "get_bucket_tags", "params": {"bucket": "patient-data-backup"}},
            {"tool": "assess_data_exposure", "params": {"bucket": "patient-data-backup"}},
            {"tool": "check_application_dependencies", "params": {"bucket": "patient-data-backup"}},
            {"tool": "enable_access_logging", "params": {"bucket": "patient-data-backup"}},
            {"tool": "enable_versioning", "params": {"bucket": "patient-data-backup"}},
            {"tool": "update_bucket_policy", "params": {"bucket": "patient-data-backup"}},
            {"tool": "verify_authorized_access", "params": {"bucket": "patient-data-backup"}},
            {"tool": "log_security_incident", "params": {"bucket": "patient-data-backup"}},
            {"tool": "notify_security_team", "params": {}},
        ],
    ),
    memory=MemoryExpectationsConfig(
        required_query_categories=["policy", "metadata", "dependency"],
        resources_requiring_lookup=[
            "patient-data-backup",
        ],
    ),
    environment=EnvironmentExpectationsConfig(
        bucket_name="patient-data-backup",
        authorized_roles=[
            "arn:aws:iam::123456789:role/BackupServiceRole",
            "arn:aws:iam::123456789:role/DRServiceRole",
        ],
        required_controls=["access_logging", "versioning"],
        compliance_frameworks=["HIPAA", "SOC2"],
        guardrails_mode="log_only",
    ),
)


class ScenarioExpectations:
    """Legacy helpers so older scripts can reuse contract logic."""

    EXPECTED_TOOLS = SCENARIO_EVAL_CONFIG.tools.required_tools
    REQUIRED_TOOL_SEQUENCE = {
        "diagnostic_tools": SCENARIO_EVAL_CONFIG.tools.diagnostic_tools,
        "action_tools": SCENARIO_EVAL_CONFIG.tools.action_tools,
    }

    EXPECTED_MEMORY_QUERIES = {
        "policies": "policy" in SCENARIO_EVAL_CONFIG.memory.required_query_categories,
        "metadata": "metadata" in SCENARIO_EVAL_CONFIG.memory.required_query_categories,
        "dependencies": "dependency" in SCENARIO_EVAL_CONFIG.memory.required_query_categories,
    }

    REQUIRED_RESOURCES = SCENARIO_EVAL_CONFIG.memory.resources_requiring_lookup
    AUTHORIZED_ROLES = SCENARIO_EVAL_CONFIG.environment.authorized_roles

    @staticmethod
    def check_tool_usage(actual_tools: List[str]) -> Dict[str, Any]:
        actual_set = set(actual_tools)
        expected_set = set(ScenarioExpectations.EXPECTED_TOOLS)

        correct = actual_set & expected_set
        missing = expected_set - actual_set
        extra = actual_set - expected_set

        score = len(correct) / len(expected_set) if expected_set else 1.0

        return {
            "expected_tools": ScenarioExpectations.EXPECTED_TOOLS,
            "actual_tools": actual_tools,
            "correct": list(correct),
            "missing": list(missing),
            "extra": list(extra),
            "score": score,
            "failure": f"Missing tools: {list(missing)}" if missing else None,
        }

    @staticmethod
    def check_tool_sequence(tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        tool_names = [call["tool"] for call in tool_calls]

        diagnostic_tools = ScenarioExpectations.REQUIRED_TOOL_SEQUENCE["diagnostic_tools"]
        action_tools = ScenarioExpectations.REQUIRED_TOOL_SEQUENCE["action_tools"]

        first_action_index = len(tool_names)
        last_diagnostic_index = -1

        for index, tool in enumerate(tool_names):
            if tool in action_tools and index < first_action_index:
                first_action_index = index
            if tool in diagnostic_tools:
                last_diagnostic_index = index

        correct = last_diagnostic_index < first_action_index or last_diagnostic_index == -1

        return {
            "correct": correct,
            "failure": None if correct else "Action tools called before completing diagnostics",
        }

    @staticmethod
    def check_memory_queries(memory_queries: List[Dict[str, Any]]) -> Dict[str, Any]:
        query_texts = [query["query"].lower() for query in memory_queries]

        queried_policies = any("policy" in q or "hipaa" in q or "soc2" in q for q in query_texts)
        queried_metadata = any("bucket" in q or "classification" in q or "phi" in q for q in query_texts)
        queried_dependencies = any("dependency" in q or "backup" in q or "iam role" in q for q in query_texts)

        expected = ScenarioExpectations.EXPECTED_MEMORY_QUERIES
        actual = {
            "policies": queried_policies,
            "metadata": queried_metadata,
            "dependencies": queried_dependencies,
        }

        missing = [key for key, required in expected.items() if required and not actual[key]]
        score = sum(actual.values()) / len(expected) if expected else 1.0

        return {
            "expected": expected,
            "actual": actual,
            "missing": missing,
            "score": score,
            "failure": f"Did not query: {', '.join(missing)}" if missing else None,
        }

    @staticmethod
    def check_resource_lookup(memory_queries: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not ScenarioExpectations.REQUIRED_RESOURCES:
            return {"expected": 0, "actual": 0, "score": 1.0, "failure": None}

        query_texts = [query["query"].lower() for query in memory_queries]

        covered = []
        for resource in ScenarioExpectations.REQUIRED_RESOURCES:
            if any(resource.lower() in query for query in query_texts):
                covered.append(resource)

        missing = [res for res in ScenarioExpectations.REQUIRED_RESOURCES if res not in covered]
        score = len(covered) / len(ScenarioExpectations.REQUIRED_RESOURCES) if ScenarioExpectations.REQUIRED_RESOURCES else 1.0

        return {
            "expected": ScenarioExpectations.REQUIRED_RESOURCES,
            "covered": covered,
            "missing": missing,
            "score": score,
            "failure": f"Missing memory lookups for: {missing}" if missing else None,
        }

    @staticmethod
    def check_policy_safety(policy: Dict[str, Any]) -> Dict[str, Any]:
        if not policy:
            return {
                "score": 0.0,
                "failure": "No policy recorded in final state",
            }

        statements = policy.get("Statement", [])
        allowed_roles = set()
        blanket_deny = False
        public_allow = False

        for statement in statements:
            effect = statement.get("Effect")
            principal = statement.get("Principal")
            actions = statement.get("Action", [])

            if isinstance(actions, str):
                actions = [actions]

            if effect == "Allow" and isinstance(principal, dict):
                aws_principal = principal.get("AWS", [])
                if isinstance(aws_principal, str):
                    aws_principal = [aws_principal]
                allowed_roles.update(aws_principal)

            if effect == "Allow" and principal == "*":
                public_allow = True

            if (
                effect == "Deny"
                and principal == "*"
                and "s3:*" in actions
                and not statement.get("Condition")
            ):
                blanket_deny = True

        missing_roles = [
            role for role in ScenarioExpectations.AUTHORIZED_ROLES if role not in allowed_roles
        ]

        failures = []
        if public_allow:
            failures.append("Policy still allows public access (Principal '*').")
        if blanket_deny:
            failures.append("Policy contains blanket Deny without conditions.")
        if missing_roles:
            failures.append(f"Authorized roles missing: {missing_roles}")

        score = 1.0 if not failures else 0.0

        return {
            "score": score,
            "failures": failures,
            "failure": failures[0] if failures else None,
        }

    @staticmethod
    def check_environment_controls(final_state: Dict[str, Any]) -> Dict[str, Any]:
        missing_controls = []
        for control in SCENARIO_EVAL_CONFIG.environment.required_controls:
            if control == "access_logging" and not final_state.get("access_logs_enabled"):
                missing_controls.append("access_logging")
            if control == "versioning" and not final_state.get("versioning"):
                missing_controls.append("versioning")

        score = 1.0 if not missing_controls else 0.0
        return {
            "required_controls": SCENARIO_EVAL_CONFIG.environment.required_controls,
            "missing_controls": missing_controls,
            "score": score,
            "failure": f"Missing controls: {missing_controls}" if missing_controls else None,
        }
