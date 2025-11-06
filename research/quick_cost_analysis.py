#!/usr/bin/env python3
"""
Quick cost analysis script for research logs.
This script analyzes the specific logs mentioned in the RQ files.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any

def load_json_log(file_path: str) -> Dict[str, Any]:
    """Load JSON log file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return {}

def extract_cost_from_log(log_data: Dict[str, Any]) -> Dict[str, float]:
    """Extract cost information from log data."""
    cost_info = {
        'total_cost': 0.0,
        'input_tokens': 0,
        'output_tokens': 0,
        'total_tokens': 0,
        'evaluation_time': 0.0
    }
    
    # Handle LLM-as-Judge format
    if 'cost_metrics' in log_data:
        cost_metrics = log_data['cost_metrics']
        cost_info['total_cost'] = cost_metrics.get('total_cost_usd', 0.0)
        cost_info['input_tokens'] = cost_metrics.get('prompt_tokens', 0)
        cost_info['output_tokens'] = cost_metrics.get('completion_tokens', 0)
        cost_info['total_tokens'] = cost_metrics.get('total_tokens', 0)
        cost_info['evaluation_time'] = cost_metrics.get('evaluation_time_seconds', 0.0)
    
    # Handle Agent-as-Judge format (single agent)
    elif 'metrics' in log_data and 'cost_metrics' in log_data['metrics']:
        cost_table = log_data['metrics']['cost_metrics'].get('cost_table', [])
        for component in cost_table:
            if component.get('component') == 'Combined':
                cost_info['total_cost'] = component.get('total_cost_usd', 0.0)
                cost_info['input_tokens'] = component.get('input_tokens', 0)
                cost_info['output_tokens'] = component.get('output_tokens', 0)
                cost_info['total_tokens'] = cost_info['input_tokens'] + cost_info['output_tokens']
                break
        cost_info['evaluation_time'] = log_data['metrics'].get('total_time_seconds', 0.0)
    
    # Handle Agent-as-Judge format (multi-agent)
    elif 'aggregated_costs' in log_data:
        cost_table = log_data['aggregated_costs'].get('cost_table', [])
        for component in cost_table:
            if component.get('component') == 'Combined':
                cost_info['total_cost'] = component.get('total_cost_usd', 0.0)
                cost_info['input_tokens'] = component.get('input_tokens', 0)
                cost_info['output_tokens'] = component.get('output_tokens', 0)
                cost_info['total_tokens'] = cost_info['input_tokens'] + cost_info['output_tokens']
                break
        
        # Calculate total time from individual evaluations
        if 'evaluations' in log_data:
            total_time = 0
            for eval_data in log_data['evaluations']:
                if 'metrics' in eval_data:
                    total_time += eval_data['metrics'].get('total_time_seconds', 0)
            cost_info['evaluation_time'] = total_time
    
    return cost_info

