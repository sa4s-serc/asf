"""
Tool definitions for Scenario 3: Performance Degradation RCA

Provides fine-grained tools for Performance, Security, and RCA agents.
"""

from moya.tools.tool import Tool
from moya.tools.tool_registry import ToolRegistry
from .performance_api import PerformanceAPI


def create_performance_tools(api: PerformanceAPI) -> ToolRegistry:
    """Create tools for Performance Diagnostics Agent.

    These tools focus on gathering performance metrics and identifying symptoms.
    """
    tool_registry = ToolRegistry()

    # Metric retrieval tools (fine-grained, not generic "get_metrics")
    tool_registry.register_tool(Tool(
        name="get_response_time_metrics",
        function=lambda service_name, timerange="1h": api.get_service_metrics(
            service_name, "response_time", timerange
        ),
        parameters={
            "service_name": {"type": "string", "description": "Service name"},
            "timerange": {"type": "string", "description": "Time range (default: 1h)"}
        }
    ))

    tool_registry.register_tool(Tool(
        name="get_error_rate_metrics",
        function=lambda service_name, timerange="1h": api.get_service_metrics(
            service_name, "error_rate", timerange
        ),
        parameters={
            "service_name": {"type": "string", "description": "Service name"},
            "timerange": {"type": "string", "description": "Time range (default: 1h)"}
        }
    ))

    tool_registry.register_tool(Tool(
        name="get_cpu_metrics",
        function=lambda service_name, timerange="1h": api.get_service_metrics(
            service_name, "cpu", timerange
        ),
        parameters={
            "service_name": {"type": "string", "description": "Service name"},
            "timerange": {"type": "string", "description": "Time range (default: 1h)"}
        }
    ))

    tool_registry.register_tool(Tool(
        name="get_memory_metrics",
        function=lambda service_name, timerange="1h": api.get_service_metrics(
            service_name, "memory", timerange
        ),
        parameters={
            "service_name": {"type": "string", "description": "Service name"},
            "timerange": {"type": "string", "description": "Time range (default: 1h)"}
        }
    ))

    tool_registry.register_tool(Tool(
        name="get_network_metrics",
        function=lambda service_name, timerange="1h": api.get_service_metrics(
            service_name, "network", timerange
        ),
        parameters={
            "service_name": {"type": "string", "description": "Service name"},
            "timerange": {"type": "string", "description": "Time range (default: 1h)"}
        }
    ))

    tool_registry.register_tool(Tool(
        name="get_connection_metrics",
        function=lambda service_name, timerange="1h": api.get_service_metrics(
            service_name, "connections", timerange
        ),
        parameters={
            "service_name": {"type": "string", "description": "Service name"},
            "timerange": {"type": "string", "description": "Time range (default: 1h)"}
        }
    ))

    # Database metrics
    tool_registry.register_tool(Tool(
        name="get_database_metrics",
        function=api.get_database_metrics
    ))

    # Application logs
    tool_registry.register_tool(Tool(
        name="get_application_logs",
        function=api.get_application_logs
    ))

    # Service info
    tool_registry.register_tool(Tool(
        name="get_service_info",
        function=api.get_service_info
    ))

    # Scaling (wrong action but agent might choose it)
    tool_registry.register_tool(Tool(
        name="scale_service",
        function=api.scale_service
    ))

    return tool_registry


def create_security_tools(api: PerformanceAPI) -> ToolRegistry:
    """Create tools for Security Configuration Agent.

    These tools focus on security groups, network configuration, and change tracking.
    """
    tool_registry = ToolRegistry()

    # Security group tools
    tool_registry.register_tool(Tool(
        name="get_security_group_details",
        function=api.get_security_group_details
    ))

    tool_registry.register_tool(Tool(
        name="update_security_group",
        function=api.update_security_group
    ))

    # Network connectivity checks
    tool_registry.register_tool(Tool(
        name="check_network_connectivity",
        function=api.check_network_connectivity
    ))

    tool_registry.register_tool(Tool(
        name="get_network_topology",
        function=api.get_network_topology
    ))

    # Change tracking
    tool_registry.register_tool(Tool(
        name="get_recent_changes",
        function=api.get_recent_changes
    ))

    return tool_registry


def create_rca_tools(api: PerformanceAPI) -> ToolRegistry:
    """Create tools for RCA Orchestrator Agent.

    These tools focus on correlation, analysis, and coordination.
    """
    tool_registry = ToolRegistry()

    # Event correlation
    tool_registry.register_tool(Tool(
        name="correlate_events",
        function=api.correlate_events
    ))

    # Access to recent changes for RCA agent too
    tool_registry.register_tool(Tool(
        name="get_recent_changes",
        function=api.get_recent_changes
    ))

    # Can also check connectivity for validation
    tool_registry.register_tool(Tool(
        name="check_network_connectivity",
        function=api.check_network_connectivity
    ))

    # Can apply fixes if needed
    tool_registry.register_tool(Tool(
        name="update_security_group",
        function=api.update_security_group
    ))

    return tool_registry
