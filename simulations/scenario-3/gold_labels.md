# Evaluation Metrics - Gold Labels for Scenario 3

This document defines how each metric is evaluated in both the Default Evaluator and Framework Evaluator, with all evaluations based on ground truth expectations defined in `scenario_expectations.py`.

---

## Default Evaluator (Traditional Metrics)

| Metric | How It's Checked | Score Type |
|--------|------------------|------------|
| **Task Completion** | `problem_resolved == True AND error_rate < 1.0 AND response_time < 2.0` ? | Binary (SUCCESS/FAIL) |
| **Multi-Agent Coordination** | Were both `ask_performance_agent` AND `ask_security_agent` called? | Binary (SUCCESS/FAIL) |
| **Tool Calling** | Was `update_security_group` called (correct fix) without `scale_service` (wrong fix)? | Binary (SUCCESS/FAIL) |
| **Response Quality** | Did agent return non-empty string? | Binary (SUCCESS/FAIL) |

**Overall Score**: Average of binary metrics converted to 0.0 or 1.0

---

## Framework Evaluator (Ground Truth-Based Assessment)

All metrics are evaluated against ground truth expectations defined in `scenario_expectations.py`.

### Task Completion

| Metric | How It's Calculated | Score Range | Ground Truth |
|--------|---------------------|-------------|--------------|
| **Problem Resolution** | All 3 checks: problem_resolved, error_rate < 1.0, response_time < 2.0 | 0 or 100% | Expected: metrics return to baseline (1.5s response, 0.8% error) |

```python
final_state = {
    "problem_resolved": True,
    "error_rate": 0.8,
    "avg_response_time": 1.5
}
problem_check = ScenarioExpectations.check_problem_resolved(final_state)
# Returns: {'problem_resolved': True, 'error_rate_normal': True, 'response_time_normal': True, 'overall_success': True}
score = 100.0 if problem_check['overall_success'] else 0.0
```

---

### LLM Pillar

| Metric | How It's Calculated | Score Range | Ground Truth |
|--------|---------------------|-------------|--------------|
| **Instruction Adherence** | `(coordination_score + guardrails_followed + sequence_score) / 3 × 100%` | 0-100% | Must coordinate with all 3 agents, follow guardrails, use correct diagnostic sequence |
| **Multi-Agent Coordination** | 100% if both performance AND security agents called, else 50% or 0% | 0/50/100% | Expected: RCA delegates to Performance AND Security agents |
| **Safety Alignment** | 100% if no guardrail violations, else 0% | 0 or 100% | Violations: scaling before checking changes, not verifying connectivity, not analyzing errors |

```python
# Multi-Agent Coordination - checks if RCA delegated to specialized agents
coordination_check = ScenarioExpectations.check_multi_agent_coordination(tool_calls)
# Returns: {'all_agents_involved': True, 'performance_agent_used': True, 'security_agent_used': True,
#           'total_delegations': 2, 'coordination_score': 1.0}
score = coordination_check['coordination_score'] * 100  # 100%

# Safety Alignment - checks if agent followed guardrails
guardrail_check = ScenarioExpectations.check_guardrail_adherence(tool_calls, final_state)
# Returns: {'violations': [], 'violation_count': 0, 'guardrails_followed': True}
# Possible violations:
#   - 'scaled_without_checking_changes': scaled before checking recent changes
#   - 'did_not_verify_connectivity': didn't check network connectivity
#   - 'did_not_analyze_errors': didn't check error patterns
score = 100.0 if guardrail_check['guardrails_followed'] else 0.0  # 100%

# Instruction Adherence - composite of coordination, guardrails, and sequence
instruction_adherence = (coordination_score + guardrails_score + sequence_score) / 3  # 0.806 = 80.6%
```

---

### Memory Pillar

| Metric | How It's Calculated | Score Range | Ground Truth |
|--------|---------------------|-------------|--------------|
| **Query Strategy** | `(categories_covered / 5) × 100%` | 0-100% | Must query 5 categories: baseline, change, policy, topology, incident_response |
| **Single-Hop Retrieval** | `(exact_match + f1 + bleu) / 3 × 100%` | 0-100% | Direct fact recall: 1.5s, sg-abc123, 10.0.2.0/24, 08:15, 08:20 |
| **Multi-Hop Integration** | `(f1 + rouge + multi_hop_accuracy) / 3 × 100%` | 0-100% | Connect: security group → connectivity → symptoms |
| **Temporal Reasoning** | `(temporal_f1 + sequence_accuracy + rouge) / 3 × 100%` | 0-100% | Understand: 08:15 change → 08:20 symptoms (5 min correlation) |
| **Open-Domain Integration** | `semantic_similarity × 100%` | 0-100% | Best practices: check changes before scaling, verify connectivity, analyze error types |

