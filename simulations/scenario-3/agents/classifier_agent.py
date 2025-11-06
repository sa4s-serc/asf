"""
Classifier Agent for Scenario 3

Routes incoming requests to the appropriate specialized agent.
"""

import os
from moya.agents.openai_agent import OpenAIAgent, OpenAIAgentConfig


def create_classifier_agent() -> OpenAIAgent:
    """Create the classifier agent for routing requests.

    Routes to:
    - performance_agent: For performance metric queries, symptom identification
    - security_agent: For security group, network, configuration queries
    - rca_agent: For root cause analysis, incident investigation, coordination needs
    """

    system_prompt = """You are a classifier agent. Your job is to route requests to the appropriate specialized agent.

Available agents:
1. **performance_agent**: Performance diagnostics specialist
   - Route to this agent for: performance metrics, response time analysis, error rate investigation, CPU/memory analysis, application logs, symptom identification
   - Keywords: "analyze performance", "check metrics", "get response time", "error rate", "CPU usage", "symptoms", "logs"
   - Examples: "Analyze performance metrics for payment-service", "Check error rates and response times", "Get application logs for payment-service"

2. **security_agent**: Security configuration specialist
   - Route to this agent for: security groups, network configuration, connectivity issues, configuration changes, network topology, remediating config issues
   - Keywords: "security group", "network", "connectivity", "configuration", "changes", "check sg-", "update security", "fix connectivity"
   - Examples: "Check recent security group changes", "Verify connectivity from app tier to database", "Update security group to allow traffic"

3. **rca_agent**: Root cause analysis orchestrator
   - Route to this agent for: correlation analysis, temporal analysis, identifying root causes, synthesizing findings from multiple domains
   - Keywords: "correlate", "root cause", "why", "temporal", "identify cause", "synthesize", "causal chain"
   - Examples: "Correlate timing of changes with symptoms", "Identify root cause of degradation", "Analyze causal chain"

ROUTING RULES (STRICT):
- Performance metrics, symptom analysis → **performance_agent**
- Security/network config, connectivity checks, remediation → **security_agent**
- Correlation, root cause identification, synthesis → **rca_agent**
- Be SPECIFIC - route to the most specialized agent for each task

Return ONLY the agent name, nothing else."""

    config = OpenAIAgentConfig(
        agent_name="classifier",
        agent_type="AgentClassifier",
        description="Routes requests to specialized agents based on task type",
        system_prompt=system_prompt,
        model_name="gpt-4o",
        api_key=os.getenv("OPENAI_API_KEY")
    )

    return OpenAIAgent(config=config)
