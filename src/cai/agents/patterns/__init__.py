"""
Agent patterns for CAI.

This module exports both swarm patterns (for handoff-based collaboration)
and parallel patterns (for simultaneous execution).
"""
import importlib
import pkgutil
from typing import Dict, Any, Optional, List, Union

__all__ = [
    'Pattern',
    'PatternType', 
    'get_pattern',
    'get_patterns_by_type',
    'get_parallel_patterns',
    'get_swarm_patterns',
    'create_pattern',
    'parallel_pattern',
    'swarm_pattern',
    'hierarchical_pattern',
    'sequential_pattern',
    'conditional_pattern',
    'PATTERNS',
    'is_swarm_pattern'
]

# Pattern registry for easy access
PATTERNS = {}

def discover_patterns() -> Dict[str, 'Pattern']:
    """Discover all patterns in the patterns directory.
    
    Automatically identifies and loads both swarm and parallel patterns,
    wrapping them in appropriate Pattern classes.
    
    Returns:
        Dictionary mapping pattern names to Pattern instances.
    """
    # Import Pattern here to avoid circular imports
    from .pattern import Pattern, PatternType
    
    patterns = {}
    
    # Get the current package
    package = __name__
    prefix = package + "."
    
    # Iterate through all modules in this package
    for importer, modname, ispkg in pkgutil.iter_modules(__path__, prefix):
        if ispkg:
            continue
            
        # Skip special modules
        module_name = modname.replace(prefix, "")
        if module_name in ["__init__", "pattern", "utils"]:
            continue
            
        try:
            module = importlib.import_module(modname)
            
            # Look for Pattern class instances
            for attr_name in dir(module):
                # Skip private attributes
                if attr_name.startswith("_"):
                    continue
                    
                attr = getattr(module, attr_name)
                
                # Check if it's a Pattern instance
                if isinstance(attr, Pattern):
                    # Use the pattern's name or the attribute name
                    pattern_name = attr.name or attr_name
                    patterns[pattern_name] = attr
                    
                    # Add to __all__ if not already there
                    if attr_name not in __all__:
                        __all__.append(attr_name)
                        
                # Check for legacy swarm patterns
                elif hasattr(attr, "pattern") and getattr(attr, "pattern") == "swarm":
                    # Always use the attribute name as the key to avoid duplicates
                    # The pattern's display name is stored in pattern.name
                    pattern_key = attr_name
                    pattern_display_name = getattr(attr, "name", attr_name)
                    
                    # Create swarm pattern wrapper
                    pattern = Pattern(
                        name=pattern_display_name,
                        type=PatternType.SWARM,
                        description=getattr(attr, "description", ""),
                        entry_agent=attr
                    )
                    pattern.agents = [attr]  # Add to agents list
                    patterns[pattern_key] = pattern
                    
                    if attr_name not in __all__:
                        __all__.append(attr_name)
                        
                # Check if it's a Pattern class (not instance)
                elif (isinstance(attr, type) and 
                      issubclass(attr, Pattern) and 
                      attr is not Pattern):
                    # Create an instance of the pattern class
                    try:
                        pattern_instance = attr()
                        pattern_name = pattern_instance.name
                        patterns[pattern_name] = pattern_instance
                        
                        # Add class name to __all__
                        if attr_name not in __all__:
                            __all__.append(attr_name)
                    except Exception:
                        # Skip if we can't instantiate
                        continue
                        
                # Check for dict-based pattern definitions
                elif (isinstance(attr, dict) and 
                      'name' in attr and 
                      'type' in attr and
                      attr_name.endswith('_pattern')):
                    # Convert dict to Pattern instance
                    try:
                        pattern_config = attr.copy()
                        pattern_name = pattern_config.pop('name')
                        pattern_type = pattern_config.pop('type')
                        
                        pattern = Pattern(
                            name=pattern_name,
                            type=pattern_type,
                            **pattern_config
                        )
                        patterns[pattern_name] = pattern
                        
                        if attr_name not in __all__:
                            __all__.append(attr_name)
                    except Exception:
                        # Skip if we can't create pattern
                        continue
                        
        except Exception as e:
            # Skip modules that cannot be imported
            # Silently ignore circular import errors for pattern files
            if "circular import" not in str(e):
                import sys
                print(f"Error importing {module_name}: {e}", file=sys.stderr)
            continue
            
    return patterns

# Defer pattern discovery until after all imports are done
def _initialize_patterns():
    """Initialize patterns after all imports are complete."""
    global PATTERNS
    if not PATTERNS:  # Only initialize once
        PATTERNS.update(discover_patterns())

# Import Pattern and related items after defining functions to avoid circular imports
from .pattern import (
    Pattern, PatternType,
    parallel_pattern, swarm_pattern, hierarchical_pattern,
    sequential_pattern, conditional_pattern
)

# Initialize patterns after imports
_initialize_patterns()

def get_pattern(pattern_name: str) -> Optional['Pattern']:
    """Get a pattern by name.
    
    Args:
        pattern_name: Name of the pattern to retrieve
        
    Returns:
        Pattern instance if found, None otherwise
    """
    return PATTERNS.get(pattern_name)

def get_patterns_by_type(pattern_type: Union[str, 'PatternType']) -> Dict[str, 'Pattern']:
    """Get all available patterns of a specific type.
    
    Args:
        pattern_type: Type of patterns to retrieve (e.g., "swarm", "parallel")
        
    Returns:
        Dictionary mapping pattern names to Pattern instances
    """
    from .pattern import PatternType
    
    if isinstance(pattern_type, str):
        try:
            pattern_type = PatternType(pattern_type)
        except ValueError:
            return {}  # Invalid type
    
    result = {}
    for name, pattern in PATTERNS.items():
        if pattern.type == pattern_type:
            result[name] = pattern
            
    return result

def get_parallel_patterns() -> Dict[str, 'Pattern']:
    """Get all available parallel patterns.
    
    Returns:
        Dictionary of pattern name to Pattern instances of type PARALLEL
    """
    from .pattern import PatternType
    return get_patterns_by_type(PatternType.PARALLEL)

def get_swarm_patterns() -> Dict[str, 'Pattern']:
    """Get all available swarm patterns.
    
    Returns:
        Dictionary of pattern name to Pattern instances of type SWARM
    """
    from .pattern import PatternType
    return get_patterns_by_type(PatternType.SWARM)

def create_pattern(
    name: str,
    pattern_type: Union[str, 'PatternType'],
    description: str = "",
    **kwargs
) -> 'Pattern':
    """Create a new pattern programmatically.
    
    Args:
        name: Pattern name
        pattern_type: Type of pattern (parallel, swarm, etc.)
        description: Pattern description
        **kwargs: Additional pattern-specific arguments
        
    Returns:
        New Pattern instance
    """
    from .pattern import Pattern
    
    return Pattern(
        name=name,
        type=pattern_type,
        description=description,
        **kwargs
    )

# Import utility functions
from .utils import is_swarm_pattern

# Import core pattern classes
from .pattern import Pattern, PatternType

# Import factory functions for creating patterns
from .pattern import (
    parallel_pattern,
    swarm_pattern,
    hierarchical_pattern,
    sequential_pattern,
    conditional_pattern
)