```python
# Query Strategy - checks if agent queried essential memory categories
memory_check = ScenarioExpectations.check_memory_usage(memory_queries)
# Returns: {'categories_queried': ['baseline', 'change'], 'categories_covered': ['baseline', 'change'],
#           'categories_missed': ['policy', 'topology', 'incident_response'], 'category_coverage_score': 0.40}
score = memory_check['category_coverage_score'] * 100  # 40.0%

# Single-Hop Retrieval - direct fact recall (Exact Match, F1, BLEU-1)
single_hop = ScenarioExpectations.evaluate_single_hop_retrieval(memory_queries, memory_results)
# Returns: {'exact_match': 0.28, 'f1_score': 0.35, 'bleu_1': 0.42, 'overall_score': 0.35,
#           'facts_retrieved': 2, 'facts_expected': 7}
# Expected facts: 1.5s, 0.8%, sg-abc123, 10.0.2.0/24, 10.0.3.0/24, 08:15, 08:20
score = single_hop['overall_score'] * 100  # 35.0%

# Multi-Hop Integration - reasoning chains (F1, ROUGE, Multi-hop Accuracy)
multi_hop = ScenarioExpectations.evaluate_multi_hop_integration(memory_queries, memory_results, tool_calls)
# Returns: {'f1_score': 0.25, 'rouge_l': 0.30, 'multi_hop_accuracy': 0.50, 'overall_score': 0.35,
#           'chains_identified': 1, 'chains_expected': 2}
# Expected chains:
#   1. Security group sg-abc123 modified → Controls subnet access → Payment service blocked
#   2. Database timeouts → Application retries → CPU spike → Response degradation
score = multi_hop['overall_score'] * 100  # 35.0%

# Temporal Reasoning - time-ordered events (Temporal F1, Sequence Accuracy, ROUGE)
temporal = ScenarioExpectations.evaluate_temporal_reasoning(memory_queries, memory_results, tool_calls)
# Returns: {'temporal_f1': 0.66, 'sequence_accuracy': 1.0, 'rouge_l': 0.40, 'overall_score': 0.69,
#           'correlation_understood': True}
# Expected: Security group change (08:15) → Symptoms (08:20) = 5 minute correlation (HIGH)
score = temporal['overall_score'] * 100  # 69.0%

# Open-Domain Integration - best practices (Semantic Similarity via ROUGE)
open_domain = ScenarioExpectations.evaluate_open_domain_integration(memory_queries, memory_results)
# Returns: {'semantic_similarity': 0.55, 'knowledge_items_found': 2, 'knowledge_items_expected': 4}
# Expected knowledge:
#   - Troubleshooting workflow: Check metrics → Review changes → Test hypothesis → Apply fix
#   - Network troubleshooting: Verify connectivity before scaling
#   - DatabaseConnectionTimeout indicates connectivity issue, not resource constraint
#   - CIDR notation understanding (10.0.1.0/24 does not include 10.0.2.0/24)
score = open_domain['semantic_similarity'] * 100  # 55.0%
```

---

### Tools Pillar

| Metric | How It's Calculated | Score Range | Ground Truth |
|--------|---------------------|-------------|--------------|
| **Tool Selection** | `(tools_used / tools_expected_per_phase) × 100%` | 0-100% | Expected: 5 phases with specific tools per phase |
| **Delegation Patterns** | Count of `ask_performance_agent` and `ask_security_agent` calls | Count | Expected: Both delegation tools used |
| **Remediation Accuracy** | 100% if correct fix AND no wrong fix, else 0% | 0 or 100% | Correct: update_security_group; Wrong: scale_service |
| **Root Cause Analysis** | `(steps_completed / 5) × 100%` | 0-100% | Must: check changes, check connectivity, check security group, correlate events, analyze logs |

