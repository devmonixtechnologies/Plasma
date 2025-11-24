"""
Tests for the unified Pattern class with type-based behavior.
"""

import pytest
from cai.agents.patterns.pattern import (
    Pattern,
    PatternType,
    parallel_pattern,
    swarm_pattern,
    hierarchical_pattern,
    sequential_pattern,
    conditional_pattern
)
from cai.repl.commands.parallel import ParallelConfig

class TestPatternType:
    """Test PatternType enum."""
    
    def test_pattern_type_values(self):
        """Test pattern type enum values."""
        assert PatternType.PARALLEL.value == "parallel"
        assert PatternType.SWARM.value == "swarm"
        assert PatternType.HIERARCHICAL.value == "hierarchical"
        assert PatternType.SEQUENTIAL.value == "sequential"
        assert PatternType.CONDITIONAL.value == "conditional"
    
    def test_pattern_type_from_string(self):
        """Test converting string to PatternType."""
        assert PatternType.from_string("parallel") == PatternType.PARALLEL
        assert PatternType.from_string("SWARM") == PatternType.SWARM
        assert PatternType.from_string("Hierarchical") == PatternType.HIERARCHICAL
        
        with pytest.raises(ValueError):
            PatternType.from_string("invalid")

class TestUnifiedPattern:
    """Test the unified Pattern class."""
    
    def test_pattern_creation_with_enum(self):
        """Test creating pattern with PatternType enum."""
        pattern = Pattern(
            name="test",
            type=PatternType.PARALLEL,
            description="Test pattern"
        )
        assert pattern.name == "test"
        assert pattern.type == PatternType.PARALLEL
        assert pattern.description == "Test pattern"
    
    def test_pattern_creation_with_string(self):
        """Test creating pattern with string type."""
        pattern = Pattern(
            name="test",
            type="swarm",
            description="Test pattern"
        )
        assert pattern.type == PatternType.SWARM
    
    def test_invalid_pattern_type(self):
        """Test creating pattern with invalid type."""
        with pytest.raises(ValueError):
            Pattern(name="test", type="invalid_type")

class TestParallelPatternType:
    """Test Pattern class with PARALLEL type."""
    
    def test_parallel_pattern_methods(self):
        """Test parallel-specific methods."""
        pattern = Pattern("test", type=PatternType.PARALLEL)
        
        # Add string agent
        pattern.add_parallel_agent("agent1")
        assert len(pattern.configs) == 1
        assert pattern.configs[0].agent_name == "agent1"
        
        # Add ParallelConfig
        config = ParallelConfig("agent2", unified_context=False)
        pattern.add_parallel_agent(config)
        assert len(pattern.configs) == 2
        assert pattern.configs[1] == config
    
    def test_parallel_pattern_validation(self):
        """Test parallel pattern validation."""
        pattern = Pattern("test", type=PatternType.PARALLEL)
        assert not pattern.validate()  # No configs
        
        pattern.add_parallel_agent("agent1")
        assert pattern.validate()  # Has configs
    
    def test_parallel_pattern_generic_add(self):
        """Test generic add method for parallel."""
        pattern = Pattern("test", type=PatternType.PARALLEL)
        pattern.add("agent1")
        pattern.add(ParallelConfig("agent2"))
        
        assert len(pattern.configs) == 2
        assert pattern.get_agents() == ["agent1", "agent2"]
    
    def test_parallel_wrong_methods(self):
        """Test using wrong methods on parallel pattern."""
        pattern = Pattern("test", type=PatternType.PARALLEL)
        
        with pytest.raises(ValueError):
            pattern.set_entry_agent("agent")
        
        with pytest.raises(ValueError):
            pattern.set_root_agent("agent")

class TestSwarmPatternType:
    """Test Pattern class with SWARM type."""
    
    def test_swarm_pattern_methods(self):
        """Test swarm-specific methods."""
        pattern = Pattern("test", type=PatternType.SWARM)
        
        # Set entry agent
        pattern.set_entry_agent("leader")
        assert pattern.entry_agent == "leader"
        assert "leader" in pattern.agents
        
        # Add more agents
        pattern.add("follower1")
        pattern.add("follower2")
        assert len(pattern.agents) == 3
    
    def test_swarm_pattern_validation(self):
        """Test swarm pattern validation."""
        pattern = Pattern("test", type=PatternType.SWARM)
        assert not pattern.validate()  # No entry agent
        
        pattern.set_entry_agent("leader")
        assert pattern.validate()  # Has entry agent

class TestHierarchicalPatternType:
    """Test Pattern class with HIERARCHICAL type."""
    
    def test_hierarchical_pattern_methods(self):
        """Test hierarchical-specific methods."""
        pattern = Pattern("test", type=PatternType.HIERARCHICAL)
        
        # Set root agent
        pattern.set_root_agent("root")
        assert pattern.root_agent == "root"
        assert "root" in pattern.agents
        
        # Add child agents
        pattern.add("child1")
        pattern.add("child2")
        assert len(pattern.agents) == 3
    
    def test_hierarchical_pattern_validation(self):
        """Test hierarchical pattern validation."""
        pattern = Pattern("test", type=PatternType.HIERARCHICAL)
        assert not pattern.validate()  # No root agent
        
        pattern.set_root_agent("root")
        assert pattern.validate()  # Has root agent and agents

