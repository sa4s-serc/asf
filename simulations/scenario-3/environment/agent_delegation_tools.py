"""
Agent Delegation Tools for Scenario 3

Enables RCA agent to delegate tasks to specialized Performance and Security agents.
Agents are exposed as tools that can be called.
"""

from moya.agents.agent import Agent
from moya.tools.tool import Tool
from moya.tools.tool_registry import ToolRegistry


class AgentDelegationTools:
    """Provides tools for agents to delegate to other agents."""

    def __init__(self, performance_agent: Agent, security_agent: Agent, api):
        """
        Initialize delegation tools.

        Args:
            performance_agent: Performance diagnostics agent
            security_agent: Security configuration agent
            api: PerformanceAPI instance for logging
        """
        self.performance_agent = performance_agent
        self.security_agent = security_agent
        self.api = api
        self.delegation_count = 0

    def ask_performance_agent(self, task: str) -> str:
        """Delegate a performance analysis task to the Performance Diagnostics Agent.

        Use this when you need to:
        - Analyze performance metrics (response time, error rate, CPU, memory)
        - Get application logs and error details
        - Check database performance
        - Identify performance symptoms

        Parameters:
        - task: The performance analysis request (e.g., "Check current performance metrics for payment-service and identify error patterns")

        Returns:
        - Detailed performance analysis from the Performance Agent
        """
        self.delegation_count += 1
        thread_id = f"perf_delegation_{self.delegation_count}"

        # Log this delegation as a tool call
        self.api.log_tool_call("ask_performance_agent", {"task": task})

        try:
            response = self.performance_agent.handle_message(task, thread_id=thread_id)
            return f"[Performance Agent Response]\n\n{response}"
        except Exception as e:
            return f"Error delegating to Performance Agent: {str(e)}"

    def ask_security_agent(self, task: str) -> str:
        """Delegate a security/configuration task to the Security Configuration Agent.

        Use this when you need to:
        - Check security group configurations
        - Verify network connectivity
        - Investigate recent configuration changes
        - Update security group rules (remediation)
        - Check network topology

        Parameters:
        - task: The security/configuration request (e.g., "Check security group sg-abc123 configuration and verify connectivity from 10.0.2.0/24 to prod-payment-db port 5432")

        Returns:
        - Security analysis or remediation results from the Security Agent
        """
        self.delegation_count += 1
        thread_id = f"sec_delegation_{self.delegation_count}"

        # Log this delegation as a tool call
        self.api.log_tool_call("ask_security_agent", {"task": task})

        try:
            response = self.security_agent.handle_message(task, thread_id=thread_id)
            return f"[Security Agent Response]\n\n{response}"
        except Exception as e:
            return f"Error delegating to Security Agent: {str(e)}"


def create_agent_delegation_tools(
    performance_agent: Agent,
    security_agent: Agent,
    api
) -> ToolRegistry:
    """
    Create a tool registry with agent delegation tools.

    Args:
        performance_agent: Performance diagnostics agent to delegate to
        security_agent: Security configuration agent to delegate to
        api: PerformanceAPI for logging

    Returns:
        ToolRegistry with agent delegation tools
    """
    delegator = AgentDelegationTools(performance_agent, security_agent, api)
    tool_registry = ToolRegistry()

    # Register agent delegation tools
    tool_registry.register_tool(Tool(
        name="ask_performance_agent",
        function=delegator.ask_performance_agent,
        parameters={
            "task": {
                "type": "string",
                "description": "Performance analysis task to delegate (e.g., 'Analyze response time and error patterns for payment-service')"
            }
        }
    ))

    tool_registry.register_tool(Tool(
        name="ask_security_agent",
        function=delegator.ask_security_agent,
        parameters={
            "task": {
                "type": "string",
                "description": "Security/configuration task to delegate (e.g., 'Check security group sg-abc123 and fix any connectivity issues')"
            }
        }
    ))

    return tool_registry
