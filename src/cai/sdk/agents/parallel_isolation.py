"""
Parallel History Isolation System - Ensures complete isolation between parallel agents.

This module provides a clean way to manage isolated message histories for parallel agents,
ensuring that each agent has its own completely independent copy of the conversation history.
"""

import copy
from typing import Dict, List, Any, Optional, Tuple
from threading import Lock

from cai.sdk.agents.simple_agent_manager import AGENT_MANAGER


class ParallelHistoryIsolation:
    """Manages isolated message histories for parallel agent execution."""
    
    def __init__(self):
        self._isolated_histories: Dict[str, List[dict]] = {}  # agent_id -> isolated history
        self._base_history: List[dict] = []  # The base history before parallel execution
        self._lock = Lock()
        self._parallel_mode = False
        self._selected_agent_id: Optional[str] = None  # Track which agent was selected after parallel
    
    def create_isolated_history(self, base_history: List[dict]) -> List[dict]:
        """Create a deep copy of the given history to ensure complete isolation.
        
        Args:
            base_history: The history to copy
            
        Returns:
            A completely independent copy of the history
        """
        # Use deepcopy to ensure no shared references at any level
        return copy.deepcopy(base_history)
    
    def transfer_to_parallel(self, base_history: List[dict], num_agents: int, agent_ids: List[str]) -> Dict[str, List[dict]]:
        """Transfer from single agent mode to parallel mode.
        
        Creates N isolated copies of the base history, one for each parallel agent.
        
        Args:
            base_history: The current single agent's history
            num_agents: Number of parallel agents
            agent_ids: List of agent IDs for the parallel agents
            
        Returns:
            Dictionary mapping agent_id to isolated history
        """
        with self._lock:
            # Store the base history
            self._base_history = copy.deepcopy(base_history)
            self._parallel_mode = True
            
            # Create isolated histories for each agent
            isolated_histories = {}
            for i in range(min(num_agents, len(agent_ids))):
                agent_id = agent_ids[i]
                # Each agent gets its own deep copy
                isolated_histories[agent_id] = self.create_isolated_history(base_history)
                self._isolated_histories[agent_id] = isolated_histories[agent_id]
            
            return isolated_histories
    
    def transfer_from_parallel(self, agent_histories: Dict[str, List[dict]], selected_agent_id: Optional[str] = None) -> List[dict]:
        """Transfer from parallel mode back to single agent mode.
        
        Selects one agent's history to continue with in single agent mode.
        
        Args:
            agent_histories: Dictionary of agent_id -> history
            selected_agent_id: Optional specific agent to select. If None, selects the longest history.
            
        Returns:
            The selected history for single agent mode
        """
        with self._lock:
            self._parallel_mode = False
            
            if not agent_histories:
                # No histories to transfer, return empty
                return []
            
            # If a specific agent is selected, use its history
            if selected_agent_id and selected_agent_id in agent_histories:
                self._selected_agent_id = selected_agent_id
                selected_history = agent_histories[selected_agent_id]
            else:
                # Otherwise, select the agent with the longest history (most interactions)
                selected_agent_id = max(agent_histories.keys(), 
                                       key=lambda aid: len(agent_histories[aid]))
                self._selected_agent_id = selected_agent_id
                selected_history = agent_histories[selected_agent_id]
            
            # Return a deep copy to ensure continued isolation
            return copy.deepcopy(selected_history)
    
    def get_isolated_history(self, agent_id: str) -> Optional[List[dict]]:
        """Get the isolated history for a specific agent.
        
        Args:
            agent_id: The agent's ID
            
        Returns:
            The agent's isolated history or None if not found
        """
        with self._lock:
            if agent_id in self._isolated_histories:
                # Return a copy to prevent external modifications
                return copy.deepcopy(self._isolated_histories[agent_id])
            return None
    
    def update_isolated_history(self, agent_id: str, new_message: dict):
        """Update an agent's isolated history with a new message.
        
        Args:
            agent_id: The agent's ID
            new_message: The message to add
        """
        with self._lock:
            if agent_id in self._isolated_histories:
                # Add a deep copy of the message
                self._isolated_histories[agent_id].append(copy.deepcopy(new_message))
    
    def replace_isolated_history(self, agent_id: str, new_history: List[dict]):
        """Replace an agent's entire isolated history.
        
        Args:
            agent_id: The agent's ID
            new_history: The new history to set
        """
        with self._lock:
            # Replace with a deep copy
            self._isolated_histories[agent_id] = copy.deepcopy(new_history)
            # If we're adding histories, we should be in parallel mode
            if agent_id and new_history is not None:
                self._parallel_mode = True
    
    def clear_all_histories(self):
        """Clear all isolated histories and reset state."""
        with self._lock:
            self._isolated_histories.clear()
            self._base_history.clear()
            self._parallel_mode = False
            self._selected_agent_id = None
    
    def clear_agent_history(self, agent_id: str):
        """Clear history for a specific agent."""
        with self._lock:
            if agent_id in self._isolated_histories:
                self._isolated_histories[agent_id].clear()
    
    def is_parallel_mode(self) -> bool:
        """Check if currently in parallel mode."""
        return self._parallel_mode
    
    def has_isolated_histories(self) -> bool:
        """Check if there are any isolated histories stored."""
        with self._lock:
            return len(self._isolated_histories) > 0
    
    def get_base_history(self) -> List[dict]:
        """Get the base history (before parallel execution)."""
        with self._lock:
            return copy.deepcopy(self._base_history)
    
    def get_selected_agent_id(self) -> Optional[str]:
        """Get the ID of the agent selected after parallel execution."""
        return self._selected_agent_id
    
    def sync_with_agent_manager(self):
        """Synchronize isolated histories with AGENT_MANAGER.
        
        This ensures that the agent manager's view of histories matches
        our isolated copies.
        """
        with self._lock:
            for agent_id, history in self._isolated_histories.items():
                # Find the agent name for this ID
                agent_name = AGENT_MANAGER.get_agent_by_id(agent_id)
                if agent_name:
                    # Clear existing history and replace with isolated copy
                    AGENT_MANAGER.clear_history(agent_name)
                    for msg in history:
                        AGENT_MANAGER.add_to_history(agent_name, copy.deepcopy(msg))
    
    def create_parallel_agent_histories(self, base_agent_name: str, agent_configs: List[Tuple[str, str]]) -> Dict[str, List[dict]]:
        """Create isolated histories for parallel agents based on configurations.
        
        Args:
            base_agent_name: The name of the current single agent
            agent_configs: List of (agent_name, agent_id) tuples for parallel agents
            
        Returns:
            Dictionary mapping agent_id to isolated history
        """
        with self._lock:
            # Get the base history from AGENT_MANAGER
            base_history = AGENT_MANAGER.get_message_history(base_agent_name)
            
            # Store it as our base
            self._base_history = copy.deepcopy(base_history)
            self._parallel_mode = True
            
            # Create isolated histories
            isolated_histories = {}
            for agent_name, agent_id in agent_configs:
                # Each agent gets its own deep copy
                isolated_history = self.create_isolated_history(base_history)
                isolated_histories[agent_id] = isolated_history
                self._isolated_histories[agent_id] = isolated_history
                
                # Also update AGENT_MANAGER with the isolated copy
                AGENT_MANAGER.clear_history(agent_name)
                for msg in isolated_history:
                    AGENT_MANAGER.add_to_history(agent_name, copy.deepcopy(msg))
            
            return isolated_histories
    
    def merge_parallel_histories_to_single(self, selected_agent_name: str, target_agent_name: str):
        """Merge a selected parallel agent's history to a single agent.
        
        Args:
            selected_agent_name: The parallel agent whose history to use
            target_agent_name: The single agent to receive the history
        """
        with self._lock:
            # Get the selected agent's ID
            selected_id = AGENT_MANAGER.get_id_by_name(selected_agent_name)
            if not selected_id or selected_id not in self._isolated_histories:
                return
            
            # Get the isolated history
            selected_history = self._isolated_histories[selected_id]
            
            # Clear the target agent's history and replace with selected
            AGENT_MANAGER.clear_history(target_agent_name)
            for msg in selected_history:
                AGENT_MANAGER.add_to_history(target_agent_name, copy.deepcopy(msg))
            
            # Clear parallel mode
            self._parallel_mode = False
            self._selected_agent_id = selected_id
            
            # Clear isolated histories
            self._isolated_histories.clear()


# Global instance
PARALLEL_ISOLATION = ParallelHistoryIsolation()