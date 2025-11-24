"""
Implementation of a Cyclic Swarm Pattern for Red Team Operations

This module establishes a coordinated multi-agent system where specialized agents
collaborate on security assessment tasks. The pattern implements a directed graph
of agent relationships, where each agent can transfer context (message history) 
to another agent through handoff functions, creating a complete communication network
for comprehensive security analysis.
"""
from cai.agents.red_teamer import redteam_agent
from cai.agents.thought import thought_agent
from cai.agents.mail import dns_smtp_agent
from cai.sdk.agents import handoff


# Clone agents to avoid modifying the original instances
_redteam_agent_copy = redteam_agent.clone()
_thought_agent_copy = thought_agent.clone()
_dns_smtp_agent_copy = dns_smtp_agent.clone()

# Clear any existing handoffs to ensure independence
_redteam_agent_copy.handoffs = []
_thought_agent_copy.handoffs = []
_dns_smtp_agent_copy.handoffs = []

# Create handoffs using the SDK handoff function
_dns_smtp_handoff = handoff(
    agent=_dns_smtp_agent_copy,
    tool_description_override="Use for DNS scans and domain reconnaissance about DMARC and DKIM records"
)

_redteam_handoff = handoff(
    agent=_redteam_agent_copy,
    tool_description_override="Transfer to Red Team Agent for security assessment and exploitation tasks"
)

_thought_handoff = handoff(
    agent=_thought_agent_copy,
    tool_description_override="Transfer to Thought Agent for analysis and planning"
)

_thought_agent_copy.name = "Red team manager"
# Register handoff to enable inter-agent communication pathways
_redteam_agent_copy.handoffs.append(_dns_smtp_handoff)
_dns_smtp_agent_copy.handoffs.append(_redteam_handoff)
_thought_agent_copy.handoffs.append(_redteam_handoff)

# Initialize the swarm pattern with the thought agent as the entry point
redteam_swarm_pattern = _thought_agent_copy
redteam_swarm_pattern.pattern = "swarm"

# Mark all agents in the swarm with the pattern attribute
_redteam_agent_copy.pattern = "swarm"
_dns_smtp_agent_copy.pattern = "swarm"