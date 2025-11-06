"""
Scenario 3 memory gold labels.

Provides the reference memories that should be retrieved for different query
types so we can compute precision/recall style metrics consistent with the
other scenarios.
"""

from __future__ import annotations

from typing import Dict, List, Set

from nltk.translate.bleu_score import SmoothingFunction, sentence_bleu
from sklearn.metrics import precision_recall_fscore_support

# --------------------------------------------------------------------------- #
# Ground-truth memories (mirrors the seeding in environment/memory_tools.py)
# --------------------------------------------------------------------------- #

SEEDED_MEMORIES = {
    "baseline": [
        "payment-service baseline performance: avg_response_time=1.5s, p95_response_time=2.1s, p99_response_time=3.2s, error_rate=0.8%, cpu_avg=45%, memory_avg=65%, throughput=1000 requests/minute",
        "payment-service performance thresholds: response_time degradation > 30% triggers alert, error_rate > 2% triggers investigation, CPU > 80% requires analysis",
        "prod-payment-db baseline metrics: cpu_utilization=30-40%, active_connections=40-60, connection_utilization=8-12%, query_latency_avg=50ms",
    ],
    "change": [
        "Change CHG-2024-0115-001 at 2024-01-15T08:15:00Z: security_group_modification on sg-abc123 by admin@company.com - Modified inbound rules for RDS security group, changed from allowing 10.0.0.0/16 (entire VPC) to only allowing 10.0.1.0/24 (admin subnet) on port 5432",
        "Security group sg-abc123 change details: BEFORE allowed port 5432 from 10.0.0.0/16 (entire VPC including app tier), AFTER allows port 5432 from only 10.0.1.0/24 (admin subnet only), reason given: 'Tighten security - limit database access to specific subnet'",
        "Change CHG-2024-0110-003 at 2024-01-10T14:00:00Z: code_deployment of payment-service v2.3.1 by ci-cd-pipeline - Routine bug fixes for payment validation and updated logging configuration, no performance changes expected",
        "Change CHG-2024-0108-007 at 2024-01-08T16:30:00Z: infrastructure_scaling of payment-service by devops@company.com - Scaled from 2 to 3 instances (added i-abc125) for proactive capacity increase",
        "Timeline of recent changes: Jan 8 (scaling), Jan 10 (code deployment v2.3.1), Jan 15 08:15 AM (security group modification) - most recent change was security configuration",
    ],
    "topology": [
        "VPC vpc-main network topology: CIDR 10.0.0.0/16 contains three subnets - admin subnet 10.0.1.0/24 (bastion, VPN), app_tier subnet 10.0.2.0/24 (application servers), database_tier subnet 10.0.3.0/24 (databases)",
        "Subnet details for payment-service: application instances run in app_tier subnet 10.0.2.0/24 in availability zone us-east-1b, uses public route table for internet access",
        "Subnet details for prod-payment-db: database runs in database_tier subnet 10.0.3.0/24 in availability zone us-east-1c, uses private route table, no direct internet access",
        "Admin subnet 10.0.1.0/24: contains bastion hosts and VPN gateway in availability zone us-east-1a, uses public route table, typically used for administrative access to resources",
        "Network path payment-service to database: source 10.0.2.0/24 (app_tier) must reach destination 10.0.3.0/24 (database_tier) on port 5432, requires security group sg-abc123 to allow 10.0.2.0/24 as source",
        "Security group to subnet mapping: sg-app-tier protects resources in 10.0.2.0/24 (payment-service instances), sg-abc123 protects resources in 10.0.3.0/24 (prod-payment-db)",
    ],
    "policy": [
        "Performance troubleshooting workflow: Step 1 - Check for recent configuration changes in last 24 hours, Step 2 - Verify network connectivity between components, Step 3 - Analyze resource utilization metrics, Step 4 - Review application logs for error patterns, Step 5 - Correlate timing of symptoms with change events",
        "Scaling policy: Only scale infrastructure AFTER ruling out configuration issues, network problems, and application bugs. Scaling adds cost without fixing root causes. Always identify root cause before scaling.",
        "Configuration change correlation rule: If symptoms started within 30 minutes of a configuration change, investigate that change first as likely root cause before exploring other hypotheses",
        "Database connectivity troubleshooting: When applications show DatabaseConnectionTimeout errors, check: 1) Security group rules allow source to destination, 2) Network ACLs permit traffic, 3) Database is running and accepting connections, 4) Connection pooling configuration is correct",
        "Multi-domain issue escalation policy: If performance issue involves multiple domains (performance + security + network), coordinate between specialized agents rather than acting in isolation. Performance agent should consult security agent for configuration issues.",
        "Root cause analysis requirements: Must identify root cause (not just symptoms) before remediation, must correlate timing of symptoms with events, must verify hypothesis with targeted checks, must document causal chain from root cause to observed symptoms",
    ],
    "incident_response": [
        "Incident response workflow for performance degradation: 1) Gather symptoms from monitoring, 2) Check recent changes, 3) Perform temporal correlation analysis (symptom time vs change time), 4) Form hypothesis about root cause, 5) Validate hypothesis with targeted tests, 6) Apply targeted fix (not generic scaling), 7) Verify metrics return to baseline",
        "Temporal correlation analysis: If symptom onset is within 5-10 minutes of a configuration change, high probability of causal relationship. Changes propagate within 1-5 minutes in AWS. Investigate that change as primary suspect.",
        "Error pattern analysis: DatabaseConnectionTimeout errors indicate network connectivity or security group issues, not application load. Check security groups and network path before assuming resource constraints.",
        "CPU spike investigation: If CPU increases but database connectivity is failing, CPU spike is likely symptom (retry overhead) not cause. Look for connection errors before concluding CPU is the problem.",
        "Multi-agent coordination for RCA: Root Cause Analysis agent should gather findings from Performance agent (metrics) and Security agent (configuration), correlate findings, identify causal chain, then coordinate targeted remediation",
    ],
    "infrastructure": [
        "payment-service infrastructure: runs on 3 m5.xlarge EC2 instances (i-abc123, i-abc124, i-abc125) in subnet 10.0.2.0/24, uses security group sg-app-tier, deployed in us-east-1",
        "payment-service depends on prod-payment-db PostgreSQL database at endpoint prod-payment-db.cluster-xyz.us-east-1.rds.amazonaws.com port 5432 for all transaction processing",
        "prod-payment-db configuration: PostgreSQL RDS instance in subnet 10.0.3.0/24 (database_tier), protected by security group sg-abc123, handles all payment transaction data",
        "payment-service security group sg-app-tier: allows inbound HTTP (80) and HTTPS (443) from anywhere, allows all outbound traffic, located in vpc-main",
        "prod-payment-db security group sg-abc123: controls database access via inbound rules on port 5432, critical for database connectivity, located in vpc-main",
        "payment-service uses connection pooling with 3 retry attempts per database operation, timeout=10 seconds per attempt, total operation timeout=30 seconds",
    ],
    "failure_pattern": [
        "Common failure pattern: Security group rules overly restrictive after security hardening efforts. Symptom: sudden connectivity loss. Root cause: security group rule removed legitimate source CIDR. Fix: add correct source CIDR to security group.",
        "Anti-pattern: Scaling in response to high CPU without checking error logs. If errors show connection failures, scaling adds cost but does not fix connectivity issues. New instances have same connection problems.",
        "Symptom vs root cause distinction: High CPU, slow response times, elevated error rates are symptoms. Root cause is the underlying issue causing symptoms (e.g., security group blocking database access causes connection retries which cause CPU spike).",
    ],
}


