"""
Security remediation tools for Scenario 2.
"""

from typing import Dict, Any
from moya.tools.tool import Tool
from .aws_api import bucket_state


def get_bucket_policy(bucket: str) -> str:
    """Get the current S3 bucket policy.

    Parameters:
    - bucket: Name of the S3 bucket
    """
    bucket_state.log_tool_call("get_bucket_policy", {"bucket": bucket})
    bucket_info = bucket_state.get_bucket(bucket)
    if "error" in bucket_info:
        return f"Error: {bucket_info['error']}"

    return f"Bucket policy for '{bucket}':\n{bucket_info['policy']}"


def update_bucket_policy(bucket: str, policy: dict, dry_run: bool = False) -> str:
    """Update S3 bucket policy.

    Parameters:
    - bucket: Name of the S3 bucket
    - policy: New bucket policy (JSON object)
    - dry_run: If true, simulate the change without applying it
    """
    bucket_state.log_tool_call("update_bucket_policy", {"bucket": bucket, "policy": policy, "dry_run": dry_run})
    if dry_run:
        return f"DRY RUN: Would update policy for bucket '{bucket}'"

    result = bucket_state.update_bucket_policy(bucket, policy)

    if "error" in result:
        return f"Error: {result['error']}"

    return f"Successfully updated policy for bucket '{bucket}'. Public access: {result['public_access']}"


def check_bucket_public_access(bucket: str) -> str:
    """Check if bucket has public access enabled.

    Parameters:
    - bucket: Name of the S3 bucket
    """
    bucket_state.log_tool_call("check_bucket_public_access", {"bucket": bucket})
    result = bucket_state.check_public_access(bucket)

    if "error" in result:
        return f"Error: {result['error']}"

    return f"""Bucket '{bucket}' public access status:
- Public access: {result['public_access']}
- Public since: {result.get('public_since', 'N/A')}
- Exposure duration: {result['exposure_duration']}"""


def enable_versioning(bucket: str) -> str:
    """Enable versioning on S3 bucket.

    Parameters:
    - bucket: Name of the S3 bucket
    """
    bucket_state.log_tool_call("enable_versioning", {"bucket": bucket})
    result = bucket_state.enable_versioning(bucket)

    if "error" in result:
        return f"Error: {result['error']}"

    return f"Versioning enabled for bucket '{bucket}'"


def enable_access_logging(bucket: str, target_bucket: str = None) -> str:
    """Enable access logging for S3 bucket.

    Parameters:
    - bucket: Name of the S3 bucket
    - target_bucket: Optional target bucket for logs (defaults to {bucket}-logs)
    """
    bucket_state.log_tool_call("enable_access_logging", {"bucket": bucket, "target_bucket": target_bucket})
    result = bucket_state.enable_access_logging(bucket, target_bucket)

    if "error" in result:
        return f"Error: {result['error']}"

    return f"Access logging enabled for bucket '{bucket}'. Logs will be stored in '{result['target_bucket']}'"


def get_bucket_tags(bucket: str) -> str:
    """Get bucket tags including data classification.

    Parameters:
    - bucket: Name of the S3 bucket
    """
    bucket_state.log_tool_call("get_bucket_tags", {"bucket": bucket})
    result = bucket_state.get_bucket_tags(bucket)

    if "error" in result:
        return f"Error: {result['error']}"

    tags_str = "\n".join([f"- {k}: {v}" for k, v in result['tags'].items()])
    return f"Tags for bucket '{bucket}':\n{tags_str}"


