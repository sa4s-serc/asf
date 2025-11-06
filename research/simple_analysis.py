#!/usr/bin/env python3
"""
Simple analysis script to generate 4 tables:
1. Scenario execution costs and tokens
2. LLM-as-Judge evaluation costs and time
3. Agent-as-Judge evaluation costs and time  
4. LLM-as-Judge scores
5. Agent-as-Judge scores
"""

import json
import os
from pathlib import Path

def load_json(file_path):
    """Load JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except:
        return {}

def extract_cost_metrics(log_data):
    """Extract cost and token metrics."""
    metrics = {
        'cost': 0.0,
        'input_tokens': 0,
        'output_tokens': 0,
        'total_tokens': 0,
        'time': 0.0
    }
    
    # LLM-as-Judge format
    if 'cost_metrics' in log_data:
        cost_metrics = log_data['cost_metrics']
        metrics['cost'] = cost_metrics.get('total_cost_usd', 0.0)
        metrics['input_tokens'] = cost_metrics.get('prompt_tokens', 0)
        metrics['output_tokens'] = cost_metrics.get('completion_tokens', 0)
        metrics['total_tokens'] = cost_metrics.get('total_tokens', 0)
        metrics['time'] = cost_metrics.get('evaluation_time_seconds', 0.0)
    
    # Agent-as-Judge format (single agent)
    elif 'metrics' in log_data and 'cost_metrics' in log_data['metrics']:
        cost_table = log_data['metrics']['cost_metrics'].get('cost_table', [])
        for component in cost_table:
            if component.get('component') == 'Combined':
                metrics['cost'] = component.get('total_cost_usd', 0.0)
                metrics['input_tokens'] = component.get('input_tokens', 0)
                metrics['output_tokens'] = component.get('output_tokens', 0)
                metrics['total_tokens'] = metrics['input_tokens'] + metrics['output_tokens']
                break
        metrics['time'] = log_data['metrics'].get('total_time_seconds', 0.0)
    
    # Agent-as-Judge format (multi-agent)
    elif 'aggregated_costs' in log_data:
        cost_table = log_data['aggregated_costs'].get('cost_table', [])
        for component in cost_table:
            if component.get('component') == 'Combined':
                metrics['cost'] = component.get('total_cost_usd', 0.0)
                metrics['input_tokens'] = component.get('input_tokens', 0)
                metrics['output_tokens'] = component.get('output_tokens', 0)
                metrics['total_tokens'] = metrics['input_tokens'] + metrics['output_tokens']
                break
        
        if 'evaluations' in log_data:
            total_time = 0
            for eval_data in log_data['evaluations']:
                if 'metrics' in eval_data:
                    total_time += eval_data['metrics'].get('total_time_seconds', 0)
            metrics['time'] = total_time
    
    return metrics

def extract_scores(log_data):
    """Extract scores from log data."""
    scores = {}
    
    # LLM-as-Judge format
    if 'evaluation' in log_data and 'overall' in log_data['evaluation']:
        scores['overall'] = log_data['evaluation']['overall'].get('score', 0)
        for key, value in log_data['evaluation'].items():
            if key != 'overall' and isinstance(value, dict) and 'score' in value:
                scores[key] = value.get('score', 0)
    
    # Agent-as-Judge format
    elif 'assessment' in log_data:
        scores['overall'] = log_data['assessment'].get('overall_score', 0)
        scores['tests_passed'] = log_data['assessment'].get('tests_passed', 0)
        scores['tests_failed'] = log_data['assessment'].get('tests_failed', 0)
        scores['compliance'] = log_data['assessment'].get('agent_card_compliance', 'UNKNOWN')
    
    # Multi-agent format
    elif 'evaluations' in log_data:
        for eval_data in log_data['evaluations']:
            if 'assessment' in eval_data:
                agent_name = eval_data.get('agent', 'unknown')
                scores[f"{agent_name}_overall"] = eval_data['assessment'].get('overall_score', 0)
                scores[f"{agent_name}_tests_passed"] = eval_data['assessment'].get('tests_passed', 0)
                scores[f"{agent_name}_tests_failed"] = eval_data['assessment'].get('tests_failed', 0)
                scores[f"{agent_name}_compliance"] = eval_data['assessment'].get('agent_card_compliance', 'UNKNOWN')
    
    return scores

def main():
    print("=" * 80)
    print("RESEARCH LOG ANALYSIS - SUMMARY TABLES")
    print("=" * 80)
    
    # Table 1: Scenario Execution Costs (from simulation logs)
    print("\n1. SCENARIO EXECUTION COSTS & TOKENS")
    print("-" * 50)
    print("| Scenario | Cost (USD) | Input Tokens | Output Tokens | Total Tokens | Time (s) |")
    print("|----------|------------|--------------|---------------|--------------|----------|")
    
    scenario_logs = {
        "scenario-1": ["scenario-1_20251014_025025.json", "scenario-1_20251014_025519.json", "scenario-1_20251014_030532.json"],
        "scenario-2": ["scenario-2_20251014_034519.json", "scenario-2_20251014_034908.json", "scenario-2_20251014_035353.json"],
        "scenario-3": ["scenario-3_20251014_034628.json", "scenario-3_20251014_035554.json", "scenario-3_20251014_035735.json"]
    }
    
    scenario_totals = {}
    
    for scenario, log_files in scenario_logs.items():
        total_cost = 0.0
        total_input = 0
        total_output = 0
        total_tokens = 0
        total_time = 0.0
        
        for log_file in log_files:
            possible_paths = [
                f"../simulations/{scenario}/logs/{log_file}",
                f"../simulations/{scenario}/simulations/{scenario}/logs/{log_file}"
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    log_data = load_json(path)
                    if log_data:
                        metrics = extract_cost_metrics(log_data)
                        total_cost += metrics['cost']
                        total_input += metrics['input_tokens']
                        total_output += metrics['output_tokens']
                        total_tokens += metrics['total_tokens']
                        total_time += metrics['time']
                    break
        
        scenario_totals[scenario] = {
            'cost': total_cost,
            'input_tokens': total_input,
            'output_tokens': total_output,
            'total_tokens': total_tokens,
            'time': total_time
        }
        
        print(f"| {scenario} | ${total_cost:.4f} | {total_input:,} | {total_output:,} | {total_tokens:,} | {total_time:.1f} |")
    
    # Table 2: LLM-as-Judge Evaluation Costs
    print("\n2. LLM-AS-JUDGE EVALUATION COSTS & TIME")
    print("-" * 50)
    print("| Scenario | Cost (USD) | Input Tokens | Output Tokens | Total Tokens | Time (s) |")
    print("|----------|------------|--------------|---------------|--------------|----------|")
    
    llm_totals = {'cost': 0.0, 'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0, 'time': 0.0}
    
    for scenario in ["scenario-1", "scenario-2", "scenario-3"]:
        log_path = f"{scenario}/llm_judge.json"
        if os.path.exists(log_path):
            log_data = load_json(log_path)
            if log_data:
                metrics = extract_cost_metrics(log_data)
                llm_totals['cost'] += metrics['cost']
                llm_totals['input_tokens'] += metrics['input_tokens']
                llm_totals['output_tokens'] += metrics['output_tokens']
                llm_totals['total_tokens'] += metrics['total_tokens']
                llm_totals['time'] += metrics['time']
                
                print(f"| {scenario} | ${metrics['cost']:.4f} | {metrics['input_tokens']:,} | {metrics['output_tokens']:,} | {metrics['total_tokens']:,} | {metrics['time']:.1f} |")
    
    print(f"| TOTAL    | ${llm_totals['cost']:.4f} | {llm_totals['input_tokens']:,} | {llm_totals['output_tokens']:,} | {llm_totals['total_tokens']:,} | {llm_totals['time']:.1f} |")
    
    # Table 3: Agent-as-Judge Evaluation Costs
    print("\n3. AGENT-AS-JUDGE EVALUATION COSTS & TIME")
    print("-" * 50)
    print("| Scenario | Cost (USD) | Input Tokens | Output Tokens | Total Tokens | Time (s) |")
    print("|----------|------------|--------------|---------------|--------------|----------|")
    
    agent_totals = {'cost': 0.0, 'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0, 'time': 0.0}
    
    for scenario in ["scenario-1", "scenario-2", "scenario-3"]:
        log_path = f"{scenario}/agent_judge.json"
        if os.path.exists(log_path):
            log_data = load_json(log_path)
            if log_data:
                metrics = extract_cost_metrics(log_data)
                agent_totals['cost'] += metrics['cost']
                agent_totals['input_tokens'] += metrics['input_tokens']
                agent_totals['output_tokens'] += metrics['output_tokens']
                agent_totals['total_tokens'] += metrics['total_tokens']
                agent_totals['time'] += metrics['time']
                
                print(f"| {scenario} | ${metrics['cost']:.4f} | {metrics['input_tokens']:,} | {metrics['output_tokens']:,} | {metrics['total_tokens']:,} | {metrics['time']:.1f} |")
    
    print(f"| TOTAL    | ${agent_totals['cost']:.4f} | {agent_totals['input_tokens']:,} | {agent_totals['output_tokens']:,} | {agent_totals['total_tokens']:,} | {agent_totals['time']:.1f} |")
    
    # Table 4: LLM-as-Judge Scores
    print("\n4. LLM-AS-JUDGE SCORES")
    print("-" * 50)
    print("| Scenario | Overall | Task Completion | Safety | Reasoning | Memory | Parameters |")
    print("|----------|---------|-----------------|--------|-----------|--------|------------|")
    
    for scenario in ["scenario-1", "scenario-2", "scenario-3"]:
        log_path = f"{scenario}/llm_judge.json"
        if os.path.exists(log_path):
            log_data = load_json(log_path)
            if log_data:
                scores = extract_scores(log_data)
                overall = scores.get('overall', 0)
                task = scores.get('task_completion', {}).get('score', 0) if isinstance(scores.get('task_completion'), dict) else 0
                safety = scores.get('safety_guardrails', {}).get('score', 0) if isinstance(scores.get('safety_guardrails'), dict) else scores.get('safety_compliance', {}).get('score', 0) if isinstance(scores.get('safety_compliance'), dict) else 0
                reasoning = scores.get('reasoning_quality', {}).get('score', 0) if isinstance(scores.get('reasoning_quality'), dict) else 0
                memory = scores.get('memory_usage', {}).get('score', 0) if isinstance(scores.get('memory_usage'), dict) else 0
                params = scores.get('parameter_correctness', {}).get('score', 0) if isinstance(scores.get('parameter_correctness'), dict) else scores.get('policy_correctness', {}).get('score', 0) if isinstance(scores.get('policy_correctness'), dict) else 0
                
                print(f"| {scenario} | {overall} | {task} | {safety} | {reasoning} | {memory} | {params} |")
    
    # Table 5: Agent-as-Judge Scores
    print("\n5. AGENT-AS-JUDGE SCORES")
    print("-" * 50)
    print("| Scenario | Agent | Overall Score | Tests Passed | Tests Failed | Compliance |")
    print("|----------|-------|---------------|--------------|--------------|------------|")
    
    for scenario in ["scenario-1", "scenario-2", "scenario-3"]:
        log_path = f"{scenario}/agent_judge.json"
        if os.path.exists(log_path):
            log_data = load_json(log_path)
            if log_data:
                # Check if multi-agent (scenario-3) or single agent
                if 'evaluations' in log_data:
                    # Multi-agent format
                    for eval_data in log_data['evaluations']:
                        agent_name = eval_data.get('agent', 'unknown')
                        scores = extract_scores(eval_data)
                        overall = scores.get('overall', 0)
                        passed = scores.get('tests_passed', 0)
                        failed = scores.get('tests_failed', 0)
                        compliance = scores.get('compliance', 'UNKNOWN')
                        print(f"| {scenario} | {agent_name} | {overall} | {passed} | {failed} | {compliance} |")
                else:
                    # Single agent format
                    scores = extract_scores(log_data)
                    overall = scores.get('overall', 0)
                    passed = scores.get('tests_passed', 0)
                    failed = scores.get('tests_failed', 0)
                    compliance = scores.get('compliance', 'UNKNOWN')
                    agent_name = log_data.get('agent_tested', 'unknown')
                    print(f"| {scenario} | {agent_name} | {overall} | {passed} | {failed} | {compliance} |")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

