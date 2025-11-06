# Evaluation Scripts for Scenario 2

## Overview
Scenario 2 now mirrors the Scenario 1 evaluation harness. Two evaluators provide
contrasting views of the same execution, and helper scripts aggregate results
and surface pillar-level gaps.

## Scripts

### 1. `default_evaluator.py`
Traditional metrics assessment:
- Task completion (bucket made private?)
- Tool calling accuracy (registered tools only?)
- Response quality (any answer?)

**Usage:**
```bash
python default_evaluator.py
```

### 2. `framework_evaluator.py`
Four-pillar assessment aligned with Scenario 1:
- **LLM**: Guardrail adherence, incident documentation
- **Memory**: Policy/compliance/dependency retrieval quality
- **Tools**: Selection, sequencing, policy safety, parameter semantics
- **Environment**: Controls enabled, authorised access preserved

**Usage:**
```bash
python framework_evaluator.py
```

### 3. `compare_evaluators.py`
Side-by-side comparison (same table layout as Scenario 1) highlighting what the
default metrics miss.

**Usage:**
```bash
python compare_evaluators.py
```

### 4. `ablation_study.py`
Counts average failures per pillar (same "Avg misses/run" table as Scenario 1).

**Usage:**
```bash
python ablation_study.py
```

## Expected Results

### Default Evaluator
```
Overall Status: SUCCESS
Overall Score: 0.93

✅ Task Completion: SUCCESS (bucket public access removed)
✅ Tool Calling Accuracy: 100%
✅ Response Quality: SUCCESS
```

### Framework Evaluator
```
Overall Status: FAILED
Overall Score: 0.34

❌ Policy/Compliance queries missing
❌ Dependencies unverified
❌ Policy update blocks authorised roles
❌ Logging/versioning controls left disabled
❌ Incident never documented
```

## Key Insight
Same execution → Different conclusions based on evaluation depth, exactly as in
Scenario 1. The framework view exposes compliance, evidence, and dependency
gaps that traditional success metrics overlook.