def analyze_research_logs():
    """Analyze all research logs and calculate totals."""
    
    # Define the logs mentioned in RQ files
    logs_to_analyze = {
        "scenario-1": [
            "scenario-1_20251014_025025.json",
            "scenario-1_20251014_025519.json", 
            "scenario-1_20251014_030532.json"
        ],
        "scenario-2": [
            "scenario-2_20251014_034519.json",
            "scenario-2_20251014_034908.json",
            "scenario-2_20251014_035353.json"
        ],
        "scenario-3": [
            "scenario-3_20251014_034628.json",
            "scenario-3_20251014_035554.json",
            "scenario-3_20251014_035735.json"
        ]
    }
    
    # Also include the evaluation logs from research directory
    evaluation_logs = {
        "scenario-1": ["agent_judge.json", "llm_judge.json"],
        "scenario-2": ["agent_judge.json", "llm_judge.json"], 
        "scenario-3": ["agent_judge.json", "llm_judge.json"]
    }
    
    print("🔍 Analyzing Research Logs")
    print("=" * 50)
    
    total_cost = 0.0
    total_tokens = 0
    total_time = 0.0
    total_logs = 0
    
    scenario_totals = {}
    
    # Analyze simulation logs
    for scenario, log_files in logs_to_analyze.items():
        print(f"\n📊 {scenario.upper()}")
        scenario_cost = 0.0
        scenario_tokens = 0
        scenario_time = 0.0
        scenario_logs = 0
        
        for log_file in log_files:
            # Try different possible locations
            possible_paths = [
                f"../simulations/{scenario}/logs/{log_file}",
                f"../simulations/{scenario}/simulations/{scenario}/logs/{log_file}",
                f"../simulations/{scenario}/{log_file}"
            ]
            
            log_data = {}
            found_path = None
            
            for path in possible_paths:
                if os.path.exists(path):
                    log_data = load_json_log(path)
                    found_path = path
                    break
            
            if log_data:
                cost_info = extract_cost_from_log(log_data)
                scenario_cost += cost_info['total_cost']
                scenario_tokens += cost_info['total_tokens']
                scenario_time += cost_info['evaluation_time']
                scenario_logs += 1
                total_logs += 1
                
                print(f"  ✅ {log_file}: ${cost_info['total_cost']:.4f}, {cost_info['total_tokens']:,} tokens")
            else:
                print(f"  ❌ {log_file}: Not found")
        
        scenario_totals[scenario] = {
            'cost': scenario_cost,
            'tokens': scenario_tokens,
            'time': scenario_time,
            'logs': scenario_logs
        }
        
        total_cost += scenario_cost
        total_tokens += scenario_tokens
        total_time += scenario_time
    
    # Analyze evaluation logs
    print(f"\n📊 EVALUATION LOGS")
    eval_cost = 0.0
    eval_tokens = 0
    eval_time = 0.0
    eval_logs = 0
    
    for scenario, log_files in evaluation_logs.items():
        for log_file in log_files:
            log_path = f"{scenario}/{log_file}"
            if os.path.exists(log_path):
                log_data = load_json_log(log_path)
                if log_data:
                    cost_info = extract_cost_from_log(log_data)
                    eval_cost += cost_info['total_cost']
                    eval_tokens += cost_info['total_tokens']
                    eval_time += cost_info['evaluation_time']
                    eval_logs += 1
                    total_logs += 1
                    
                    print(f"  ✅ {log_path}: ${cost_info['total_cost']:.4f}, {cost_info['total_tokens']:,} tokens")
            else:
                print(f"  ❌ {log_path}: Not found")
    
    # Print summary
    print("\n" + "=" * 50)
    print("📋 SUMMARY")
    print("=" * 50)
    
    print(f"📊 Total Logs Analyzed: {total_logs}")
    print(f"💰 Total Cost: ${total_cost:.4f} USD")
    print(f"🔤 Total Tokens: {total_tokens:,}")
    print(f"⏱️  Total Time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
    
    if total_tokens > 0:
        cost_per_token = total_cost / total_tokens
        print(f"💵 Cost per Token: ${cost_per_token:.6f}")
    
    if total_time > 0:
        tokens_per_second = total_tokens / total_time
        print(f"⚡ Tokens per Second: {tokens_per_second:.1f}")
    
    print("\n📈 Per-Scenario Breakdown:")
    for scenario, totals in scenario_totals.items():
        print(f"  {scenario}: ${totals['cost']:.4f} ({totals['logs']} logs, {totals['tokens']:,} tokens)")
    
    if eval_logs > 0:
        print(f"  Evaluation Logs: ${eval_cost:.4f} ({eval_logs} logs, {eval_tokens:,} tokens)")
    
    # Save results to file
    results = {
        'total_cost': total_cost,
        'total_tokens': total_tokens,
        'total_time': total_time,
        'total_logs': total_logs,
        'scenario_totals': scenario_totals,
        'evaluation_totals': {
            'cost': eval_cost,
            'tokens': eval_tokens,
            'time': eval_time,
            'logs': eval_logs
        }
    }
    
    with open('cost_analysis_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: cost_analysis_results.json")

if __name__ == "__main__":
    analyze_research_logs()