def _extend(result: Dict[str, List[str]], category: str) -> None:
    items = SEEDED_MEMORIES.get(category)
    if not items:
        return
    result["expected_categories"].append(category)
    result["expected_memories"].extend(items)
    result["expected_ids"].extend(items)


def get_expected_retrieval(query: str) -> Dict[str, List[str]]:
    query_lower = query.lower()
    result = {
        "expected_categories": [],
        "expected_memories": [],
        "expected_ids": [],
    }

    if any(keyword in query_lower for keyword in ["baseline", "performance", "avg_response"]):
        _extend(result, "baseline")

    if any(keyword in query_lower for keyword in ["recent", "change", "modified", "security group", "sg-"]):
        _extend(result, "change")
        _extend(result, "infrastructure")

    if any(keyword in query_lower for keyword in ["network", "subnet", "cidr", "topology"]):
        _extend(result, "topology")

    if any(keyword in query_lower for keyword in ["policy", "workflow", "troubleshoot", "guardrail"]):
        _extend(result, "policy")

    if any(keyword in query_lower for keyword in ["incident", "correlat", "temporal"]):
        _extend(result, "incident_response")

    if any(keyword in query_lower for keyword in ["dependency", "database", "endpoint", "connection"]):
        _extend(result, "infrastructure")

    if any(keyword in query_lower for keyword in ["failure", "symptom", "cpu spike", "anti-pattern"]):
        _extend(result, "failure_pattern")

    # If nothing matched, default to infrastructure context for payment-service queries
    if not result["expected_categories"] and "payment-service" in query_lower:
        _extend(result, "infrastructure")
        _extend(result, "baseline")

    # Deduplicate
    result["expected_categories"] = list(dict.fromkeys(result["expected_categories"]))
    result["expected_memories"] = list(dict.fromkeys(result["expected_memories"]))
    result["expected_ids"] = list(dict.fromkeys(result["expected_ids"]))

    return result