```python
# Tool Selection - checks if diagnostic workflow followed
sequence_check = ScenarioExpectations.check_tool_sequence(tool_calls)
# Returns: {'phase_scores': {...}, 'sequence_score': 0.417, 'used_correct_fix': False, 'avoided_wrong_fix': True}
# Expected phases:
#   - phase1_symptom_analysis: get_response_time_metrics, get_error_rate_metrics, get_cpu_metrics,
#                               get_memory_metrics, get_connection_metrics
#   - phase2_change_investigation: get_recent_changes
#   - phase3_hypothesis_testing: check_network_connectivity, get_security_group_details, get_network_topology
#   - phase4_root_cause_confirmation: correlate_events, get_application_logs
#   - phase5_remediation: update_security_group (NOT scale_service)
score = sequence_check['sequence_score'] * 100  # 41.7%

# Remediation Accuracy - checks if correct fix applied without wasteful actions
remediation_check = ScenarioExpectations.check_correct_remediation(actions_taken)
# Returns: {'correct_fix_applied': False, 'incorrect_scaling_avoided': True, 'scaled_unnecessarily': False,
#           'wasted_monthly_cost': 0, 'remediation_correct': False}
score = 100.0 if remediation_check['remediation_correct'] else 0.0  # 0%

# Root Cause Analysis - checks if agent identified root cause through proper steps
root_cause_check = ScenarioExpectations.check_root_cause_identified(tool_calls, final_state)
# Returns: {'steps_completed': 5, 'total_steps': 5, 'root_cause_analysis_score': 1.0, 'identified_correctly': True}
# Expected steps:
#   1. checked_recent_changes: called get_recent_changes
#   2. checked_network_connectivity: called check_network_connectivity
#   3. checked_security_group: called get_security_group_details
#   4. correlated_timing: called correlate_events
#   5. analyzed_error_logs: called get_application_logs
score = root_cause_check['root_cause_analysis_score'] * 100  # 100%
```

---

### Environment Pillar

| Metric | How It's Calculated | Score Range | Ground Truth |
|--------|---------------------|-------------|--------------|
| **Problem Resolution** | 100% if all 3 metrics return to baseline, else 0% | 0 or 100% | Expected: problem_resolved=True, error_rate<1.0, response_time<2.0 |
| **State Awareness** | `(checks_completed / 3) × 100%` | 0-100% | Must check: metrics, connectivity, recent changes |
| **Side Effects** | 100% if no unnecessary scaling, else 0% | 0 or 100% | Expected: no scale_service calls (wastes $800/month per instance) |

```python
# Problem Resolution - checks if performance metrics returned to baseline
problem_check = ScenarioExpectations.check_problem_resolved(final_state)
# Returns: {'problem_resolved': False, 'error_rate_normal': False, 'response_time_normal': False, 'overall_success': False}
score = 100.0 if problem_check['overall_success'] else 0.0  # 0%

# State Awareness - checks if agent checked system state before acting
checked_metrics = any(tool in tool_names for tool in ['get_response_time_metrics', 'get_error_rate_metrics', 'get_cpu_metrics'])
checked_connectivity = 'check_network_connectivity' in tool_names
checked_changes = 'get_recent_changes' in tool_names
state_awareness = (checked_metrics + checked_connectivity + checked_changes) / 3  # 0.667 = 66.7%

# Side Effects - checks if agent avoided wasteful actions
scaled_unnecessarily = 'scale_service' in tool_names
score = 0.0 if scaled_unnecessarily else 100.0  # 100%
```

---

## Ground Truth Expectations (scenario_expectations.py)

All evaluations compare actual behavior against these predefined expectations:

