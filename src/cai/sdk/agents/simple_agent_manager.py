"""
Simple Agent Manager - Manages the single active agent instance.

This module ensures that only ONE agent instance exists at a time,
unless explicitly configured for parallel execution.
"""

import weakref
from typing import Optional, Dict, Any

class SimpleAgentManager:
    """Manages the single active agent instance."""
    
    def __init__(self):
        self._active_agent = None  # The ONE active agent
        self._agent_id = "P1"  # Default ID
        self._message_history: Dict[str, list] = {}  # Agent name -> history
        self._agent_registry: Dict[str, str] = {}  # Agent name -> ID mapping
        self._id_counter = 0  # Counter for generating IDs
        self._parallel_agents: Dict[str, Any] = {}  # ID -> agent ref for parallel mode
        self._pending_history_transfer = None  # Temporary storage for history transfer
        self._active_agent_name = None  # Track the currently active agent name
        self._swarm_agents: Dict[str, str] = {}  # Track swarm pattern agents: agent_name -> ID
        self._swarm_counter = 0  # Counter for swarm agent IDs
    
    def set_active_agent(self, agent, agent_name: str, agent_id: str = None):
        """Set the active agent instance."""
        # CRITICAL: Always use the agent's proper name, not the agent key
        # This prevents duplicate registrations like "blueteam_agent" and "Blue Team Agent"
        if hasattr(agent, 'name') and agent.name:
            agent_name = agent.name
        
        # In single agent mode, use switch_to_single_agent for proper cleanup
        if not self._parallel_agents and not agent_id:
            # If we're in single agent mode and no explicit ID is provided
            # Check if this is actually a switch (different agent than current)
            if self._active_agent_name and self._active_agent_name != agent_name:
                # This is a switch - use the proper method
                self.switch_to_single_agent(agent, agent_name)
                return
        
        # Otherwise, proceed with normal set_active_agent logic
        self._active_agent = weakref.ref(agent) if agent else None
        self._active_agent_name = agent_name  # Track the active agent name
        
        # Check if this agent is part of a swarm pattern
        is_swarm_agent = False
        if hasattr(agent, 'pattern') and agent.pattern == 'swarm':
            is_swarm_agent = True
        
        # In single agent mode, check for swarm patterns
        if not self._parallel_agents:
            if is_swarm_agent:
                # For swarm agents, assign unique IDs like P1-1, P1-2, etc.
                if agent_name not in self._swarm_agents:
                    self._swarm_counter += 1
                    swarm_id = f"P1-{self._swarm_counter}"
                    self._swarm_agents[agent_name] = swarm_id
                    self._agent_registry[agent_name] = swarm_id
                else:
                    swarm_id = self._swarm_agents[agent_name]
                self._agent_id = swarm_id
            else:
                # Non-swarm single agents still get P1
                self._agent_id = "P1"
                self._agent_registry[agent_name] = "P1"
        else:
            # For parallel mode, use provided ID or generate new one
            if agent_id:
                self._agent_id = agent_id
            else:
                # Only increment counter for new agents in parallel mode
                if agent_name not in self._agent_registry:
                    self._id_counter += 1
                    agent_id = f"P{self._id_counter}"
                else:
                    agent_id = self._agent_registry[agent_name]
                self._agent_id = agent_id
            self._agent_registry[agent_name] = self._agent_id
        
        # Initialize message history for this agent if needed
        if agent_name not in self._message_history:
            # Check if the agent's model already has a history and use that reference
            if hasattr(agent, 'model') and hasattr(agent.model, 'message_history'):
                self._message_history[agent_name] = agent.model.message_history
            else:
                self._message_history[agent_name] = []
    
    def get_active_agent(self):
        """Get the active agent instance."""
        if self._active_agent:
            return self._active_agent()
        return None
    
    def get_agent_id(self) -> str:
        """Get the ID of the active agent."""
        return self._agent_id
    
    def get_message_history(self, agent_name: str) -> list:
        """Get message history for an agent."""
        return self._message_history.get(agent_name, [])
    
    def add_to_history(self, agent_name: str, message: dict):
        """Add a message to agent's history."""
        if agent_name not in self._message_history:
            self._message_history[agent_name] = []
        self._message_history[agent_name].append(message)
    
    def clear_history(self, agent_name: str):
        """Clear history for an agent."""
        if agent_name in self._message_history:
            # Clear the list in-place to maintain the same reference
            # This is critical when the model and manager share the same list
            self._message_history[agent_name].clear()
        
        # Also clear the active agent's model instance history if it matches
        # This handles cases where they don't share the same reference
        if self._active_agent and self._active_agent_name == agent_name:
            agent = self._active_agent()
            if agent and hasattr(agent, 'model') and hasattr(agent.model, 'message_history'):
                agent.model.message_history.clear()
    
    def clear_all_histories(self):
        """Clear all message histories."""
        self._message_history.clear()
    
    def get_all_histories(self) -> Dict[str, list]:
        """Get all agent histories."""
        # Clean up duplicates first in single agent mode
        if not self._parallel_agents:
            self._cleanup_single_agent_duplicates()
        
        # Clean up any duplicate IDs in parallel mode
        if self._parallel_agents:
            self._cleanup_duplicate_ids()
        
        # Return histories for all registered agents
        result = {}
        
        # In single agent mode
        if not self._parallel_agents:
            # In single agent mode, ONLY show the ONE active agent
            if self._active_agent_name and self._active_agent_name in self._agent_registry:
                agent_id = self._agent_registry[self._active_agent_name]
                history = self._message_history.get(self._active_agent_name, [])
                result[f"{self._active_agent_name} [{agent_id}]"] = history
            # That's it - no other agents in single agent mode
        else:
            # In parallel mode, show all registered agents
            for agent_name, agent_id in sorted(self._agent_registry.items()):
                history = self._message_history.get(agent_name, [])
                result[f"{agent_name} [{agent_id}]"] = history
        
        return result

    def get_agent_by_id(self, agent_id: str) -> Optional[str]:
        """Get agent name by ID."""
        # Check all registered agents
        for agent_name, aid in self._agent_registry.items():
            if aid == agent_id:
                return agent_name
        return None
    
    def get_id_by_name(self, agent_name: str) -> Optional[str]:
        """Get ID by agent name."""
        return self._agent_registry.get(agent_name)
    
    def reset_registry(self):
        """Reset the agent registry (for testing or clean start)."""
        # Keep agents with message history
        agents_to_keep = {}
        for agent_name, agent_id in self._agent_registry.items():
            if self._message_history.get(agent_name):
                agents_to_keep[agent_name] = agent_id
        
        self._agent_registry = agents_to_keep
        self._id_counter = 0
        self._agent_id = "P1"
        self._parallel_agents.clear()
        self._swarm_agents.clear()
        self._swarm_counter = 0
    
    def set_parallel_agent(self, agent_id: str, agent, agent_name: str):
        """Register a parallel agent."""
        # CRITICAL: Always use the agent's proper name, not the agent key
        # This prevents duplicate registrations like "blueteam_agent" and "Blue Team Agent"
        if hasattr(agent, 'name') and agent.name:
            agent_name = agent.name
        
        # Check if this ID is already registered to a different agent
        existing_agent_name = self.get_agent_by_id(agent_id)
        if existing_agent_name and existing_agent_name != agent_name:
            # Don't overwrite existing registration - just update the agent reference
            self._parallel_agents[agent_id] = weakref.ref(agent) if agent else None
            return
        
        self._parallel_agents[agent_id] = weakref.ref(agent) if agent else None
        self._agent_registry[agent_name] = agent_id
        
        # Initialize message history for this agent if needed
        if agent_name not in self._message_history:
            # Check if the agent's model already has a history and use that reference
            if hasattr(agent, 'model') and hasattr(agent.model, 'message_history'):
                self._message_history[agent_name] = agent.model.message_history
            else:
                self._message_history[agent_name] = []
    
    def clear_parallel_agents(self):
        """Clear all parallel agents (when switching to single agent mode)."""
        self._parallel_agents.clear()
        
    def clear_all_agents_except_pending_history(self):
        """Clear ALL agents from registry but preserve any pending history transfer.
        
        This is used when switching from parallel to single agent mode to ensure
        no lingering agents remain active.
        """
        # Store any pending history transfer
        pending_history = self._pending_history_transfer
        
        # Store ALL existing message histories before clearing
        # This preserves histories from agents that existed before parallel mode
        existing_histories = dict(self._message_history)
        
        # Clear everything
        self._agent_registry.clear()
        self._parallel_agents.clear()
        self._active_agent = None
        self._active_agent_name = None
        self._agent_id = "P1"
        self._id_counter = 0
        
        # Restore the message histories - they are needed for history preservation
        self._message_history = existing_histories
        
        # Restore pending history if any
        self._pending_history_transfer = pending_history
    
    def get_active_agents(self) -> Dict[str, str]:
        """Get only truly active agents with their IDs."""
        active = {}
        
        # In single agent mode
        if not self._parallel_agents:
            # Use the tracked active agent name
            if self._active_agent_name and self._active_agent_name in self._agent_registry:
                active[self._active_agent_name] = self._agent_registry[self._active_agent_name]
        else:
            # In parallel mode, check parallel agents
            for aid, agent_ref in list(self._parallel_agents.items()):
                if agent_ref and agent_ref():
                    # Find agent name for this ID
                    for name, registered_id in self._agent_registry.items():
                        if registered_id == aid:
                            active[name] = aid
                            break
        
        return active
    
    def get_registered_agents(self) -> Dict[str, str]:
        """Get all registered agents, whether active or not."""
        return dict(self._agent_registry)
    
    def _cleanup_stale_registrations(self):
        """Clean up stale agent registrations that no longer have active instances."""
        active_agents = self.get_active_agents()
        
        # Find agents to remove (not active and have no message history)
        to_remove = []
        for agent_name, agent_id in list(self._agent_registry.items()):
            if agent_name not in active_agents and len(self._message_history.get(agent_name, [])) == 0:
                to_remove.append(agent_name)
        
        # Remove stale registrations
        for agent_name in to_remove:
            del self._agent_registry[agent_name]
            if agent_name in self._message_history:
                del self._message_history[agent_name]
        
        # Reset ID counter to highest used ID
        if self._agent_registry:
            max_id = 0
            for agent_id in self._agent_registry.values():
                if agent_id.startswith("P") and agent_id[1:].isdigit():
                    max_id = max(max_id, int(agent_id[1:]))
            self._id_counter = max_id
    
    def _cleanup_single_agent_duplicates(self):
        """Clean up duplicate P1 entries in single agent mode."""
        if self._parallel_agents:
            return  # Only cleanup in single agent mode
        
        # In single agent mode, there should be ONLY ONE agent
        if not self._active_agent_name:
            return
        
        # Remove ALL agents except the active one
        agents_to_remove = []
        for agent_name in list(self._agent_registry.keys()):
            if agent_name != self._active_agent_name:
                agents_to_remove.append(agent_name)
        
        for agent_name in agents_to_remove:
            del self._agent_registry[agent_name]
            if agent_name in self._message_history:
                del self._message_history[agent_name]
        
        return
    
    def _cleanup_duplicate_ids(self):
        """Clean up agents with duplicate IDs in parallel mode."""
        # Build a map of ID to agent names
        id_to_agents = {}
        for agent_name, agent_id in list(self._agent_registry.items()):
            if agent_id not in id_to_agents:
                id_to_agents[agent_id] = []
            id_to_agents[agent_id].append(agent_name)
        
        # For each ID with duplicates, keep only the one that should be active according to PARALLEL_CONFIGS
        from cai.repl.commands.parallel import PARALLEL_CONFIGS
        
        for agent_id, agent_names in id_to_agents.items():
            if len(agent_names) > 1:
                # Find which agent should have this ID based on PARALLEL_CONFIGS
                correct_agent_name = None
                
                # Check parallel configs for the correct mapping
                for config in PARALLEL_CONFIGS:
                    if config.id == agent_id:
                        # For pattern-based configs, we need to resolve to the actual agent name
                        if config.agent_name.endswith("_pattern"):
                            from cai.agents.patterns import get_pattern
                            pattern = get_pattern(config.agent_name)
                            if pattern and hasattr(pattern, 'entry_agent'):
                                correct_agent_name = getattr(pattern.entry_agent, "name", None)
                                break
                        else:
                            from cai.agents import get_available_agents
                            available_agents = get_available_agents()
                            if config.agent_name in available_agents:
                                agent = available_agents[config.agent_name]
                                correct_agent_name = getattr(agent, "name", config.agent_name)
                                break
                
                # If we found the correct agent, keep only that one
                if correct_agent_name and correct_agent_name in agent_names:
                    for name in agent_names:
                        if name != correct_agent_name:
                            del self._agent_registry[name]
                else:
                    # Otherwise, keep the first one with an active parallel agent
                    active_name = None
                    for name in agent_names:
                        if agent_id in self._parallel_agents and self._parallel_agents[agent_id]:
                            agent_ref = self._parallel_agents[agent_id]
                            if agent_ref():  # Check if weakref is still valid
                                active_name = name
                                break
                    
                    if not active_name:
                        active_name = agent_names[0]
                    
                    # Remove all others
                    for name in agent_names:
                        if name != active_name:
                            del self._agent_registry[name]
    
    def switch_to_single_agent(self, agent, agent_name: str):
        """Switch to a new single agent, properly cleaning up the previous one."""
        # CRITICAL: Always use the agent's proper name, not the agent key
        # This prevents duplicate registrations like "blueteam_agent" and "Blue Team Agent"
        if hasattr(agent, 'name') and agent.name:
            agent_name = agent.name
        
        # Check for pending history transfer (from parallel mode)
        # This is ONLY used when switching from parallel to single agent mode
        transfer_history = None
        if hasattr(self, '_pending_history_transfer') and self._pending_history_transfer:
            transfer_history = self._pending_history_transfer
            self._pending_history_transfer = None
        
        # Clear parallel agents when switching to single agent mode
        self._parallel_agents.clear()
        
        # Only clean up agents that have no history
        # Keep agents with history or swarm agents in the registry
        old_agents = list(self._agent_registry.keys())
        for old_name in old_agents:
            if old_name != agent_name:
                # Check if this agent has any history
                if old_name in self._message_history and self._message_history[old_name]:
                    # Keep the agent in registry if it has history
                    continue
                # Also keep swarm agents in the registry
                elif old_name in self._swarm_agents:
                    continue
                else:
                    # Remove from registry only if no history and not a swarm agent
                    del self._agent_registry[old_name]
                    # Clean up empty history entry
                    if old_name in self._message_history:
                        del self._message_history[old_name]
        
        # Clear any duplicate P1 entries before setting new one
        self._cleanup_single_agent_duplicates()
        
        # Check if this agent is part of a swarm pattern
        is_swarm_agent = False
        if hasattr(agent, 'pattern') and agent.pattern == 'swarm':
            is_swarm_agent = True
        
        # Assign ID based on whether it's a swarm agent
        if is_swarm_agent:
            # For swarm agents, use unique IDs
            if agent_name not in self._swarm_agents:
                self._swarm_counter += 1
                swarm_id = f"P1-{self._swarm_counter}"
                self._swarm_agents[agent_name] = swarm_id
                self._agent_registry[agent_name] = swarm_id
            else:
                swarm_id = self._swarm_agents[agent_name]
            self._agent_id = swarm_id
        else:
            # Non-swarm single agents get P1
            self._agent_id = "P1"
            self._agent_registry[agent_name] = "P1"
        
        self._active_agent = weakref.ref(agent) if agent else None
        self._active_agent_name = agent_name  # Track active agent name
        
        # Initialize or update message history for this agent
        if agent_name not in self._message_history:
            # Only use transfer_history if we're coming from parallel mode
            if transfer_history:
                self._message_history[agent_name] = transfer_history
            else:
                # Otherwise, start with empty history (don't transfer from other agents)
                self._message_history[agent_name] = []
        else:
            # Agent already has a history entry
            # If there's a transfer_history, always use it (this is an explicit transfer request)
            if transfer_history:
                self._message_history[agent_name] = transfer_history
        
        # Reset ID counter for cleanliness
        self._id_counter = 1
        
        # Final cleanup to ensure only one agent in single mode
        self._cleanup_single_agent_duplicates()
    
    def share_swarm_history(self, agent1_name: str, agent2_name: str):
        """Share message history between two swarm agents.
        
        This ensures both agents share the same list reference,
        so changes made by one agent are visible to the other.
        """
        # Get the history from agent1 (or create if doesn't exist)
        if agent1_name in self._message_history:
            shared_history = self._message_history[agent1_name]
        else:
            shared_history = []
            self._message_history[agent1_name] = shared_history
        
        # Make agent2 share the same reference
        self._message_history[agent2_name] = shared_history

# Global instance
AGENT_MANAGER = SimpleAgentManager()