"""
Unified Pattern class with type-based behavior.

This module provides a single Pattern class that adapts its behavior
based on the pattern type (parallel, swarm, hierarchical, etc.).
"""

from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from cai.repl.commands.parallel import ParallelConfig

class PatternType(Enum):
    """Enumeration of available pattern types."""
    PARALLEL = "parallel"
    SWARM = "swarm"
    HIERARCHICAL = "hierarchical"
    SEQUENTIAL = "sequential"
    CONDITIONAL = "conditional"
    
    @classmethod
    def from_string(cls, value: str) -> 'PatternType':
        """Convert string to PatternType."""
        try:
            return cls(value.lower())
        except ValueError:
            raise ValueError(f"Invalid pattern type: {value}. Valid types: {[t.value for t in cls]}")


@dataclass
class Pattern:
    """
    Unified pattern class that adapts behavior based on type.
    
    This class uses the type attribute to determine how to handle
    configurations and execution flow.
    """
    name: str
    type: Union[PatternType, str]
    description: str = ""
    
    # Type-specific attributes
    configs: List[ParallelConfig] = field(default_factory=list)  # For parallel
    entry_agent: Optional[Any] = None  # For swarm
    agents: List[Any] = field(default_factory=list)  # For swarm/hierarchical
    root_agent: Optional[Any] = None  # For hierarchical
    sequence: List[Any] = field(default_factory=list)  # For sequential
    conditions: Dict[str, Any] = field(default_factory=dict)  # For conditional
    
    # Common configuration options
    max_concurrent: Optional[int] = None
    unified_context: bool = True
    timeout: Optional[float] = None
    retry_on_failure: bool = False
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize pattern type and validate."""
        if isinstance(self.type, str):
            self.type = PatternType.from_string(self.type)
        
        # Initialize type-specific defaults
        self._initialize_for_type()
    
    def _initialize_for_type(self):
        """Initialize attributes based on pattern type."""
        if self.type == PatternType.PARALLEL:
            # Parallel patterns use configs
            if not hasattr(self, '_parallel_initialized'):
                self._parallel_initialized = True
                
        elif self.type == PatternType.SWARM:
            # Swarm patterns need entry agent
            if not hasattr(self, '_swarm_initialized'):
                self._swarm_initialized = True
                
        elif self.type == PatternType.HIERARCHICAL:
            # Hierarchical patterns need root agent
            if not hasattr(self, '_hierarchical_initialized'):
                self._hierarchical_initialized = True
                
        elif self.type == PatternType.SEQUENTIAL:
            # Sequential patterns use sequence list
            if not hasattr(self, '_sequential_initialized'):
                self._sequential_initialized = True
                
        elif self.type == PatternType.CONDITIONAL:
            # Conditional patterns use conditions dict
            if not hasattr(self, '_conditional_initialized'):
                self._conditional_initialized = True
    
    # Type-specific methods
    def add_parallel_agent(self, agent: Union[str, ParallelConfig]) -> 'Pattern':
        """Add an agent for parallel execution."""
        if self.type != PatternType.PARALLEL:
            raise ValueError(f"add_parallel_agent only works for PARALLEL patterns, not {self.type.value}")
        
        if isinstance(agent, str):
            agent = ParallelConfig(agent, unified_context=self.unified_context)
        
        self.configs.append(agent)
        return self
    
    def set_entry_agent(self, agent: Any) -> 'Pattern':
        """Set the entry agent for swarm patterns."""
        if self.type != PatternType.SWARM:
            raise ValueError(f"set_entry_agent only works for SWARM patterns, not {self.type.value}")
        
        self.entry_agent = agent
        if agent not in self.agents:
            self.agents.append(agent)
        return self
    
    def set_root_agent(self, agent: Any) -> 'Pattern':
        """Set the root agent for hierarchical patterns."""
        if self.type != PatternType.HIERARCHICAL:
            raise ValueError(f"set_root_agent only works for HIERARCHICAL patterns, not {self.type.value}")
        
        self.root_agent = agent
        if agent not in self.agents:
            self.agents.append(agent)
        return self
    
    def add_sequence_step(self, agent: Any, wait_for_previous: bool = True) -> 'Pattern':
        """Add a step to sequential execution."""
        if self.type != PatternType.SEQUENTIAL:
            raise ValueError(f"add_sequence_step only works for SEQUENTIAL patterns, not {self.type.value}")
        
        self.sequence.append({
            "agent": agent,
            "wait_for_previous": wait_for_previous
        })
        return self
    
    def add_condition(self, condition_name: str, agent: Any, predicate: Optional[Callable] = None) -> 'Pattern':
        """Add a conditional branch."""
        if self.type != PatternType.CONDITIONAL:
            raise ValueError(f"add_condition only works for CONDITIONAL patterns, not {self.type.value}")
        
        self.conditions[condition_name] = {
            "agent": agent,
            "predicate": predicate
        }
        return self
    
    # Generic methods that work based on type
    def add(self, item: Any) -> 'Pattern':
        """Generic add method that works based on pattern type."""
        if self.type == PatternType.PARALLEL:
            return self.add_parallel_agent(item)
        elif self.type == PatternType.SWARM:
            self.agents.append(item)
            return self
        elif self.type == PatternType.HIERARCHICAL:
            self.agents.append(item)
            return self
        elif self.type == PatternType.SEQUENTIAL:
            return self.add_sequence_step(item)
        elif self.type == PatternType.CONDITIONAL:
            # For conditional, expect a tuple of (name, agent, predicate)
            if isinstance(item, tuple) and len(item) >= 2:
                return self.add_condition(item[0], item[1], item[2] if len(item) > 2 else None)
            raise ValueError("Conditional patterns expect (name, agent, predicate) tuples")
        
        return self
    
    def validate(self) -> bool:
        """Validate pattern based on its type."""
        if not self.name or not self.type:
            return False
        
        if self.type == PatternType.PARALLEL:
            return len(self.configs) > 0
        
        elif self.type == PatternType.SWARM:
            return self.entry_agent is not None
        
        elif self.type == PatternType.HIERARCHICAL:
            return self.root_agent is not None and len(self.agents) > 0
        
        elif self.type == PatternType.SEQUENTIAL:
            return len(self.sequence) > 0
        
        elif self.type == PatternType.CONDITIONAL:
            return len(self.conditions) > 0
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert pattern to dictionary representation."""
        base = {
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "metadata": self.metadata
        }
        
        # Add type-specific data
        if self.type == PatternType.PARALLEL:
            base["configs"] = [c.__dict__ for c in self.configs]
            base["max_concurrent"] = self.max_concurrent
            base["unified_context"] = self.unified_context
            
        elif self.type == PatternType.SWARM:
            base["entry_agent"] = getattr(self.entry_agent, "name", str(self.entry_agent))
            base["agents"] = [getattr(a, "name", str(a)) for a in self.agents]
            
        elif self.type == PatternType.HIERARCHICAL:
            base["root_agent"] = getattr(self.root_agent, "name", str(self.root_agent))
            base["agents"] = [getattr(a, "name", str(a)) for a in self.agents]
            
        elif self.type == PatternType.SEQUENTIAL:
            base["sequence"] = [
                {
                    "agent": getattr(s["agent"], "name", str(s["agent"])),
                    "wait_for_previous": s.get("wait_for_previous", True)
                }
                for s in self.sequence
            ]
            
        elif self.type == PatternType.CONDITIONAL:
            base["conditions"] = {
                name: {
                    "agent": getattr(cond["agent"], "name", str(cond["agent"])),
                    "has_predicate": cond.get("predicate") is not None
                }
                for name, cond in self.conditions.items()
            }
        
        return base
    
    def get_agents(self) -> List[Any]:
        """Get all agents involved in this pattern."""
        if self.type == PatternType.PARALLEL:
            return [c.agent_name for c in self.configs]
        
        elif self.type == PatternType.SWARM:
            return self.agents
        
        elif self.type == PatternType.HIERARCHICAL:
            return self.agents
        
        elif self.type == PatternType.SEQUENTIAL:
            return [s["agent"] for s in self.sequence]
        
        elif self.type == PatternType.CONDITIONAL:
            return [cond["agent"] for cond in self.conditions.values()]
        
        return []
    
    def __repr__(self) -> str:
        """String representation of the pattern."""
        agent_count = len(self.get_agents())
        return f"Pattern(name='{self.name}', type={self.type.value}, agents={agent_count})"


