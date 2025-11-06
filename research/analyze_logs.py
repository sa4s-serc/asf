#!/usr/bin/env python3
"""
Script to analyze JSON logs from the research directory and calculate total costs and tokens.
This script reads all the logs mentioned in the RQ files and provides comprehensive cost analysis.
"""

import json
import os
import glob
from pathlib import Path
from typing import Dict, List, Any, Tuple
import pandas as pd

class LogAnalyzer:
    def __init__(self, research_dir: str = "research"):
        self.research_dir = Path(research_dir)
        self.logs_data = {}
        self.cost_summary = {}
        
    def find_log_files(self) -> Dict[str, List[str]]:
        """Find all log files mentioned in RQ files and organize by scenario."""
        scenario_logs = {
            "scenario-1": [],
            "scenario-2": [], 
            "scenario-3": []
        }
        
        # Read RQ files to get the exact log filenames
        rq_files = [
            "scenario-1/rq_1.md",
            "scenario-1/rq_2.md", 
            "scenario-2/rq_1.md",
            "scenario-2/rq_2.md",
            "scenario-3/rq_1.md",
            "scenario-3/rq_2.md"
        ]
        
        for rq_file in rq_files:
            rq_path = self.research_dir / rq_file
            if rq_path.exists():
                with open(rq_path, 'r') as f:
                    content = f.read()
                    # Extract log filenames from the content
                    lines = content.split('\n')
                    for line in lines:
                        if '.json' in line and 'scenario-' in line:
                            # Extract the log filename
                            parts = line.split()
                            for part in parts:
                                if part.endswith('.json') and 'scenario-' in part:
                                    scenario = part.split('_')[0] + '_' + part.split('_')[1]
                                    if scenario in scenario_logs:
                                        scenario_logs[scenario].append(part)
        
        # Also check for logs in simulations directory
        simulations_dir = Path("simulations")
        if simulations_dir.exists():
            for scenario_dir in simulations_dir.glob("scenario-*"):
                scenario_name = scenario_dir.name
                logs_dir = scenario_dir / "logs"
                if logs_dir.exists():
                    for log_file in logs_dir.glob("*.json"):
                        log_name = log_file.name
                        if scenario_name in scenario_logs:
                            scenario_logs[scenario_name].append(log_name)
        
        # Remove duplicates
        for scenario in scenario_logs:
            scenario_logs[scenario] = list(set(scenario_logs[scenario]))
            
        return scenario_logs
    
    def load_log_file(self, log_path: Path) -> Dict[str, Any]:
        """Load and parse a JSON log file."""
        try:
            with open(log_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {log_path}: {e}")
            return {}
    
    def extract_cost_metrics(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract cost and token metrics from log data."""
        metrics = {
            'total_cost_usd': 0.0,
            'input_tokens': 0,
            'output_tokens': 0,
            'total_tokens': 0,
            'evaluation_time_seconds': 0,
            'conversation_turns': 0,
            'worker_agent_calls': 0,
            'environment_tool_calls': 0
        }
        
        # Handle different log structures
        if 'cost_metrics' in log_data:
            # LLM-as-Judge format
            cost_metrics = log_data['cost_metrics']
            metrics['total_cost_usd'] = cost_metrics.get('total_cost_usd', 0.0)
            metrics['input_tokens'] = cost_metrics.get('prompt_tokens', 0)
            metrics['output_tokens'] = cost_metrics.get('completion_tokens', 0)
            metrics['total_tokens'] = cost_metrics.get('total_tokens', 0)
            metrics['evaluation_time_seconds'] = cost_metrics.get('evaluation_time_seconds', 0)
            
        elif 'metrics' in log_data:
            # Agent-as-Judge format (single agent)
            metrics_data = log_data['metrics']
            if 'cost_metrics' in metrics_data:
                cost_table = metrics_data['cost_metrics'].get('cost_table', [])
                for component in cost_table:
                    if component.get('component') == 'Combined':
                        metrics['total_cost_usd'] = component.get('total_cost_usd', 0.0)
                        metrics['input_tokens'] = component.get('input_tokens', 0)
                        metrics['output_tokens'] = component.get('output_tokens', 0)
                        metrics['total_tokens'] = metrics['input_tokens'] + metrics['output_tokens']
                        break
            
            metrics['evaluation_time_seconds'] = metrics_data.get('total_time_seconds', 0)
            metrics['conversation_turns'] = metrics_data.get('conversation_turns', 0)
            metrics['worker_agent_calls'] = metrics_data.get('worker_agent_calls', 0)
            metrics['environment_tool_calls'] = metrics_data.get('environment_tool_calls', 0)
            
        elif 'aggregated_costs' in log_data:
            # Agent-as-Judge format (multi-agent)
            cost_table = log_data['aggregated_costs'].get('cost_table', [])
            for component in cost_table:
                if component.get('component') == 'Combined':
                    metrics['total_cost_usd'] = component.get('total_cost_usd', 0.0)
                    metrics['input_tokens'] = component.get('input_tokens', 0)
                    metrics['output_tokens'] = component.get('output_tokens', 0)
                    metrics['total_tokens'] = metrics['input_tokens'] + metrics['output_tokens']
                    break
            
            # Calculate total time from individual agent evaluations
            if 'evaluations' in log_data:
                total_time = 0
                total_turns = 0
                total_worker_calls = 0
                total_env_calls = 0
                for eval_data in log_data['evaluations']:
                    if 'metrics' in eval_data:
                        total_time += eval_data['metrics'].get('total_time_seconds', 0)
                        total_turns += eval_data['metrics'].get('conversation_turns', 0)
                        total_worker_calls += eval_data['metrics'].get('worker_agent_calls', 0)
                        total_env_calls += eval_data['metrics'].get('environment_tool_calls', 0)
                
                metrics['evaluation_time_seconds'] = total_time
                metrics['conversation_turns'] = total_turns
                metrics['worker_agent_calls'] = total_worker_calls
                metrics['environment_tool_calls'] = total_env_calls
        
        return metrics
    
    def analyze_all_logs(self) -> Dict[str, Any]:
        """Analyze all log files and return comprehensive summary."""
        scenario_logs = self.find_log_files()
        all_results = {}
        
        print("🔍 Finding and analyzing log files...")
        
        for scenario, log_files in scenario_logs.items():
            print(f"\n📊 Analyzing {scenario}...")
            scenario_results = {
                'logs_analyzed': [],
                'total_cost_usd': 0.0,
                'total_input_tokens': 0,
                'total_output_tokens': 0,
                'total_tokens': 0,
                'total_evaluation_time': 0,
                'total_conversation_turns': 0,
                'total_worker_calls': 0,
                'total_env_calls': 0,
                'log_details': []
            }
            
            for log_file in log_files:
                # Try to find the log file in different locations
                log_paths = [
                    self.research_dir / scenario / log_file,
                    Path("simulations") / scenario / "logs" / log_file,
                    Path("simulations") / scenario / "simulations" / scenario / "logs" / log_file
                ]
                
                log_data = {}
                log_path = None
                
                for path in log_paths:
                    if path.exists():
                        log_data = self.load_log_file(path)
                        log_path = path
                        break
                
                if log_data:
                    metrics = self.extract_cost_metrics(log_data)
                    scenario_results['logs_analyzed'].append(log_file)
                    scenario_results['total_cost_usd'] += metrics['total_cost_usd']
                    scenario_results['total_input_tokens'] += metrics['input_tokens']
                    scenario_results['total_output_tokens'] += metrics['output_tokens']
                    scenario_results['total_tokens'] += metrics['total_tokens']
                    scenario_results['total_evaluation_time'] += metrics['evaluation_time_seconds']
                    scenario_results['total_conversation_turns'] += metrics['conversation_turns']
                    scenario_results['total_worker_calls'] += metrics['worker_agent_calls']
                    scenario_results['total_env_calls'] += metrics['environment_tool_calls']
                    
                    scenario_results['log_details'].append({
                        'file': log_file,
                        'path': str(log_path),
                        'cost_usd': metrics['total_cost_usd'],
                        'input_tokens': metrics['input_tokens'],
                        'output_tokens': metrics['output_tokens'],
                        'total_tokens': metrics['total_tokens'],
                        'evaluation_time': metrics['evaluation_time_seconds'],
                        'conversation_turns': metrics['conversation_turns']
                    })
                    
                    print(f"  ✅ {log_file}: ${metrics['total_cost_usd']:.4f}, {metrics['total_tokens']} tokens")
                else:
                    print(f"  ❌ {log_file}: File not found")
            
            all_results[scenario] = scenario_results
        
        return all_results
    
    def generate_summary_report(self, results: Dict[str, Any]) -> str:
        """Generate a comprehensive summary report."""
        report = []
        report.append("# Research Log Analysis Summary")
        report.append("=" * 50)
        report.append("")
        
        # Overall totals
        total_cost = sum(scenario['total_cost_usd'] for scenario in results.values())
        total_tokens = sum(scenario['total_tokens'] for scenario in results.values())
        total_time = sum(scenario['total_evaluation_time'] for scenario in results.values())
        total_logs = sum(len(scenario['logs_analyzed']) for scenario in results.values())
        
        report.append(f"## Overall Summary")
        report.append(f"- **Total Logs Analyzed**: {total_logs}")
        report.append(f"- **Total Cost**: ${total_cost:.4f} USD")
        report.append(f"- **Total Tokens**: {total_tokens:,}")
        report.append(f"- **Total Evaluation Time**: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
        report.append("")
        
        # Per-scenario breakdown
        report.append("## Per-Scenario Breakdown")
        report.append("")
        
        for scenario, data in results.items():
            report.append(f"### {scenario.replace('_', ' ').title()}")
            report.append(f"- **Logs**: {len(data['logs_analyzed'])}")
            report.append(f"- **Cost**: ${data['total_cost_usd']:.4f} USD")
            report.append(f"- **Tokens**: {data['total_tokens']:,} ({data['total_input_tokens']:,} input, {data['total_output_tokens']:,} output)")
            report.append(f"- **Time**: {data['total_evaluation_time']:.1f} seconds")
            report.append(f"- **Conversation Turns**: {data['total_conversation_turns']}")
            report.append(f"- **Worker Calls**: {data['total_worker_calls']}")
            report.append(f"- **Environment Calls**: {data['total_env_calls']}")
            report.append("")
            
            if data['log_details']:
                report.append("#### Individual Log Details")
                report.append("| File | Cost (USD) | Tokens | Time (s) | Turns |")
                report.append("|------|------------|--------|----------|-------|")
                for detail in data['log_details']:
                    report.append(f"| {detail['file']} | ${detail['cost_usd']:.4f} | {detail['total_tokens']:,} | {detail['evaluation_time']:.1f} | {detail['conversation_turns']} |")
                report.append("")
        
        # Cost analysis
        report.append("## Cost Analysis")
        report.append("")
        
        # Calculate cost per token
        if total_tokens > 0:
            cost_per_token = total_cost / total_tokens
            report.append(f"- **Cost per Token**: ${cost_per_token:.6f}")
        
        # Calculate cost per log
        if total_logs > 0:
            cost_per_log = total_cost / total_logs
            report.append(f"- **Cost per Log**: ${cost_per_log:.4f}")
        
        # Calculate tokens per second
        if total_time > 0:
            tokens_per_second = total_tokens / total_time
            report.append(f"- **Tokens per Second**: {tokens_per_second:.1f}")
        
        report.append("")
        
        # Evaluation approach comparison
        report.append("## Evaluation Approach Comparison")
        report.append("")
        
        # Try to separate Agent-as-Judge vs LLM-as-Judge costs
        agent_judge_cost = 0
        llm_judge_cost = 0
        
        for scenario, data in results.items():
            for detail in data['log_details']:
                if 'agent_judge' in detail['file']:
                    agent_judge_cost += detail['cost_usd']
                elif 'llm_judge' in detail['file']:
                    llm_judge_cost += detail['cost_usd']
        
        if agent_judge_cost > 0 and llm_judge_cost > 0:
            cost_ratio = agent_judge_cost / llm_judge_cost
            report.append(f"- **Agent-as-Judge Total Cost**: ${agent_judge_cost:.4f}")
            report.append(f"- **LLM-as-Judge Total Cost**: ${llm_judge_cost:.4f}")
            report.append(f"- **Cost Ratio (Agent/LLM)**: {cost_ratio:.1f}x")
        
        return "\n".join(report)
    
    def save_detailed_csv(self, results: Dict[str, Any], filename: str = "log_analysis_detailed.csv"):
        """Save detailed results to CSV."""
        rows = []
        
        for scenario, data in results.items():
            for detail in data['log_details']:
                rows.append({
                    'scenario': scenario,
                    'log_file': detail['file'],
                    'cost_usd': detail['cost_usd'],
                    'input_tokens': detail['input_tokens'],
                    'output_tokens': detail['output_tokens'],
                    'total_tokens': detail['total_tokens'],
                    'evaluation_time_seconds': detail['evaluation_time'],
                    'conversation_turns': detail['conversation_turns'],
                    'evaluation_type': 'agent_judge' if 'agent_judge' in detail['file'] else 'llm_judge'
                })
        
        if rows:
            df = pd.DataFrame(rows)
            df.to_csv(filename, index=False)
            print(f"📊 Detailed results saved to {filename}")

def main():
    """Main function to run the log analysis."""
    print("🚀 Starting Research Log Analysis")
    print("=" * 50)
    
    analyzer = LogAnalyzer()
    
    # Analyze all logs
    results = analyzer.analyze_all_logs()
    
    # Generate and save report
    report = analyzer.generate_summary_report(results)
    
    # Save report to file
    with open("log_analysis_report.md", "w") as f:
        f.write(report)
    
    # Save detailed CSV
    analyzer.save_detailed_csv(results)
    
    # Print summary to console
    print("\n" + "=" * 50)
    print("📋 ANALYSIS COMPLETE")
    print("=" * 50)
    
    total_cost = sum(scenario['total_cost_usd'] for scenario in results.values())
    total_tokens = sum(scenario['total_tokens'] for scenario in results.values())
    total_logs = sum(len(scenario['logs_analyzed']) for scenario in results.values())
    
    print(f"📊 Total Logs Analyzed: {total_logs}")
    print(f"💰 Total Cost: ${total_cost:.4f} USD")
    print(f"🔤 Total Tokens: {total_tokens:,}")
    print(f"📄 Report saved to: log_analysis_report.md")
    print(f"📊 Detailed CSV saved to: log_analysis_detailed.csv")
    
    # Print per-scenario summary
    print("\n📈 Per-Scenario Summary:")
    for scenario, data in results.items():
        print(f"  {scenario}: ${data['total_cost_usd']:.4f} ({len(data['logs_analyzed'])} logs)")

if __name__ == "__main__":
    main()

