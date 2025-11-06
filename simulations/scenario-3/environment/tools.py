"""
Tool definitions for Scenario 3: Performance Degradation RCA

Provides fine-grained tools with string formatting (following scenario-2 pattern).
"""

import json
from moya.tools.tool import Tool
from moya.tools.tool_registry import ToolRegistry
from .performance_api import PerformanceAPI


def format_metric_result(result: dict) -> str:
    """Format metric dict as readable string."""
    if "error" in result:
        return f"Error: {result['error']}"

    lines = []
    for key, value in result.items():
        if key == "error_types" and isinstance(value, dict):
            lines.append(f"{key}:")
            for error_type, percent in value.items():
                lines.append(f"  - {error_type}: {percent}%")
        elif isinstance(value, (dict, list)):
            lines.append(f"{key}: {json.dumps(value, indent=2)}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def create_performance_tools(api: PerformanceAPI) -> ToolRegistry:
    """Create tools for Performance Diagnostics Agent."""
    tool_registry = ToolRegistry()

    # Wrapper functions that return strings
    def get_response_time_metrics_wrapper(service_name: str, timerange: str = "1h") -> str:
        """Get response time metrics for a service.

        Parameters:
        - service_name: Service name (e.g., 'payment-service')
        - timerange: Time range like '1h', '24h', '7d'
        """
        result = api.get_service_metrics(service_name, "response_time", timerange)
        return format_metric_result(result)

    def get_error_rate_metrics_wrapper(service_name: str, timerange: str = "1h") -> str:
        """Get error rate metrics for a service.

        Parameters:
        - service_name: Service name (e.g., 'payment-service')
        - timerange: Time range like '1h', '24h'
        """
        result = api.get_service_metrics(service_name, "error_rate", timerange)
        return format_metric_result(result)

    def get_cpu_metrics_wrapper(service_name: str, timerange: str = "1h") -> str:
        """Get CPU utilization metrics for a service.

        Parameters:
        - service_name: Service name (e.g., 'payment-service')
        - timerange: Time range like '1h', '24h'
        """
        result = api.get_service_metrics(service_name, "cpu", timerange)
        return format_metric_result(result)

    def get_memory_metrics_wrapper(service_name: str, timerange: str = "1h") -> str:
        result = api.get_service_metrics(service_name, "memory", timerange)
        return format_metric_result(result)

    def get_network_metrics_wrapper(service_name: str, timerange: str = "1h") -> str:
        result = api.get_service_metrics(service_name, "network", timerange)
        return format_metric_result(result)

    def get_connection_metrics_wrapper(service_name: str, timerange: str = "1h") -> str:
        result = api.get_service_metrics(service_name, "connections", timerange)
        return format_metric_result(result)

    def get_database_metrics_wrapper(database_name: str) -> str:
        result = api.get_database_metrics(database_name)
        return format_metric_result(result)

    def get_application_logs_wrapper(service_name: str, level: str = None,
                                     timerange: str = "1h", limit: int = 10) -> str:
        logs = api.get_application_logs(service_name, level, timerange, limit)
        if not logs:
            return f"No logs found for service '{service_name}'"

        lines = [f"Application logs for '{service_name}' (last {limit}):"]
        for log in logs:
            lines.append(f"\n[{log['timestamp']}] {log['level']} - {log['instance']}")
            lines.append(f"  {log['message']}")
            if 'details' in log:
                lines.append(f"  Details: {log['details']}")
        return "\n".join(lines)

    def get_service_info_wrapper(service_name: str) -> str:
        result = api.get_service_info(service_name)
        return format_metric_result(result)

    def scale_service_wrapper(service_name: str, target_count: int, reason: str) -> str:
        result = api.scale_service(service_name, target_count, reason)
        return format_metric_result(result)

    # Register tools with parameter descriptions
    tool_registry.register_tool(Tool(
        name="get_response_time_metrics",
        function=get_response_time_metrics_wrapper,
        parameters={
            "service_name": {"type": "string", "description": "Service name (e.g., 'payment-service')"},
            "timerange": {"type": "string", "description": "Time range like '1h', '24h', '7d' (default: '1h')"}
        }
    ))
    tool_registry.register_tool(Tool(
        name="get_error_rate_metrics",
        function=get_error_rate_metrics_wrapper,
        parameters={
            "service_name": {"type": "string", "description": "Service name (e.g., 'payment-service')"},
            "timerange": {"type": "string", "description": "Time range like '1h', '24h' (default: '1h')"}
        }
    ))
    tool_registry.register_tool(Tool(
        name="get_cpu_metrics",
        function=get_cpu_metrics_wrapper,
        parameters={
            "service_name": {"type": "string", "description": "Service name (e.g., 'payment-service')"},
            "timerange": {"type": "string", "description": "Time range like '1h', '24h' (default: '1h')"}
        }
    ))
    tool_registry.register_tool(Tool(
        name="get_memory_metrics",
        function=get_memory_metrics_wrapper,
        parameters={
            "service_name": {"type": "string", "description": "Service name (e.g., 'payment-service')"},
            "timerange": {"type": "string", "description": "Time range like '1h', '24h' (default: '1h')"}
        }
    ))
    tool_registry.register_tool(Tool(
        name="get_network_metrics",
        function=get_network_metrics_wrapper,
        parameters={
            "service_name": {"type": "string", "description": "Service name (e.g., 'payment-service')"},
            "timerange": {"type": "string", "description": "Time range like '1h', '24h' (default: '1h')"}
        }
    ))
    tool_registry.register_tool(Tool(
        name="get_connection_metrics",
        function=get_connection_metrics_wrapper,
        parameters={
            "service_name": {"type": "string", "description": "Service name (e.g., 'payment-service')"},
            "timerange": {"type": "string", "description": "Time range like '1h', '24h' (default: '1h')"}
        }
    ))
    tool_registry.register_tool(Tool(
        name="get_database_metrics",
        function=get_database_metrics_wrapper,
        parameters={
            "database_name": {"type": "string", "description": "Database name (e.g., 'prod-payment-db')"}
        }
    ))
    tool_registry.register_tool(Tool(
        name="get_application_logs",
        function=get_application_logs_wrapper,
        parameters={
            "service_name": {"type": "string", "description": "Service name (e.g., 'payment-service')"},
            "level": {"type": "string", "description": "Log level filter: 'ERROR', 'WARN', 'INFO' (optional)"},
            "timerange": {"type": "string", "description": "Time range like '1h', '24h' (default: '1h')"},
            "limit": {"type": "integer", "description": "Max number of log entries (default: 10)"}
        }
    ))
    tool_registry.register_tool(Tool(
        name="get_service_info",
        function=get_service_info_wrapper,
        parameters={
            "service_name": {"type": "string", "description": "Service name (e.g., 'payment-service')"}
        }
    ))
    tool_registry.register_tool(Tool(
        name="scale_service",
        function=scale_service_wrapper,
        parameters={
            "service_name": {"type": "string", "description": "Service name to scale"},
            "target_count": {"type": "integer", "description": "Target instance count"},
            "reason": {"type": "string", "description": "Reason for scaling"}
        }
    ))

    return tool_registry


def create_security_tools(api: PerformanceAPI) -> ToolRegistry:
    """Create tools for Security Configuration Agent."""
    tool_registry = ToolRegistry()

    def get_security_group_details_wrapper(security_group_id: str) -> str:
        result = api.get_security_group_details(security_group_id)
        if "error" in result:
            return f"Error: {result['error']}"

        lines = [f"Security Group: {result['id']} ({result['name']})"]
        lines.append(f"Description: {result['description']}")
        lines.append(f"VPC: {result['vpc_id']}")
        lines.append("\nInbound Rules:")
        for rule in result['inbound_rules']:
            lines.append(f"  - Port {rule['port']} ({rule['protocol']}) from {rule['source']}")
            lines.append(f"    Description: {rule['description']}")
        lines.append("\nOutbound Rules:")
        for rule in result['outbound_rules']:
            lines.append(f"  - Port {rule['port']} ({rule['protocol']}) to {rule['destination']}")
        return "\n".join(lines)

    def check_network_connectivity_wrapper(source: str, destination: str, port: int) -> str:
        result = api.check_network_connectivity(source, destination, port)
        return format_metric_result(result)

    def get_network_topology_wrapper(vpc_id: str = "vpc-main") -> str:
        result = api.get_network_topology(vpc_id)
        lines = [f"VPC: {result['vpc_id']} ({result['vpc_cidr']})"]
        lines.append("\nSubnets:")
        for name, config in result['subnets'].items():
            lines.append(f"  {name}: {config['cidr']} (AZ: {config['availability_zone']})")
            lines.append(f"    Resources: {', '.join(config['resources'])}")
        return "\n".join(lines)

    def update_security_group_wrapper(security_group_id: str, action: str, rule: dict) -> str:
        result = api.update_security_group(security_group_id, action, rule)
        return format_metric_result(result)

    # Register tools with proper parameter descriptions
    tool_registry.register_tool(Tool(
        name="get_security_group_details",
        function=get_security_group_details_wrapper,
        parameters={
            "security_group_id": {"type": "string", "description": "Security group ID (e.g., 'sg-abc123')"}
        }
    ))

    tool_registry.register_tool(Tool(
        name="check_network_connectivity",
        function=check_network_connectivity_wrapper,
        parameters={
            "source": {"type": "string", "description": "Source CIDR or subnet name (e.g., '10.0.2.0/24' or 'app_tier')"},
            "destination": {"type": "string", "description": "Destination resource or subnet (e.g., 'prod-payment-db' or 'database_tier')"},
            "port": {"type": "integer", "description": "Port number to check (e.g., 5432 for PostgreSQL)"}
        }
    ))

    tool_registry.register_tool(Tool(
        name="get_network_topology",
        function=get_network_topology_wrapper,
        parameters={
            "vpc_id": {"type": "string", "description": "VPC ID (default: 'vpc-main')"}
        }
    ))

    tool_registry.register_tool(Tool(
        name="update_security_group",
        function=update_security_group_wrapper,
        parameters={
            "security_group_id": {"type": "string", "description": "Security group ID to update (e.g., 'sg-abc123')"},
            "action": {"type": "string", "description": "Action: 'add_inbound' or 'remove_inbound'"},
            "rule": {"type": "object", "description": "Rule specification with port, protocol, source, description"}
        }
    ))

    tool_registry.register_tool(Tool(name="get_recent_changes", function=api.get_recent_changes))  # Already returns string

    return tool_registry


def create_rca_tools(api: PerformanceAPI) -> ToolRegistry:
    """Create tools for RCA Orchestrator Agent.

    RCA focuses on correlation and synthesis only.
    """
    tool_registry = ToolRegistry()

    tool_registry.register_tool(Tool(name="correlate_events", function=api.correlate_events))
    tool_registry.register_tool(Tool(name="get_recent_changes", function=api.get_recent_changes))

    return tool_registry
