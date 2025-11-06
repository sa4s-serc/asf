"""
Golden labels for Scenario 2 memory evaluation.

Provides the reference memories that should be retrieved for specific query
types so evaluators can compute precision/recall style metrics.
"""

from typing import Dict, List, Set

from nltk.translate.bleu_score import SmoothingFunction, sentence_bleu
from sklearn.metrics import precision_recall_fscore_support


SEEDED_MEMORIES = {
    "policies": [
        "Company policy: All PHI (Protected Health Information) must be encrypted at rest and in transit",
        "Company policy: PHI access limited to authorized personnel only",
        "Company policy: All data buckets containing PHI must have versioning enabled",
        "Company policy: All PHI storage must have access logging enabled for audit purposes",
        "Security policy: All security incidents must be logged with full details including timeline, actions, and impact",
        "Security policy: Conduct root cause analysis within 24 hours of incident detection",
    ],
    "incident_response": [
        "Security incident response step 1: Contain the threat immediately",
        "Security incident response step 2: Assess the scope of exposure",
        "Security incident response step 3: Preserve evidence before making changes",
        "Security incident response step 4: Notify relevant stakeholders",
    ],
    "compliance": [
        "HIPAA compliance requirement: Access controls required for all PHI data",
        "HIPAA compliance requirement: Audit logging required for all PHI access",
        "HIPAA compliance requirement: Breach notification required if PHI exposed for more than 500 records",
        "HIPAA compliance requirement: Encryption required in transit and at rest for PHI",
        "SOC2 compliance requirement: Continuous access monitoring required",
        "SOC2 compliance requirement: All changes must be logged and reviewed through change management process",
        "SOC2 compliance requirement: Documented incident response process required",
    ],
    "metadata": {
        "patient-data-backup": "Bucket patient-data-backup contains PHI data classified as production environment and is subject to HIPAA and SOC2 compliance requirements",
        "patient-data-backup-details": "Bucket patient-data-backup is in the Engineering department, stores 1.2TB encrypted patient backups, and requires versioning plus access logging",
    },
    "dependencies": [
        "Application dependency: backup_service accesses patient-data-backup bucket daily at 2 AM UTC for automated backups",
        "Application dependency: backup_service requires s3:PutObject and s3:GetObject permissions on patient-data-backup",
        "Application dependency: backup_service uses IAM role arn:aws:iam::123456789:role/BackupServiceRole",
        "Application dependency: disaster_recovery service accesses patient-data-backup bucket on-demand during DR drills",
        "Application dependency: disaster_recovery requires s3:GetObject and s3:ListBucket permissions on patient-data-backup",
        "Application dependency: disaster_recovery uses IAM role arn:aws:iam::123456789:role/DRServiceRole",
    ],
}


def get_expected_retrieval(query: str) -> Dict:
    """Return expected memories for a given query."""
    query_lower = query.lower()

    result = {
        "expected_categories": [],
        "expected_memories": [],
        "expected_ids": [],
        "relevance_keywords": [],
    }

    def _extend(items: List[str]):
        result["expected_memories"].extend(items)
        result["expected_ids"].extend(items)

    if any(keyword in query_lower for keyword in ["policy", "policies", "logging", "versioning"]):
        result["expected_categories"].append("policy")
        _extend(SEEDED_MEMORIES["policies"])
        result["relevance_keywords"].extend(["policy", "logging", "versioning"])

    if any(keyword in query_lower for keyword in ["hipaa", "soc2", "compliance", "breach"]):
        result["expected_categories"].append("compliance")
        _extend(SEEDED_MEMORIES["compliance"])
        result["relevance_keywords"].extend(["hipaa", "soc2", "compliance"])

    if any(keyword in query_lower for keyword in ["incident", "preserve evidence", "notify"]):
        result["expected_categories"].append("incident_response")
        _extend(SEEDED_MEMORIES["incident_response"])
        result["relevance_keywords"].extend(["incident", "evidence", "notify"])

    if "patient-data-backup" in query_lower or "bucket" in query_lower:
        result["expected_categories"].append("metadata")
        _extend(list(SEEDED_MEMORIES["metadata"].values()))
        result["relevance_keywords"].extend(["patient-data-backup", "classification", "phi"])

    if any(keyword in query_lower for keyword in ["dependency", "backup", "drservice", "iam role", "drservice", "dr service", "backupservice"]):
        result["expected_categories"].append("dependency")
        _extend(SEEDED_MEMORIES["dependencies"])
        result["relevance_keywords"].extend(["dependency", "backup", "dr", "iam role"])

    # Remove duplicates while preserving order
    result["expected_categories"] = list(dict.fromkeys(result["expected_categories"]))
    result["expected_memories"] = list(dict.fromkeys(result["expected_memories"]))
    result["expected_ids"] = list(dict.fromkeys(result["expected_ids"]))

    return result


def calculate_retrieval_metrics(query: str, retrieved_memories: list) -> dict:
    """Calculate precision/recall metrics for a retrieval."""
    expected = get_expected_retrieval(query)
    expected_ids: Set[str] = set(expected["expected_ids"])
    retrieved_ids: Set[str] = {
        memory.get("canonical_id") or memory.get("memory")
        for memory in retrieved_memories
        if memory.get("memory")
    }
    retrieved_texts: Set[str] = {memory["memory"] for memory in retrieved_memories if memory.get("memory")}

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
            "expected_ids": [],
            "retrieved_ids": [],
            "retrieved_items": [],
            "matched_ids": [],
            "matched_items": [],
        }

    true_positive_ids = expected_ids & retrieved_ids
    relevant_retrieved_count = len(true_positive_ids)

    all_ids = sorted(expected_ids | retrieved_ids)
    y_true = [1 if item in expected_ids else 0 for item in all_ids]
    y_pred = [1 if item in retrieved_ids else 0 for item in all_ids]

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        average="binary",
        zero_division=0,
    )

    if expected["expected_memories"]:
        smoothing = SmoothingFunction().method1
        reference_tokens = [memory.split() for memory in expected["expected_memories"]]
        hypothesis_tokens = " ".join(retrieved_texts).split() if retrieved_texts else []
        bleu = sentence_bleu(
            reference_tokens,
            hypothesis_tokens,
            weights=(1.0, 0, 0, 0),
            smoothing_function=smoothing,
        ) if hypothesis_tokens else 0.0
    else:
        bleu = 1.0 if retrieved_count == 0 else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "bleu": bleu,
        "expected_count": expected_count,
        "retrieved_count": retrieved_count,
        "relevant_retrieved_count": relevant_retrieved_count,
        "expected_items": sorted(expected["expected_memories"]),
        "expected_ids": sorted(expected_ids),
        "retrieved_ids": sorted(retrieved_ids),
        "retrieved_items": sorted(retrieved_texts),
        "matched_ids": sorted(true_positive_ids),
        "matched_items": sorted({memory for memory in retrieved_texts if memory in expected_ids}),
    }