def assess_data_exposure(bucket: str, start_date: str, end_date: str) -> str:
    """Assess scope of data exposure during time period.

    Parameters:
    - bucket: Name of the S3 bucket
    - start_date: Start of exposure period (ISO format)
    - end_date: End of exposure period (ISO format)
    """
    bucket_state.log_tool_call("assess_data_exposure", {"bucket": bucket, "start_date": start_date, "end_date": end_date})
    result = bucket_state.assess_data_exposure(bucket, start_date, end_date)

    if "error" in result:
        return f"Error: {result['error']}"

    findings = result['findings']
    compliance = result['compliance_impact']

    return f"""Data exposure assessment for '{bucket}':

Exposure Period: {result['exposure_period']['start']} to {result['exposure_period']['end']}

Findings:
- Access logs available: {findings['access_logs_available']}
- CloudTrail logs available: {findings['cloudtrail_logs_available']}
- Confirmed data access: {findings['confirmed_data_access']}
- Recommendation: {findings['recommendation']}

Severity: {result['severity']}

Compliance Impact:
- HIPAA: {compliance['HIPAA']}
- SOC2: {compliance['SOC2']}
- GDPR: {compliance['GDPR']}"""


def check_application_dependencies(bucket: str) -> str:
    """Check what applications depend on this bucket.

    Parameters:
    - bucket: Name of the S3 bucket
    """
    bucket_state.log_tool_call("check_application_dependencies", {"bucket": bucket})
    result = bucket_state.get_application_dependencies(bucket)

    if "error" in result:
        return f"Error: {result['error']}"

    if not result['dependencies']:
        return f"No application dependencies found for bucket '{bucket}'"

    deps_str = []
    for dep in result['dependencies']:
        deps_str.append(f"""
Service: {dep['name']}
- Access pattern: {dep['access_pattern']}
- Required permissions: {', '.join(dep['required_permissions'])}
- IAM role: {dep['iam_role']}""")

    return f"Application dependencies for bucket '{bucket}':\n" + "\n".join(deps_str)


def check_compliance_requirements(data_classification: str) -> str:
    """Get compliance requirements for data classification type.

    Parameters:
    - data_classification: Type of data (e.g., PHI, PII, PCI)
    """
    bucket_state.log_tool_call("check_compliance_requirements", {"data_classification": data_classification})
    requirements = {
        "PHI": {
            "frameworks": ["HIPAA", "SOC2"],
            "requirements": {
                "HIPAA": {
                    "access_controls": "Required - limit access to authorized personnel only",
                    "audit_logging": "Required - all access must be logged",
                    "breach_notification": "Required if PHI exposed for >500 records",
                    "encryption": "Required in transit and at rest"
                },
                "SOC2": {
                    "access_monitoring": "Continuous monitoring required",
                    "change_management": "All changes must be logged and reviewed",
                    "incident_response": "Documented process required"
                }
            }
        }
    }

    if data_classification not in requirements:
        return f"No compliance requirements found for data classification '{data_classification}'"

    reqs = requirements[data_classification]
    frameworks = ", ".join(reqs['frameworks'])

    details = []
    for framework, rules in reqs['requirements'].items():
        details.append(f"\n{framework}:")
        for key, value in rules.items():
            details.append(f"  - {key}: {value}")

    return f"Compliance requirements for {data_classification} data:\nFrameworks: {frameworks}\n{''.join(details)}"


def log_security_incident(
    bucket: str,
    incident_type: str,
    severity: str,
    exposure_details: str,
    remediation_actions: str
) -> str:
    """Log security incident with full details.

    Parameters:
    - bucket: Affected bucket name
    - incident_type: Type of incident (e.g., 'public_access_exposure')
    - severity: Severity level (LOW, MEDIUM, HIGH, CRITICAL)
    - exposure_details: Details about what was exposed
    - remediation_actions: Actions taken to remediate
    """
    bucket_state.log_tool_call("log_security_incident", {"bucket": bucket, "incident_type": incident_type, "severity": severity})
    from datetime import datetime

    incident_log = {
        "timestamp": datetime.now().isoformat(),
        "bucket": bucket,
        "incident_type": incident_type,
        "severity": severity,
        "exposure_details": exposure_details,
        "remediation_actions": remediation_actions
    }

    # In real scenario, would write to incident tracking system
    return f"""Security incident logged:
- Incident ID: SEC-{datetime.now().strftime('%Y%m%d-%H%M%S')}
- Bucket: {bucket}
- Type: {incident_type}
- Severity: {severity}
- Exposure: {exposure_details}
- Remediation: {remediation_actions}
- Logged at: {incident_log['timestamp']}"""


