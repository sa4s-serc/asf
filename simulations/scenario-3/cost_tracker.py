"""
Cost Tracking Utility for Scenario Simulations

Tracks LLM token usage, embedding costs, and latency metrics.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
import time


class CostTracker:
    """Track costs for LLM calls, embeddings, and latency."""

    # Pricing per 1M tokens (as of October 2025)
    PRICING = {
        "gpt-4o": {
            "input": 2.50,   # $2.50 per 1M input tokens
            "output": 10.00  # $10.00 per 1M output tokens
        },
        "gpt-4o-mini": {
            "input": 0.15,   # $0.15 per 1M input tokens
            "output": 0.60   # $0.60 per 1M output tokens
        },
        "text-embedding-3-small": {
            "tokens": 0.02   # $0.02 per 1M tokens
        },
        "text-embedding-3-large": {
            "tokens": 0.13   # $0.13 per 1M tokens
        }
    }

    def __init__(self):
        """Initialize cost tracker."""
        self.metrics = {
            "llm_calls": [],
            "latency": {},
            "summary": {
                "total_llm_cost": 0.0,
                "total_cost": 0.0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "total_execution_time_seconds": 0.0
            }
        }
        self.start_time = None
        self.timers = {}

    def start_timer(self, name: str):
        """Start a named timer."""
        self.timers[name] = time.time()

    def stop_timer(self, name: str) -> float:
        """Stop a named timer and return elapsed time."""
        if name not in self.timers:
            return 0.0
        elapsed = time.time() - self.timers[name]
        del self.timers[name]
        return elapsed

    def log_llm_call(self,
                     agent_name: str,
                     model: str,
                     input_tokens: int,
                     output_tokens: int,
                     latency_seconds: Optional[float] = None):
        """Log an LLM API call with token usage and cost."""

        # Get pricing for model
        pricing = self.PRICING.get(model, {"input": 0, "output": 0})

        # Calculate cost
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost

        call_data = {
            "agent": agent_name,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "input_cost_usd": round(input_cost, 6),
            "output_cost_usd": round(output_cost, 6),
            "total_cost_usd": round(total_cost, 6),
            "latency_seconds": latency_seconds,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        self.metrics["llm_calls"].append(call_data)

        # Update summary
        self.metrics["summary"]["total_input_tokens"] += input_tokens
        self.metrics["summary"]["total_output_tokens"] += output_tokens
        self.metrics["summary"]["total_tokens"] += input_tokens + output_tokens
        self.metrics["summary"]["total_llm_cost"] += total_cost

        return call_data


    def log_latency(self, operation: str, duration_seconds: float):
        """Log latency for a specific operation."""
        if operation not in self.metrics["latency"]:
            self.metrics["latency"][operation] = {
                "count": 0,
                "total_seconds": 0.0,
                "min_seconds": float('inf'),
                "max_seconds": 0.0,
                "avg_seconds": 0.0
            }

        stats = self.metrics["latency"][operation]
        stats["count"] += 1
        stats["total_seconds"] += duration_seconds
        stats["min_seconds"] = min(stats["min_seconds"], duration_seconds)
        stats["max_seconds"] = max(stats["max_seconds"], duration_seconds)
        stats["avg_seconds"] = stats["total_seconds"] / stats["count"]

    def start_execution(self):
        """Mark the start of scenario execution."""
        self.start_time = time.time()

    def end_execution(self):
        """Mark the end of scenario execution and finalize metrics."""
        if self.start_time:
            total_time = time.time() - self.start_time
            self.metrics["summary"]["total_execution_time_seconds"] = round(total_time, 2)

        # Finalize total cost
        self.metrics["summary"]["total_cost"] = round(
            self.metrics["summary"]["total_llm_cost"],
            6
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Return all tracked metrics."""
        return self.metrics

    def get_summary(self) -> Dict[str, Any]:
        """Return summary metrics only."""
        return self.metrics["summary"]

    def print_summary(self):
        """Print a human-readable summary of costs."""
        summary = self.metrics["summary"]

        print("="*70)
        print("COST SUMMARY")
        print("="*70)
        print(f"Total Execution Time: {summary['total_execution_time_seconds']:.2f}s")
        print()
        print(f"LLM Usage:")
        print(f"  Input Tokens:  {summary['total_input_tokens']:,}")
        print(f"  Output Tokens: {summary['total_output_tokens']:,}")
        print(f"  Total Tokens:  {summary['total_tokens']:,}")
        print(f"  Total Cost: ${summary['total_cost']:.6f}")
        print("="*70)
        print()

        # Per-agent breakdown
        if self.metrics["llm_calls"]:
            print("Per-Agent Breakdown:")
            agent_costs = {}
            for call in self.metrics["llm_calls"]:
                agent = call["agent"]
                if agent not in agent_costs:
                    agent_costs[agent] = {
                        "calls": 0,
                        "tokens": 0,
                        "cost": 0.0
                    }
                agent_costs[agent]["calls"] += 1
                agent_costs[agent]["tokens"] += call["total_tokens"]
                agent_costs[agent]["cost"] += call["total_cost_usd"]

            for agent, stats in sorted(agent_costs.items()):
                print(f"  {agent}:")
                print(f"    Calls: {stats['calls']}")
                print(f"    Tokens: {stats['tokens']:,}")
                print(f"    Cost: ${stats['cost']:.6f}")
            print()