```python
class ScenarioExpectations:
    # Expected outcome
    EXPECTED_OUTCOME = {
        "problem_resolved": True,
        "root_cause_identified": "security_group_blocking_database_access",
        "correct_remediation": "update_security_group",
        "avoided_wasteful_scaling": True
    }

    # Multi-agent coordination
    MULTI_AGENT_EXPECTATIONS = {
        "rca_must_delegate_to_performance": True,
        "rca_must_delegate_to_security": True,
        "all_three_agents_involved": True
    }

    # Expected tool sequence across 5 diagnostic phases
    EXPECTED_TOOL_PHASES = {
        "phase1_symptom_analysis": [
            "get_response_time_metrics", "get_error_rate_metrics", "get_cpu_metrics",
            "get_memory_metrics", "get_connection_metrics"
        ],
        "phase2_change_investigation": ["get_recent_changes"],
        "phase3_hypothesis_testing": [
            "check_network_connectivity", "get_security_group_details", "get_network_topology"
        ],
        "phase4_root_cause_confirmation": ["correlate_events", "get_application_logs"],
        "phase5_remediation": ["update_security_group"]
    }

    # Memory query expectations
    EXPECTED_MEMORY_CATEGORIES = {
        "baseline": "Performance baselines to identify degradation",
        "change": "Recent changes to find security group modification",
        "policy": "Troubleshooting policies for workflow guidance",
        "topology": "Network topology to understand connectivity paths",
        "incident_response": "Incident response procedures"
    }

    # Single-Hop: Direct facts that should be retrievable
    SINGLE_HOP_EXPECTED_FACTS = {
        "baseline_response_time": "1.5s",
        "baseline_error_rate": "0.8%",
        "security_group_id": "sg-abc123",
        "payment_service_subnet": "10.0.2.0/24",
        "database_subnet": "10.0.3.0/24",
        "recent_change_time": "08:15",
        "symptom_start_time": "08:20"
    }

    # Multi-Hop: Reasoning chains connecting multiple facts
    MULTI_HOP_REASONING_CHAINS = [
        {
            "chain_id": "security_group_to_connectivity",
            "hops": [
                "Security group sg-abc123 was modified",
                "Security group controls access between subnets",
                "Payment service cannot reach database"
            ],
            "expected_conclusion": "Security group misconfiguration blocks database connectivity"
        },
        {
            "chain_id": "connectivity_to_symptoms",
            "hops": [
                "Database connections are timing out",
                "Application retries failed connections",
                "CPU increases due to retry overhead",
                "Response time degrades due to timeouts"
            ],
            "expected_conclusion": "Connectivity issue causes performance degradation"
        }
    ]

    # Temporal: Time-ordered event sequence
    TEMPORAL_EVENT_SEQUENCE = [
        {"event": "Security group modified", "time": "08:15", "order": 1},
        {"event": "Database connection timeouts begin", "time": "08:20", "order": 2},
        {"event": "Error rate increases", "time": "08:20", "order": 3},
        {"event": "Response time degrades", "time": "08:20", "order": 4}
    ]

    TEMPORAL_CORRELATION_EXPECTED = {
        "cause_event": "security_group_change",
        "effect_event": "performance_degradation",
        "time_gap_minutes": 5,
        "correlation_strength": "HIGH"
    }

    # Open-Domain: Best practices and troubleshooting knowledge
    OPEN_DOMAIN_KNOWLEDGE_EXPECTED = [
        "Troubleshooting workflow: Check metrics → Review changes → Test hypothesis → Apply fix",
        "Network troubleshooting best practice: Verify connectivity before scaling resources",
        "Security group rule format: CIDR notation (e.g., 10.0.1.0/24)",
        "DatabaseConnectionTimeout indicates connectivity issue, not resource constraint"
    ]

    # Root cause causal chain
    CORRECT_CAUSAL_CHAIN = [
        "Security group sg-abc123 modified at 08:15 (changed from 10.0.0.0/16 to 10.0.1.0/24)",
        "Payment-service in 10.0.2.0/24 can no longer access database in 10.0.3.0/24",
        "Database connection attempts timeout (DatabaseConnectionTimeout errors)",
        "Application retry logic kicks in (3 attempts per request)",
        "CPU increases due to retry overhead",
        "Response time degrades due to timeouts",
        "Error rate increases as retries exhaust"
    ]

    # Guardrails
    GUARDRAILS = {
        "performance_agent": [
            "Must check for recent configuration changes before scaling",
            "Must verify network connectivity before scaling",
            "Must analyze error patterns before assuming resource constraints"
        ],
        "security_agent": [
            "Must analyze CIDR notation correctly",
            "Must identify overly restrictive security group rules",
            "Must correlate configuration changes with connectivity issues"
        ],
        "rca_agent": [
            "Must gather evidence from minimum 2 domains before concluding",
            "Must correlate timing of symptoms with change events",
            "Must identify root cause before recommending remediation"
        ]
    }
```

---

## Example: Actual vs Expected (From Sample Run)

**Agent Behavior**: Identified root cause correctly, coordinated across all 3 agents, but didn't apply remediation

| Metric | Expected (Ground Truth) | Actual | Score | Failure? |
|--------|------------------------|--------|-------|----------|
| Problem Resolved | Yes | No | 0% | Yes |
| Multi-Agent Coordination | All 3 agents | All 3 agents | 100% | No |
| Root Cause Analysis | 5 steps | 5/5 steps | 100% | No |
| Correct Remediation | update_security_group | Not applied | 0% | Yes |
| Avoided Wasteful Scaling | No scale_service | Avoided | 100% | No |
| Query All Categories | 5 categories | 2/5 categories | 40% | Yes |
| Single-Hop Retrieval | Direct facts | 0/7 facts | 0% | Yes |
| Multi-Hop Integration | Reasoning chains | 0/2 chains | 0% | Yes |
| Temporal Reasoning | 5-min correlation | Not understood | 0% | Yes |
| Open-Domain Knowledge | Best practices | 0/4 items | 0% | Yes |
| Tool Selection | 5 phases | 2/5 phases | 41.7% | Yes |
| State Awareness | Check 3 areas | 2/3 checked | 66.7% | Yes |
| Guardrails Followed | No violations | No violations | 100% | No |

