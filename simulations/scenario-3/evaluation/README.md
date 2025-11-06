# Evaluation Scripts for Scenario 3

## Overview
Scenario 3 now shares the same dataclass-driven contract as the other scenarios
(`scenario_expectations.py` defines the LLM, Tools, Memory, and Environment
expectations inside a single `SCENARIO_EVAL_CONFIG`). Every evaluator reads from
that contract so results stay consistent across the paper.

## Scripts

### 1. `default_evaluator.py`
Legacy metrics (task completion, tool syntax) for baseline comparison.

### 2. `framework_evaluator.py`
Four-pillar assessment with Scenario 3 specifics:
- **LLM**: Multi-agent coordination, guardrail adherence, reasoning sequence
- **Memory**: Category coverage, single/multi hop scores, temporal/causal signals
- **Tools**: Phase coverage, delegation counts, remediation correctness
- **Environment**: Resolution flags, guardrail violations, cost impact

### 3. `memory_evaluator.py`
Focused memory analysis using the same contract. Reports:
- Required/optional category coverage, with sampled memories
- Retrieval mechanism scores (single-hop, multi-hop, temporal, causal)
- An overall memory score that folds into the paper’s pillar dashboard

### 4. `compare_evaluators.py` & `ablation_study.py`
Side-by-side comparisons and pillar ablations (updated to consume the shared
config). Use them the same way as Scenarios 1 and 2.

## Usage
Run any script from `simulations/scenario-3/evaluation/`:
```bash
python framework_evaluator.py
python memory_evaluator.py                  # latest log
python memory_evaluator.py path/to/log.json # specific log
python compare_evaluators.py
python ablation_study.py
```

## Notes for the Paper
- The Scenario 3 configuration exposes every expectation in a single structure,
  mirroring Scenarios 1/2 so tables and plots can share the same schema.
- The memory evaluator feeds directly from `SCENARIO_EVAL_CONFIG.memory`, so any
  additions (new categories or signals) automatically appear in the report.
