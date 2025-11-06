"""
Gold Labels for Memory Retrieval Evaluation

Defines what memories SHOULD be retrieved for different query types.
This serves as ground truth for evaluating retrieval accuracy.
"""

from typing import Dict, List, Set

from nltk.translate.bleu_score import SmoothingFunction, sentence_bleu
from sklearn.metrics import precision_recall_fscore_support


# All seeded memories (ground truth)
SEEDED_MEMORIES = {
    "policies": [
        "Company cost optimization policy: Always prioritize non-production environments first when reducing costs",
        "Company policy: Production database changes require Change Advisory Board (CAB) approval before execution",
        "Company policy: All production infrastructure changes must go through formal change management process"
    ],
    "metadata": {
        "prod-db-primary": "prod-db-primary: production environment, high criticality, 99.99% uptime SLA requirement, db.r5.2xlarge instance type, $1200/month cost",
        "prod-db-replica": "prod-db-replica: production environment, high criticality, 99.99% uptime SLA requirement, db.r5.2xlarge instance type, $1200/month cost",
        "dev-db-1": "dev-db-1: development environment, low criticality, no uptime SLA, db.t3.medium instance type, $150/month cost",
        "dev-db-2": "dev-db-2: development environment, low criticality, no uptime SLA, db.t3.medium instance type, $150/month cost",
        "dev-db-3": "dev-db-3: development environment, low criticality, no uptime SLA, db.t3.medium instance type, $150/month cost"
    },
    "dependencies": [
        "prod-db-primary depends on prod-db-replica for high availability and automatic failover capability",
        "prod-db-replica serves as read replica for prod-db-primary, handling read traffic to distribute load",
        "prod-db-replica acts as failover target for prod-db-primary in case of primary instance failure",
        "Terminating prod-db-replica would eliminate high availability for prod-db-primary and overload it with all read queries",
        "Development instances (dev-db-1, dev-db-2, dev-db-3) are independent with no production dependencies"
    ]
}


def get_expected_retrieval(query: str) -> dict:
    """
    Given a query, return what SHOULD be retrieved.

    Returns:
        {
            "expected_categories": ["policy", "metadata", "dependency"],
            "expected_memories": [...],
            "relevance_keywords": [...]
        }
    """
    query_lower = query.lower()

    result = {
        "expected_categories": [],
        "expected_memories": [],
        "expected_ids": [],
        "relevance_keywords": []
    }

    # Policy queries
    if any(keyword in query_lower for keyword in ["policy", "policies", "rule", "guidelines"]):
        result["expected_categories"].append("policy")
        result["expected_memories"].extend(SEEDED_MEMORIES["policies"])
        result["expected_ids"].extend(SEEDED_MEMORIES["policies"])
        result["relevance_keywords"].extend(["policy", "approval", "change management", "non-production"])

    # Instance-specific metadata queries
    for instance_id in ["prod-db-primary", "prod-db-replica", "dev-db-1", "dev-db-2", "dev-db-3"]:
        if instance_id in query_lower:
            result["expected_categories"].append("metadata")
            memory_text = SEEDED_MEMORIES["metadata"][instance_id]
            result["expected_memories"].append(memory_text)
            result["expected_ids"].append(memory_text)
            result["relevance_keywords"].extend([instance_id, "environment", "criticality"])

            # If querying prod instances, dependencies are also relevant
            if "prod" in instance_id:
                result["expected_categories"].append("dependency")
                # Add relevant dependencies
                for dep in SEEDED_MEMORIES["dependencies"]:
                    if instance_id in dep:
                        result["expected_memories"].append(dep)
                        result["expected_ids"].append(dep)
                result["relevance_keywords"].extend(["depends", "replica", "failover"])

    # General metadata queries
    if any(keyword in query_lower for keyword in ["metadata", "environment", "criticality", "cost"]) and not any(inst in query_lower for inst in ["prod-db", "dev-db"]):
        result["expected_categories"].append("metadata")
        metadata_values = list(SEEDED_MEMORIES["metadata"].values())
        result["expected_memories"].extend(metadata_values)
        result["expected_ids"].extend(metadata_values)
        result["relevance_keywords"].extend(["environment", "criticality", "production", "development"])

    # Dependency queries
    if any(keyword in query_lower for keyword in ["depend", "relationship", "connection", "impact"]):
        result["expected_categories"].append("dependency")
        result["expected_memories"].extend(SEEDED_MEMORIES["dependencies"])
        result["expected_ids"].extend(SEEDED_MEMORIES["dependencies"])
        result["relevance_keywords"].extend(["depends", "replica", "failover", "independent"])

    # Remove duplicates
    result["expected_categories"] = list(set(result["expected_categories"]))
    result["expected_memories"] = list(set(result["expected_memories"]))
    result["expected_ids"] = list(set(result["expected_ids"]))

    return result


def calculate_retrieval_metrics(query: str, retrieved_memories: list) -> dict:
    """
    Calculate retrieval precision and recall for a query using text similarity metrics.

    Parameters:
        query: The query string
        retrieved_memories: List of dicts with "memory" and "category" keys

    Returns:
        {
            "precision": float,
            "recall": float,
            "f1": float,
            "bleu": float,
            "expected_count": int,
            "retrieved_count": int,
            "relevant_retrieved_count": int
        }
    """
    expected = get_expected_retrieval(query)
    expected_memories: Set[str] = set(expected["expected_memories"])
    expected_ids: Set[str] = set(expected["expected_ids"])
    retrieved_ids: Set[str] = {
        m.get("canonical_id") or m.get("memory")
        for m in retrieved_memories
        if m.get("memory")
    }
    retrieved_texts: Set[str] = {m["memory"] for m in retrieved_memories if m.get("memory")}

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
            "relevant_retrieved_count": 0
        }

    true_positive_ids = expected_ids & retrieved_ids
    true_positive_texts = expected_memories & retrieved_texts
    relevant_retrieved_count = len(true_positive_ids)

    # Build label vectors for precision/recall scoring using sklearn when available
    all_ids = sorted(expected_ids | retrieved_ids)
    y_true = [1 if item in expected_ids else 0 for item in all_ids]
    y_pred = [1 if item in retrieved_ids else 0 for item in all_ids]

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        average="binary",
        zero_division=0,
    )

    # Compute BLEU-1 using NLTK when available
    if expected_memories:
        smoothing = SmoothingFunction().method1
        reference_tokens = [memory.split() for memory in expected_memories]
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
        "expected_items": sorted(expected_memories),
        "expected_ids": sorted(expected_ids),
        "retrieved_ids": sorted(retrieved_ids),
        "retrieved_items": sorted(retrieved_texts),
        "matched_ids": sorted(true_positive_ids),
        "matched_items": sorted(true_positive_texts),
    }
