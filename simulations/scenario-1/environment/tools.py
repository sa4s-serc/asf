"""
Tool definitions for Scenario 1: Cost Optimization

Wraps AWS API functions as MOYA tools.
"""

from moya.tools.tool import Tool
from moya.tools.tool_registry import ToolRegistry
from .aws_api import AWSAPI


def create_cost_optimization_tools(aws_api: AWSAPI) -> ToolRegistry:
    """Create and register all tools for cost optimization scenario.

    Parameters:
        - aws_api: Instance of AWSAPI to use for tool operations
    """

    tool_registry = ToolRegistry()

    # Cost analysis tools
    tool_registry.register_tool(Tool(
        name="get_cost_breakdown",
        function=aws_api.get_cost_breakdown
    ))

    tool_registry.register_tool(Tool(
        name="analyze_utilization",
        function=aws_api.analyze_utilization
    ))

    # Action tools
    # Note: Policy, metadata, and dependency information is now stored in memory
    # Agent must use query_memory() to retrieve this context
    tool_registry.register_tool(Tool(
        name="terminate_instances",
        function=aws_api.terminate_instances,
        parameters={
            "instance_ids": {
                "type": "array",
                "description": "Array of instance IDs to terminate",
                "items": {"type": "string"}
            }
        }
    ))

    tool_registry.register_tool(Tool(
        name="create_approval_request",
        function=aws_api.create_approval_request,
        parameters={
            "instance_ids": {
                "type": "array",
                "description": "Array of instance IDs requiring approval",
                "items": {"type": "string"}
            },
            "reason": {
                "type": "string",
                "description": "Reason for the change"
            },
            "cost_benefit": {
                "type": "string",
                "description": "Expected cost benefit"
            }
        }
    ))

    return tool_registry