def notify_security_team(message: str, severity: str = "MEDIUM") -> str:
    """Send notification to security team.

    Parameters:
    - message: Notification message
    - severity: Severity level (LOW, MEDIUM, HIGH, CRITICAL)
    """
    bucket_state.log_tool_call("notify_security_team", {"message": message, "severity": severity})
    # In real scenario, would send email/Slack/PagerDuty alert
    return f"Security team notified (Severity: {severity}):\n{message}"


def verify_authorized_access(bucket: str, iam_roles: str) -> str:
    """Verify that authorized IAM roles can still access the bucket.

    Parameters:
    - bucket: Name of the S3 bucket
    - iam_roles: Comma-separated list of IAM role ARNs that should have access
    """
    bucket_state.log_tool_call("verify_authorized_access", {"bucket": bucket, "iam_roles": iam_roles})
    # Convert comma-separated string to list
    if isinstance(iam_roles, str):
        iam_roles = [role.strip() for role in iam_roles.split(',')]
    elif not isinstance(iam_roles, list):
        iam_roles = [iam_roles]
    bucket_info = bucket_state.get_bucket(bucket)
    if "error" in bucket_info:
        return f"Error: {bucket_info['error']}"

    policy = bucket_info.get("policy", {})

    # Check if roles are explicitly allowed in policy
    allowed_roles = []
    denied_roles = []

    for statement in policy.get("Statement", []):
        principal = statement.get("Principal", {})
        effect = statement.get("Effect")

        # Check for blanket deny (Deny * with no condition, or Deny * on all actions)
        if effect == "Deny" and principal == "*":
            # If there's a Condition, it's conditional deny (OK)
            # If Action is not s3:*, it's limited deny (OK)
            has_condition = bool(statement.get("Condition"))
            actions = statement.get("Action", [])
            if isinstance(actions, str):
                actions = [actions]

            # Only warn if it's a true blanket deny (no condition, blocks all S3 actions)
            if not has_condition and "s3:*" in actions:
                return f"WARNING: Current policy denies ALL access. Authorized IAM roles will be blocked!"

        if effect == "Allow" and isinstance(principal, dict):
            aws_principal = principal.get("AWS", [])
            if isinstance(aws_principal, str):
                aws_principal = [aws_principal]
            allowed_roles.extend(aws_principal)

    results = []
    for role in iam_roles:
        if role in allowed_roles:
            results.append(f"✓ {role}: Access granted")
        else:
            results.append(f"✗ {role}: Access denied")
            denied_roles.append(role)

    if denied_roles:
        return f"Access verification FAILED:\n" + "\n".join(results) + f"\n\nWARNING: {len(denied_roles)} authorized role(s) will lose access!"

    return f"Access verification PASSED:\n" + "\n".join(results)


# Tool registration helper
def register_security_tools(tool_registry):
    """Register all security tools."""
    tools = [
        Tool(name="get_bucket_policy", function=get_bucket_policy),
        Tool(name="update_bucket_policy", function=update_bucket_policy),
        Tool(name="check_bucket_public_access", function=check_bucket_public_access),
        Tool(name="enable_versioning", function=enable_versioning),
        Tool(name="enable_access_logging", function=enable_access_logging),
        Tool(name="get_bucket_tags", function=get_bucket_tags),
        Tool(name="assess_data_exposure", function=assess_data_exposure),
        Tool(name="check_application_dependencies", function=check_application_dependencies),
        Tool(name="check_compliance_requirements", function=check_compliance_requirements),
        Tool(name="log_security_incident", function=log_security_incident),
        Tool(name="notify_security_team", function=notify_security_team),
        Tool(name="verify_authorized_access", function=verify_authorized_access),
    ]

    for tool in tools:
        tool_registry.register_tool(tool)

    return tool_registry