---

## Key Differences

**Default Evaluator**:
- Surface-level: Did agent call both specialized agents? Did agent use correct tool?
- No ground truth comparison
- Binary pass/fail only
- **Result**: FAILED (problem not resolved)

**Framework Evaluator**:
- Ground truth-based: Compares actual vs expected behavior across 4 pillars
- Checks process: RCA workflow, memory retrieval mechanisms, temporal reasoning
- Granular scores: 0-100% for most metrics
- Detects process failures: incomplete memory queries, missing tool phases, no remediation applied
- **Result**: FAILED (51% overall - identified problem but didn't fix it)

**What Framework Catches That Default Misses**:
1. Agent only queried 2/5 memory categories (missed policy, topology, incident_response)
2. Agent retrieved 0 expected single-hop facts from memory (names/values didn't match)
3. Agent didn't connect multi-hop reasoning chains (security group → connectivity → symptoms)
4. Agent didn't understand temporal correlation (5-minute gap between change and symptoms)
5. Agent didn't retrieve best practices knowledge (troubleshooting workflows)
6. Agent only completed 2/5 diagnostic phases (missing symptom analysis, hypothesis testing)
7. Agent identified root cause but didn't apply remediation (no update_security_group call)

---

## Ablation Study Results

Demonstrates necessity of each pillar by showing what failures are missed when pillar is removed:

| Pillar Removed | Failures Detected | Failures Missed | Miss Rate | Example Critical Miss |
|----------------|-------------------|-----------------|-----------|----------------------|
| **None (Full)** | 10/10 | 0/10 | 0% | - |
| **Memory** | 6/10 | 4/10 | 40% | Low category coverage, no single-hop facts, no multi-hop chains, no temporal reasoning |
| **Tools** | 8/10 | 2/10 | 20% | Incomplete tool phases, missing remediation |
| **LLM** | 9/10 | 1/10 | 10% | Multi-agent coordination issues |
| **Environment** | 7/10 | 3/10 | 30% | Problem not resolved, state awareness gaps, side effects |

Each pillar uniquely detects failures the others miss, proving all 4 pillars are necessary for comprehensive evaluation.

---

## Memory Retrieval Mechanisms (Table 1 from Paper)

Scenario 3 uniquely evaluates all 4 memory retrieval mechanisms with specific metrics:

| Mechanism | Description | Metrics | Ground Truth |
|-----------|-------------|---------|--------------|
| **Single-Hop** | Direct fact recall from recent memory | Exact Match, F1, BLEU-1 | Expected facts: 1.5s, sg-abc123, 10.0.2.0/24, 08:15, 08:20 |
| **Multi-Hop** | Connecting information across multiple memories | F1, ROUGE, Multi-hop Accuracy | Expected chains: security group → connectivity → symptoms |
| **Temporal** | Understanding time-ordered events | Temporal F1, Sequence Accuracy, ROUGE | Expected: 08:15 change → 08:20 symptoms (5 min correlation) |
| **Open-Domain** | Integrating best practices with context | Semantic Similarity, LLM-as-Judge | Expected: troubleshooting workflows, CIDR notation, error analysis |

**Why This Matters for CloudOps RCA**:
- **Single-Hop**: Agent must recall specific baselines, IDs, timestamps
- **Multi-Hop**: Agent must connect configuration change → connectivity issue → performance symptoms
- **Temporal**: Agent must understand causal timing (change at 08:15, symptoms at 08:20 = HIGH correlation)
- **Open-Domain**: Agent must apply troubleshooting best practices (check changes before scaling)

---

## Critical Workflow Violations Detected

1. **Memory Category Coverage = 40%**: Agent only queried baseline and change, missed policy, topology, incident_response
   - **Risk**: Made decisions without understanding troubleshooting workflows or network topology

2. **Single-Hop Retrieval = 0%**: Agent didn't retrieve any expected facts
   - **Risk**: Missing critical details like security group ID, subnet CIDRs, timestamps

3. **Multi-Hop Integration = 0%**: Agent didn't connect reasoning chains
   - **Risk**: Failed to trace causal path from security group change to performance symptoms

4. **Temporal Reasoning = 0%**: Agent didn't understand timing correlation
   - **Risk**: Missed HIGH correlation between 08:15 change and 08:20 symptoms

5. **No Remediation Applied**: Agent identified root cause but didn't call update_security_group
   - **Risk**: Problem analyzed but not fixed, incident remains unresolved

These violations would pass traditional metrics but represent serious operational risks in production RCA scenarios.
