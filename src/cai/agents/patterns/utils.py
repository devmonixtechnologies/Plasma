"""
Utility functions for working with patterns.

Provides helper functions to convert patterns to parallel configurations
and integrate with the CAI execution system.
"""

from typing import List, Optional, Union
from cai.repl.commands.parallel import ParallelConfig, PARALLEL_CONFIGS
from cai.agents import get_available_agents

def pattern_to_parallel_configs(pattern: Union['Pattern', str]) -> List[ParallelConfig]:
    """Convert a pattern to a list of ParallelConfig objects.
    
    Args:
        pattern: Either a Pattern instance or pattern name string
        
    Returns:
        List of ParallelConfig objects ready for parallel execution
        
    Raises:
        ValueError: If pattern is not a parallel pattern or pattern not found
    """
    # Import here to avoid circular imports
    from .pattern import Pattern, PatternType
    from . import get_pattern
    
    # Handle string pattern names
    if isinstance(pattern, str):
        pattern = get_pattern(pattern)
        if not pattern:
            raise ValueError(f"Pattern '{pattern}' not found")
    
    # Only PARALLEL type patterns can be converted to parallel configs
    if pattern.type != PatternType.PARALLEL:
        raise ValueError(f"Pattern must be of type PARALLEL, got {pattern.type.value}")
    
    return pattern.configs

def apply_pattern_to_parallel_command(pattern: Union['Pattern', str]) -> None:
    """Apply a pattern to the global PARALLEL_CONFIGS for execution.
    
    This function integrates with the parallel command system by
    setting up the configurations from a pattern.
    
    Args:
        pattern: Either a Pattern instance (must be PARALLEL type) or pattern name string
    """
    configs = pattern_to_parallel_configs(pattern)
    
    # Clear existing configs and apply pattern configs
    PARALLEL_CONFIGS.clear()
    PARALLEL_CONFIGS.extend(configs)

def create_pattern_from_current_parallel_configs(name: str, description: str = "") -> 'Pattern':
    """Create a new Pattern (PARALLEL type) from the current PARALLEL_CONFIGS.
    
    This allows users to save their current parallel configuration as a reusable pattern.
    
    Args:
        name: Name for the new pattern
        description: Optional description
        
    Returns:
        New Pattern instance with type PARALLEL
    """
    from .pattern import Pattern, PatternType
    
    if not PARALLEL_CONFIGS:
        raise ValueError("No parallel configurations currently set")
    
    return Pattern(
        name=name,
        type=PatternType.PARALLEL,
        description=description,
        configs=list(PARALLEL_CONFIGS)  # Make a copy
    )

def validate_pattern_agents(pattern: Union['Pattern', str]) -> List[str]:
    """Validate that all agents in a pattern exist.
    
    Args:
        pattern: Either a Pattern instance or pattern name string
        
    Returns:
        List of missing agent names (empty if all valid)
    """
    from .pattern import PatternType
    from . import get_pattern
    
    if isinstance(pattern, str):
        pattern = get_pattern(pattern)
        if not pattern:
            return [f"Pattern '{pattern}' not found"]
    
    if pattern.type != PatternType.PARALLEL:
        return []
    
    available_agents = get_available_agents()
    missing = []
    
    for config in pattern.configs:
        if config.agent_name not in available_agents:
            missing.append(config.agent_name)
    
    return missing

def list_pattern_agents(pattern: Union['Pattern', str]) -> List[str]:
    """Get a list of agent names from a pattern.
    
    Args:
        pattern: Either a Pattern instance or pattern name string
        
    Returns:
        List of agent names in the pattern
    """
    from .pattern import PatternType
    from . import get_pattern
    
    if isinstance(pattern, str):
        pattern = get_pattern(pattern)
        if not pattern:
            return []
    
    if pattern.type == PatternType.PARALLEL:
        return [config.agent_name for config in pattern.configs]
    elif pattern.type == PatternType.SWARM:
        return [getattr(agent, "name", str(agent)) for agent in pattern.agents]
    
    return []


def is_swarm_pattern(agent) -> bool:
    """Check if an agent is part of a swarm pattern.
    
    Args:
        agent: The agent instance to check
        
    Returns:
        True if the agent is part of a swarm pattern, False otherwise
    """
    # Check if the agent has a pattern attribute set to 'swarm'
    if hasattr(agent, 'pattern') and agent.pattern == 'swarm':
        return True
    
    # Alternative: Check if the agent has bidirectional handoffs
    # which is a characteristic of swarm patterns
    if hasattr(agent, 'handoffs') and agent.handoffs:
        # For each handoff this agent has
        for handoff in agent.handoffs:
            if not hasattr(handoff, 'agent_name'):
                continue
                
            # Get the target agent name from the handoff
            target_agent_name = handoff.agent_name
            
            # Now we need to check if the target agent has a handoff back to this agent
            # Since we can't access the target agent directly from the handoff,
            # we need to check using the on_invoke_handoff function
            # But for a simpler approach, let's check if the handoff has the actual agent reference
            
            # Check if we can get the actual agent from the handoff's on_invoke_handoff
            # This is a bit tricky, but let's try to extract it
            if hasattr(handoff, 'on_invoke_handoff'):
                # The on_invoke_handoff is a closure that captures the agent
                # We can try to extract it from the closure
                closure_vars = handoff.on_invoke_handoff.__closure__
                if closure_vars:
                    for cell in closure_vars:
                        try:
                            cell_contents = cell.cell_contents
                            # Check if this is an Agent instance
                            if hasattr(cell_contents, 'name') and hasattr(cell_contents, 'handoffs'):
                                # Found the target agent, check if it has a handoff back
                                for target_handoff in cell_contents.handoffs:
                                    if (hasattr(target_handoff, 'agent_name') and 
                                        hasattr(agent, 'name') and 
                                        target_handoff.agent_name == agent.name):
                                        return True
                        except:
                            continue
    
    return False