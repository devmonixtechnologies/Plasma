"""
Agent Registry - Centralized management of agent instances and IDs.

This module provides a clean, centralized way to manage agent instances,
their IDs, and their display names throughout the CAI system.
"""

import weakref
from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple
from threading import Lock

@dataclass
class AgentInstanceInfo:
    """Information about a registered agent instance."""
    agent_type: str  # e.g., "red_teamer"
    display_name: str  # e.g., "Red Team Agent"
    agent_id: str  # e.g., "P1", "P2", etc.
    instance_number: int  # Instance number for this agent type (1, 2, etc.)
    model_name: str  # The model being used
    is_parallel: bool = False  # Whether this is a parallel instance
    is_pattern: bool = False  # Whether this is part of a pattern
    pattern_name: Optional[str] = None  # Name of the pattern if applicable

class AgentRegistry:
    """Centralized registry for managing agent instances."""
    
    def __init__(self):
        self._instances: Dict[str, weakref.ref] = {}  # agent_id -> weak ref to model
        self._instance_info: Dict[str, AgentInstanceInfo] = {}  # agent_id -> info
        self._next_id: int = 1
        self._lock = Lock()
        
        # Track instance counts per agent type for numbering
        self._type_counters: Dict[str, int] = {}
        
    def register_agent(self, 
                      model_instance,
                      agent_type: str,
                      display_name: str,
                      agent_id: Optional[str] = None,
                      is_parallel: bool = False,
                      is_pattern: bool = False,
                      pattern_name: Optional[str] = None) -> str:
        """
        Register a new agent instance.
        
        Args:
            model_instance: The OpenAIChatCompletionsModel instance
            agent_type: The type of agent (e.g., "red_teamer")
            display_name: The display name (e.g., "Red Team Agent")
            agent_id: Optional specific ID (e.g., "P1"). If None, auto-generates.
            is_parallel: Whether this is a parallel instance
            is_pattern: Whether this is part of a pattern
            pattern_name: Name of the pattern if applicable
            
        Returns:
            The agent ID assigned to this instance
        """
        with self._lock:
            # Generate ID if not provided
            if not agent_id:
                agent_id = f"P{self._next_id}"
                self._next_id += 1
            
            # Track instance number for this agent type
            if agent_type not in self._type_counters:
                self._type_counters[agent_type] = 0
            self._type_counters[agent_type] += 1
            instance_number = self._type_counters[agent_type]
            
            # Store weak reference to model
            self._instances[agent_id] = weakref.ref(model_instance)
            
            # Store instance info
            self._instance_info[agent_id] = AgentInstanceInfo(
                agent_type=agent_type,
                display_name=display_name,
                agent_id=agent_id,
                instance_number=instance_number,
                model_name=getattr(model_instance, 'model', 'unknown'),
                is_parallel=is_parallel,
                is_pattern=is_pattern,
                pattern_name=pattern_name
            )
            
            return agent_id
    
    def get_agent_by_id(self, agent_id: str) -> Optional[Tuple[object, AgentInstanceInfo]]:
        """
        Get agent model and info by ID.
        
        Returns:
            Tuple of (model_instance, info) or None if not found
        """
        with self._lock:
            if agent_id not in self._instances:
                return None
                
            model_ref = self._instances[agent_id]
            model = model_ref() if model_ref else None
            
            if not model:
                # Clean up dead reference
                del self._instances[agent_id]
                del self._instance_info[agent_id]
                return None
                
            return (model, self._instance_info[agent_id])
    
    def get_agent_by_name(self, name: str) -> Optional[Tuple[object, AgentInstanceInfo]]:
        """
        Get agent by display name or type name.
        
        Args:
            name: Either display name ("Red Team Agent") or type ("red_teamer")
            
        Returns:
            Tuple of (model_instance, info) or None if not found
        """
        with self._lock:
            # First try exact match on display name
            for agent_id, info in self._instance_info.items():
                if info.display_name == name:
                    return self.get_agent_by_id(agent_id)
            
            # Then try agent type
            for agent_id, info in self._instance_info.items():
                if info.agent_type == name:
                    return self.get_agent_by_id(agent_id)
                    
            return None
    
    def get_all_agents(self) -> List[Tuple[str, AgentInstanceInfo]]:
        """
        Get all registered agents.
        
        Returns:
            List of (agent_id, info) tuples
        """
        with self._lock:
            # Clean up dead references first
            dead_ids = []
            for agent_id, model_ref in self._instances.items():
                if not model_ref():
                    dead_ids.append(agent_id)
            
            for agent_id in dead_ids:
                del self._instances[agent_id]
                del self._instance_info[agent_id]
            
            return [(agent_id, info) for agent_id, info in self._instance_info.items()]
    
    def get_display_name(self, agent_id: str, include_instance: bool = True) -> str:
        """
        Get the display name for an agent.
        
        Args:
            agent_id: The agent ID
            include_instance: Whether to include instance number if > 1
            
        Returns:
            Display name like "Red Team Agent" or "Red Team Agent #2"
        """
        with self._lock:
            if agent_id not in self._instance_info:
                return f"Unknown Agent [{agent_id}]"
            
            info = self._instance_info[agent_id]
            base_name = info.display_name
            
            if include_instance and info.instance_number > 1:
                return f"{base_name} #{info.instance_number}"
            
            return base_name
    
    def get_full_display_name(self, agent_id: str) -> str:
        """
        Get the full display name including ID.
        
        Returns:
            Display name like "Red Team Agent [P1]" or "Red Team Agent #2 [P3]"
        """
        display_name = self.get_display_name(agent_id, include_instance=True)
        return f"{display_name} [{agent_id}]"
    
    def reset_type_counter(self, agent_type: str):
        """Reset the instance counter for a specific agent type."""
        with self._lock:
            if agent_type in self._type_counters:
                self._type_counters[agent_type] = 0
    
    def reset_all_counters(self):
        """Reset all type counters."""
        with self._lock:
            self._type_counters.clear()
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent by ID."""
        with self._lock:
            if agent_id in self._instances:
                del self._instances[agent_id]
            if agent_id in self._instance_info:
                del self._instance_info[agent_id]

# Global registry instance
AGENT_REGISTRY = AgentRegistry()