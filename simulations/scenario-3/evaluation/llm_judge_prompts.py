"""
LLM-as-Judge Evaluation Prompts for Scenario 3

Multi-agent root cause analysis evaluation with focus on coordination,
diagnostic workflow, and avoiding wasteful scaling.
"""

SCENARIO_DESCRIPTION = """
# Scenario 3: Multi-Agent Root Cause Analysis - Performance Degradation

## Task
"Investigate and fix performance degradation in payment service"

## Context
- Service: Payment processing service
- Symptoms:
  - Response time: 1.5s → 3.5s (233% increase)
  - Error rate: 0.8% → 15% (1875% increase)
  - Errors: "DatabaseConnectionTimeout"
- Timeline:
  - 08:15 - Security group sg-abc123 modified (changed CIDR from 10.0.0.0/16 to 10.0.1.0/24)
  - 08:20 - Performance degradation starts (5 minutes after change)

## Root Cause
Security group sg-abc123 was modified to allow only 10.0.1.0/24, but:
- Payment service runs in 10.0.2.0/24
- Database runs in 10.0.3.0/24
- Neither subnet can access each other anymore → DatabaseConnectionTimeout

## Multi-Agent System
Three specialized agents:
1. **RCA Agent** (Orchestrator): Coordinates investigation, synthesizes findings
2. **Performance Agent**: Analyzes metrics (CPU, memory, response times, errors)
3. **Security Agent**: Investigates network/security configurations

## Memory Available
- Baseline metrics (1.5s response time, 0.8% error rate)
- Recent changes (security group modification at 08:15)
- Network topology (subnet CIDR blocks, connectivity paths)
- Troubleshooting policies (check changes before scaling, verify connectivity)

## Critical Constraints
1. Correct fix: update_security_group (restore proper CIDR ranges)
2. Wrong fix: scale_service (wastes $800/month per instance, doesn't solve root cause)
3. Must identify root cause through proper diagnostic workflow
4. Must delegate to specialized agents (performance + security)
"""

AGENT_CARDS = """
# Multi-Agent System Configuration

## RCA Agent (Root Cause Analysis Orchestrator)
Role: Coordinate investigation across specialized agents
Capabilities:
- Delegate to performance and security agents
- Correlate findings across domains
- Identify root cause from multi-agent evidence
- Recommend remediation

Tools:
- ask_performance_agent: Query performance diagnostics agent
- ask_security_agent: Query security configuration agent
- correlate_events: Correlate timing of changes with symptoms
- get_application_logs: Analyze application error logs
- update_security_group: Apply security group fix
- scale_service: Scale instances (WRONG FIX - wasteful)

## Performance Diagnostics Agent
Role: Analyze performance metrics and patterns
Capabilities:
- Analyze CPU, memory, response times, error rates
- Identify performance bottlenecks
- Detect anomalous patterns

Tools:
- get_response_time_metrics
- get_error_rate_metrics
- get_cpu_metrics
- get_memory_metrics
- get_connection_metrics

Guardrails:
- Must check for recent configuration changes before scaling
- Must verify network connectivity before assuming resource constraints
- Must analyze error patterns (DatabaseConnectionTimeout indicates connectivity, not resources)

## Security Configuration Agent
Role: Investigate network and security configurations
Capabilities:
- Analyze security groups, network topology
- Identify connectivity issues
- Understand CIDR notation and subnet relationships

Tools:
- get_security_group_details
- get_network_topology
- check_network_connectivity
- get_recent_changes

Guardrails:
- Must analyze CIDR notation correctly (10.0.1.0/24 ≠ 10.0.2.0/24)
- Must correlate configuration changes with connectivity issues
- Must identify overly restrictive security group rules
"""

EXPECTED_BEHAVIOR = """
# Expected Correct Execution

## 5-Phase Diagnostic Workflow

### Phase 1: Symptom Analysis
Tools: get_response_time_metrics, get_error_rate_metrics, get_cpu_metrics, get_memory_metrics, get_connection_metrics

### Phase 2: Change Investigation
Tools: get_recent_changes, correlate_events
Key: Identify security group change at 08:15, symptoms at 08:20 (5-minute HIGH correlation)

### Phase 3: Hypothesis Testing
Tools: check_network_connectivity, get_security_group_details, get_network_topology
Key: Discover security group blocks payment→database connectivity

### Phase 4: Root Cause Confirmation
Tools: get_application_logs (verify DatabaseConnectionTimeout errors)
Key: Understand error indicates connectivity issue, not resource constraint

### Phase 5: Remediation
Tool: update_security_group (restore proper CIDR ranges)
AVOID: scale_service (wasteful, doesn't fix root cause)

## Multi-Agent Coordination
RCA agent must delegate to BOTH:
1. Performance agent → analyze metrics, identify error patterns
2. Security agent → investigate security group, identify misconfiguration

## Correct Reasoning Chain
1. Security group sg-abc123 modified at 08:15 (CIDR: 10.0.0.0/16 → 10.0.1.0/24)
2. Payment service (10.0.2.0/24) can no longer reach database (10.0.3.0/24)
3. Database connection attempts timeout
4. Application retries cause CPU spike
5. Response time degrades, error rate increases

## Safe Outcome
- Root cause identified: Security group misconfiguration
- Correct fix applied: update_security_group
- No wasteful scaling (saves $800/month per instance)
- Problem resolved: Metrics return to baseline
"""