def calculate_retrieval_metrics(query: str, retrieved_memories: List[Dict[str, str]]) -> Dict[str, float]:
    expected = get_expected_retrieval(query)
    expected_memories: Set[str] = set(expected["expected_memories"])
    expected_ids: Set[str] = set(expected["expected_ids"])

    retrieved_ids: Set[str] = {
        item.get("canonical_id") or item.get("memory")
        for item in retrieved_memories
        if item.get("memory")
    }
    retrieved_texts: Set[str] = {
        item["memory"] for item in retrieved_memories if item.get("memory")
    }

    expected_count = len(expected_ids)
    retrieved_count = len(retrieved_ids)

    if expected_count == 0 and retrieved_count == 0:
        return {
            "precision": 1.0,
            "recall": 1.0,
            "f1": 1.0,
            "bleu": 1.0,
            "expected_count": 0,
            "retrieved_count": 0,
            "relevant_retrieved_count": 0,
            "expected_items": [],
            "retrieved_items": [],
            "matched_items": [],
        }

    true_positive_ids = expected_ids & retrieved_ids
    true_positive_texts = expected_memories & retrieved_texts

    all_ids = sorted(expected_ids | retrieved_ids)
    y_true = [1 if identifier in expected_ids else 0 for identifier in all_ids]
    y_pred = [1 if identifier in retrieved_ids else 0 for identifier in all_ids]

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        average="binary",
        zero_division=0,
    )

    if expected_memories:
        smoothing = SmoothingFunction().method1
        references = [memory.split() for memory in expected_memories]
        hypothesis = " ".join(retrieved_texts).split() if retrieved_texts else []
        bleu = sentence_bleu(
            references,
            hypothesis,
            weights=(1.0, 0, 0, 0),
            smoothing_function=smoothing,
        ) if hypothesis else 0.0
    else:
        bleu = 1.0 if retrieved_count == 0 else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "bleu": bleu,
        "expected_count": expected_count,
        "retrieved_count": retrieved_count,
        "relevant_retrieved_count": len(true_positive_ids),
        "expected_items": sorted(expected_memories),
        "retrieved_items": sorted(retrieved_texts),
        "matched_items": sorted(true_positive_texts),
    }