# Factory functions for creating patterns
def parallel_pattern(name: str, description: str = "", agents: Optional[List[str]] = None, **kwargs) -> Pattern:
    """Create a parallel execution pattern."""
    pattern = Pattern(name=name, type=PatternType.PARALLEL, description=description, **kwargs)
    
    if agents:
        for agent in agents:
            pattern.add_parallel_agent(agent)
    
    return pattern


def swarm_pattern(name: str, entry_agent: Any, description: str = "", agents: Optional[List[Any]] = None, **kwargs) -> Pattern:
    """Create a swarm collaboration pattern."""
    pattern = Pattern(name=name, type=PatternType.SWARM, description=description, **kwargs)
    pattern.set_entry_agent(entry_agent)
    
    if agents:
        pattern.agents.extend(agents)
    
    return pattern


def hierarchical_pattern(name: str, root_agent: Any, description: str = "", children: Optional[List[Any]] = None, **kwargs) -> Pattern:
    """Create a hierarchical pattern."""
    pattern = Pattern(name=name, type=PatternType.HIERARCHICAL, description=description, **kwargs)
    pattern.set_root_agent(root_agent)
    
    if children:
        pattern.agents.extend(children)
    
    return pattern


def sequential_pattern(name: str, steps: List[Any], description: str = "", **kwargs) -> Pattern:
    """Create a sequential execution pattern."""
    pattern = Pattern(name=name, type=PatternType.SEQUENTIAL, description=description, **kwargs)
    
    for step in steps:
        pattern.add_sequence_step(step)
    
    return pattern


def conditional_pattern(name: str, conditions: Dict[str, Any], description: str = "", **kwargs) -> Pattern:
    """Create a conditional execution pattern."""
    pattern = Pattern(name=name, type=PatternType.CONDITIONAL, description=description, **kwargs)
    
    for cond_name, agent in conditions.items():
        pattern.add_condition(cond_name, agent)
    
    return pattern