class TestSequentialPatternType:
    """Test Pattern class with SEQUENTIAL type."""
    
    def test_sequential_pattern_methods(self):
        """Test sequential-specific methods."""
        pattern = Pattern("test", type=PatternType.SEQUENTIAL)
        
        # Add sequence steps
        pattern.add_sequence_step("step1", wait_for_previous=True)
        pattern.add_sequence_step("step2", wait_for_previous=False)
        
        assert len(pattern.sequence) == 2
        assert pattern.sequence[0]["agent"] == "step1"
        assert pattern.sequence[0]["wait_for_previous"] is True
        assert pattern.sequence[1]["wait_for_previous"] is False
    
    def test_sequential_pattern_validation(self):
        """Test sequential pattern validation."""
        pattern = Pattern("test", type=PatternType.SEQUENTIAL)
        assert not pattern.validate()  # No sequence
        
        pattern.add_sequence_step("step1")
        assert pattern.validate()  # Has sequence

class TestConditionalPatternType:
    """Test Pattern class with CONDITIONAL type."""
    
    def test_conditional_pattern_methods(self):
        """Test conditional-specific methods."""
        pattern = Pattern("test", type=PatternType.CONDITIONAL)
        
        # Add conditions
        pattern.add_condition("web", "web_agent")
        pattern.add_condition("network", "network_agent", predicate=lambda x: True)
        
        assert len(pattern.conditions) == 2
        assert pattern.conditions["web"]["agent"] == "web_agent"
        assert pattern.conditions["network"]["agent"] == "network_agent"
        assert pattern.conditions["network"]["predicate"] is not None
    
    def test_conditional_pattern_validation(self):
        """Test conditional pattern validation."""
        pattern = Pattern("test", type=PatternType.CONDITIONAL)
        assert not pattern.validate()  # No conditions
        
        pattern.add_condition("default", "default_agent")
        assert pattern.validate()  # Has conditions
    
    def test_conditional_generic_add(self):
        """Test generic add with tuples for conditional."""
        pattern = Pattern("test", type=PatternType.CONDITIONAL)
        
        # Add with tuple
        pattern.add(("cond1", "agent1"))
        pattern.add(("cond2", "agent2", lambda x: x > 0))
        
        assert len(pattern.conditions) == 2

class TestPatternConversion:
    """Test pattern conversion methods."""
    
    def test_parallel_to_dict(self):
        """Test converting parallel pattern to dict."""
        pattern = Pattern("test", type=PatternType.PARALLEL, max_concurrent=2)
        pattern.add_parallel_agent("agent1")
        
        result = pattern.to_dict()
        assert result["name"] == "test"
        assert result["type"] == "parallel"
        assert len(result["configs"]) == 1
        assert result["max_concurrent"] == 2
    
    def test_swarm_to_dict(self):
        """Test converting swarm pattern to dict."""
        pattern = Pattern("test", type=PatternType.SWARM)
        pattern.set_entry_agent("leader")
        pattern.add("follower")
        
        result = pattern.to_dict()
        assert result["entry_agent"] == "leader"
        assert "follower" in result["agents"]

class TestFactoryFunctions:
    """Test pattern factory functions."""
    
    def test_parallel_pattern_factory(self):
        """Test parallel pattern factory."""
        pattern = parallel_pattern(
            "test",
            "Test pattern",
            agents=["a1", "a2"],
            max_concurrent=2
        )
        assert pattern.type == PatternType.PARALLEL
        assert len(pattern.configs) == 2
        assert pattern.max_concurrent == 2
    
    def test_swarm_pattern_factory(self):
        """Test swarm pattern factory."""
        pattern = swarm_pattern(
            "test",
            "leader",
            "Test pattern",
            agents=["follower1", "follower2"]
        )
        assert pattern.type == PatternType.SWARM
        assert pattern.entry_agent == "leader"
        assert len(pattern.agents) == 3  # leader + 2 followers
    
    def test_hierarchical_pattern_factory(self):
        """Test hierarchical pattern factory."""
        pattern = hierarchical_pattern(
            "test",
            "root",
            "Test pattern",
            children=["child1", "child2"]
        )
        assert pattern.type == PatternType.HIERARCHICAL
        assert pattern.root_agent == "root"
        assert len(pattern.agents) == 3  # root + 2 children
    
    def test_sequential_pattern_factory(self):
        """Test sequential pattern factory."""
        pattern = sequential_pattern(
            "test",
            ["step1", "step2", "step3"],
            "Test pattern"
        )
        assert pattern.type == PatternType.SEQUENTIAL
        assert len(pattern.sequence) == 3
    
    def test_conditional_pattern_factory(self):
        """Test conditional pattern factory."""
        pattern = conditional_pattern(
            "test",
            {"cond1": "agent1", "cond2": "agent2"},
            "Test pattern"
        )
        assert pattern.type == PatternType.CONDITIONAL
        assert len(pattern.conditions) == 2

class TestPatternMetadata:
    """Test pattern metadata and additional features."""
    
    def test_pattern_with_metadata(self):
        """Test pattern with metadata."""
        pattern = Pattern(
            "test",
            type=PatternType.PARALLEL,
            metadata={"version": "1.0", "author": "test"}
        )
        assert pattern.metadata["version"] == "1.0"
        assert pattern.metadata["author"] == "test"
    
    def test_pattern_repr(self):
        """Test pattern string representation."""
        pattern = Pattern("test_pattern", type=PatternType.PARALLEL)
        pattern.add_parallel_agent("agent1")
        pattern.add_parallel_agent("agent2")
        
        repr_str = repr(pattern)
        assert "test_pattern" in repr_str
        assert "parallel" in repr_str
        assert "agents=2" in repr_str