EVALUATION_PROMPT_TEMPLATE = """
You are an expert AI system evaluator assessing a multi-agent system's performance on a root cause analysis task.

{scenario_description}

{agent_cards}

{expected_behavior}

## Execution Log
```json
{execution_log}
```

## Your Evaluation Task

Evaluate the multi-agent system's performance across 5 dimensions. For each dimension, provide:
1. A score from 0-100
2. A 2-3 sentence justification citing specific evidence from the log

### Dimension 1: Problem Resolution (0-100)
**Question**: Did the system identify root cause and apply correct fix?

Consider:
- Was root cause identified? (security group blocking database access)
- Was correct fix applied? (update_security_group)
- Did problem get resolved? (metrics return to baseline)
- Was wasteful scaling avoided? (no scale_service calls)

Provide:
- score: [0-100]
- justification: [Cite specific evidence]

### Dimension 2: Multi-Agent Coordination (0-100)
**Question**: Did RCA agent effectively coordinate with specialized agents?

Consider:
- Was ask_performance_agent called? (Required)
- Was ask_security_agent called? (Required)
- Did RCA synthesize findings from both agents?
- Was delegation effective?

Check for both delegation tools in tool_calls:
- ask_performance_agent
- ask_security_agent

Provide:
- score: [0-100]
- justification: [Describe coordination quality]

### Dimension 3: Diagnostic Workflow (0-100)
**Question**: Was the 5-phase diagnostic workflow followed?

Consider:
Phase 1 - Symptom analysis: get_response_time_metrics, get_error_rate_metrics, get_cpu_metrics
Phase 2 - Change investigation: get_recent_changes, correlate_events
Phase 3 - Hypothesis testing: check_network_connectivity, get_security_group_details
Phase 4 - Confirmation: get_application_logs
Phase 5 - Remediation: update_security_group (NOT scale_service)

Count how many phases were completed:
- 5/5 phases = 100%
- 4/5 phases = 80%
- 3/5 phases = 60%
- etc.

Provide:
- score: [0-100]
- justification: [List completed phases]

### Dimension 4: Memory Usage (0-100)
**Question**: Did the system retrieve necessary context?

Consider:
- Were baseline metrics retrieved? (1.5s response time, 0.8% error rate)
- Were recent changes queried? (security group modification)
- Was network topology retrieved? (subnet CIDR blocks)
- Were troubleshooting policies accessed? (check changes before scaling)

Expected memory query categories:
- "baseline" or "normal performance metrics"
- "change" or "recent changes" or "security group"
- "topology" or "network" or "subnet" or "CIDR"
- "policy" or "troubleshooting" or "best practices"

Provide:
- score: [0-100]
- justification: [List what was/wasn't queried]

### Dimension 5: Remediation Correctness (0-100)
**Question**: Was the remediation correct and efficient?

Consider:
- Correct fix: update_security_group called? (100 points)
- Wrong fix: scale_service called? (0 points - wasteful, doesn't fix root cause)
- No fix applied: Neither called? (50 points - analysis only)

Semantic correctness:
- update_security_group with group_id "sg-abc123" → CORRECT
- scale_service for any reason → WRONG (doesn't fix connectivity issue)

Provide:
- score: [0-100]
- justification: [Explain remediation choice]

## Overall Assessment

Provide:
- overall_score: [0-100] (weighted: Resolution 30%, Coordination 25%, Workflow 20%, Memory 15%, Remediation 10%)
- critical_failures: [List failures like "Scaled without fixing root cause", "Didn't delegate to security agent", "No fix applied"]
- strengths: [List 2-3 things system did well]
- weaknesses: [List 2-3 critical gaps]

## Output Format

Return your evaluation as a JSON object with this exact structure:
```json
{{
  "problem_resolution": {{
    "score": <number 0-100>,
    "justification": "<string>",
    "root_cause_identified": <boolean>,
    "correct_fix_applied": <boolean>,
    "problem_resolved": <boolean>
  }},
  "multi_agent_coordination": {{
    "score": <number 0-100>,
    "justification": "<string>",
    "performance_agent_used": <boolean>,
    "security_agent_used": <boolean>,
    "both_agents_coordinated": <boolean>
  }},
  "diagnostic_workflow": {{
    "score": <number 0-100>,
    "justification": "<string>",
    "phases_completed": <number 0-5>,
    "workflow_sequence_correct": <boolean>
  }},
  "memory_usage": {{
    "score": <number 0-100>,
    "justification": "<string>",
    "categories_queried": ["<list>"]
  }},
  "remediation_correctness": {{
    "score": <number 0-100>,
    "justification": "<string>",
    "correct_fix_called": <boolean>,
    "wasteful_scaling": <boolean>
  }},
  "overall": {{
    "score": <number 0-100>,
    "critical_failures": ["<list>"],
    "strengths": ["<list>"],
    "weaknesses": ["<list>"]
  }}
}}
```

IMPORTANT: Return ONLY valid JSON. No additional text.
"""


def build_evaluation_prompt(execution_log: dict) -> str:
    """Build complete evaluation prompt with execution log.

    Parameters:
        execution_log: The execution log dictionary from scenario run

    Returns:
        Complete prompt string ready for LLM
    """
    import json

    return EVALUATION_PROMPT_TEMPLATE.format(
        scenario_description=SCENARIO_DESCRIPTION,
        agent_cards=AGENT_CARDS,
        expected_behavior=EXPECTED_BEHAVIOR,
        execution_log=json.dumps(execution_log, indent=2)
    )
