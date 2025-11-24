#!/usr/bin/env python3
"""
Test suite for the parallel command functionality.
Tests all handle methods and input possibilities for the parallel command.
"""

import os
import sys
import pytest
from unittest.mock import patch, Mock, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 
                                '..', '..', 'src'))

from cai.repl.commands.parallel import ParallelCommand, ParallelConfig
import cai.repl.commands.parallel as parallel_module
from cai.repl.commands.base import Command


class TestParallelCommand:
    """Test cases for ParallelCommand."""
    
    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """Setup and cleanup for each test."""
        # Clear parallel configs before each test
        parallel_module.PARALLEL_CONFIGS.clear()
        
        # Set up test environment
        os.environ['CAI_TELEMETRY'] = 'false'
        os.environ['CAI_TRACING'] = 'false'
        
        yield
        
        # Cleanup after each test
        parallel_module.PARALLEL_CONFIGS.clear()
    
    @pytest.fixture
    def parallel_command(self):
        """Create a ParallelCommand instance for testing."""
        return ParallelCommand()
    
    def test_command_initialization(self, parallel_command):
        """Test that ParallelCommand initializes correctly."""
        assert parallel_command.name == "/parallel"
        assert parallel_command.description == "Configure multiple agents to run in parallel with different settings"
        assert parallel_command.aliases == ["/par", "/p"]
        
        # Check subcommands are registered
        expected_subcommands = ["add", "list", "clear", "remove", "override-models", "merge", "prompt"]
        assert set(parallel_command.get_subcommands()) == set(expected_subcommands)
    
    def test_parallel_config_initialization(self):
        """Test ParallelConfig initialization."""
        config = ParallelConfig("test_agent", "gpt-4", "Test prompt")
        assert config.agent_name == "test_agent"
        assert config.model == "gpt-4"
        assert config.prompt == "Test prompt"
        assert config.id is None  # ID should be None initially
        
        # Test default values
        config_default = ParallelConfig("test_agent")
        assert config_default.agent_name == "test_agent"
        assert config_default.model is None
        assert config_default.prompt is None
        assert config_default.id is None
    
    def test_parallel_config_str_representation(self):
        """Test ParallelConfig string representation."""
        # Test with all parameters
        config = ParallelConfig("test_agent", "gpt-4", "Test prompt")
        str_repr = str(config)
        assert "Agent: test_agent" in str_repr
        assert "model: gpt-4" in str_repr
        assert "prompt: 'Test prompt'" in str_repr
        
        # Test with long prompt (should be truncated)
        long_prompt = "This is a very long prompt that should be truncated when displayed"
        config_long = ParallelConfig("test_agent", "gpt-4", long_prompt)
        str_repr_long = str(config_long)
        assert "..." in str_repr_long
        
        # Test with minimal parameters
        config_minimal = ParallelConfig("test_agent")
        str_repr_minimal = str(config_minimal)
        assert "Agent: test_agent" in str_repr_minimal
        assert "model:" not in str_repr_minimal
        assert "prompt:" not in str_repr_minimal

    @patch('cai.repl.commands.parallel.get_available_agents')
    def test_handle_add_valid_agent(self, mock_get_agents, parallel_command):
        """Test adding a valid agent to parallel config."""
        # Mock available agents
        mock_get_agents.return_value = {
            "test_agent": Mock(),
            "another_agent": Mock()
        }
        
        # Test basic add
        result = parallel_command.handle_add(["test_agent"])
        assert result is True
        assert len(parallel_module.PARALLEL_CONFIGS) == 1
        assert parallel_module.PARALLEL_CONFIGS[0].agent_name == "test_agent"
        assert parallel_module.PARALLEL_CONFIGS[0].model is None
        assert parallel_module.PARALLEL_CONFIGS[0].prompt is None
        assert parallel_module.PARALLEL_CONFIGS[0].id == "P1"  # Should be assigned P1
    
    @patch('cai.repl.commands.parallel.get_available_agents')
    def test_handle_add_with_model_and_prompt(self, mock_get_agents, parallel_command):
        """Test adding agent with model and prompt parameters."""
        mock_get_agents.return_value = {"test_agent": Mock()}
        
        args = ["test_agent", "--model", "gpt-4", "--prompt", "Custom prompt"]
        result = parallel_command.handle_add(args)
        
        assert result is True
        assert len(parallel_module.PARALLEL_CONFIGS) == 1
        config = parallel_module.PARALLEL_CONFIGS[0]
        assert config.agent_name == "test_agent"
        assert config.model == "gpt-4"
        assert config.prompt == "Custom prompt"
    
    @patch('cai.repl.commands.parallel.get_available_agents')
    def test_handle_add_invalid_agent(self, mock_get_agents, parallel_command):
        """Test adding an invalid agent name."""
        mock_get_agents.return_value = {"valid_agent": Mock()}
        
        result = parallel_command.handle_add(["invalid_agent"])
        assert result is False
        assert len(parallel_module.PARALLEL_CONFIGS) == 0
    
    def test_handle_add_no_args(self, parallel_command):
        """Test add command with no arguments."""
        result = parallel_command.handle_add([])
        assert result is False
        assert len(parallel_module.PARALLEL_CONFIGS) == 0
    
    @patch('cai.repl.commands.parallel.get_available_agents')
    def test_handle_add_multiple_agents(self, mock_get_agents, parallel_command):
        """Test adding multiple agents."""
        mock_get_agents.return_value = {
            "agent1": Mock(),
            "agent2": Mock(),
            "agent3": Mock()
        }
        
        # Add first agent
        result1 = parallel_command.handle_add(["agent1", "--model", "gpt-4"])
        assert result1 is True
        
        # Add second agent
        result2 = parallel_command.handle_add(["agent2", "--prompt", "Second prompt"])
        assert result2 is True
        
        # Add third agent
        result3 = parallel_command.handle_add(["agent3"])
        assert result3 is True
        
        assert len(parallel_module.PARALLEL_CONFIGS) == 3
        assert parallel_module.PARALLEL_CONFIGS[0].agent_name == "agent1"
        assert parallel_module.PARALLEL_CONFIGS[1].agent_name == "agent2"
        assert parallel_module.PARALLEL_CONFIGS[2].agent_name == "agent3"
        
        # Check IDs are assigned correctly
        assert parallel_module.PARALLEL_CONFIGS[0].id == "P1"
        assert parallel_module.PARALLEL_CONFIGS[1].id == "P2"
        assert parallel_module.PARALLEL_CONFIGS[2].id == "P3"
    
    def test_handle_list_empty(self, parallel_command):
        """Test listing when no parallel configs exist."""
        result = parallel_command.handle_list([])
        assert result is True
        assert len(parallel_module.PARALLEL_CONFIGS) == 0
    
    def test_handle_list_with_configs(self, parallel_command):
        """Test listing existing parallel configs."""
        # Add some configs
        parallel_module.PARALLEL_CONFIGS.append(ParallelConfig("agent1", "gpt-4", "Prompt 1"))
        parallel_module.PARALLEL_CONFIGS.append(ParallelConfig("agent2", None, None))
        parallel_module.PARALLEL_CONFIGS.append(ParallelConfig("agent3", "claude", "Long prompt"))
        
        result = parallel_command.handle_list([])
        assert result is True
    
    def test_handle_clear_empty(self, parallel_command):
        """Test clearing empty parallel configs."""
        result = parallel_command.handle_clear([])
        assert result is True
        assert len(parallel_module.PARALLEL_CONFIGS) == 0
    
    def test_handle_clear_with_configs(self, parallel_command):
        """Test clearing existing parallel configs."""
        # Add some configs
        parallel_module.PARALLEL_CONFIGS.append(ParallelConfig("agent1"))
        parallel_module.PARALLEL_CONFIGS.append(ParallelConfig("agent2"))
        parallel_module.PARALLEL_CONFIGS.append(ParallelConfig("agent3"))
        
        assert len(parallel_module.PARALLEL_CONFIGS) == 3
        
        result = parallel_command.handle_clear([])
        assert result is True
        assert len(parallel_module.PARALLEL_CONFIGS) == 0
    
    def test_handle_remove_valid_index(self, parallel_command):
        """Test removing a config by valid index."""
        # Add some configs
        parallel_module.PARALLEL_CONFIGS.append(ParallelConfig("agent1"))
        parallel_module.PARALLEL_CONFIGS.append(ParallelConfig("agent2"))
        parallel_module.PARALLEL_CONFIGS.append(ParallelConfig("agent3"))
        
        # Remove the second config (index 2)
        result = parallel_command.handle_remove(["2"])
        assert result is True
        assert len(parallel_module.PARALLEL_CONFIGS) == 2
        assert parallel_module.PARALLEL_CONFIGS[0].agent_name == "agent1"
        assert parallel_module.PARALLEL_CONFIGS[1].agent_name == "agent3"
    
    def test_handle_remove_invalid_index(self, parallel_command):
        """Test removing with invalid index."""
        parallel_module.PARALLEL_CONFIGS.append(ParallelConfig("agent1"))
        
        # Test invalid numeric index
        result1 = parallel_command.handle_remove(["5"])
        assert result1 is False
        assert len(parallel_module.PARALLEL_CONFIGS) == 1
        
        # Test negative index
        result2 = parallel_command.handle_remove(["-1"])
        assert result2 is False
        assert len(parallel_module.PARALLEL_CONFIGS) == 1
        
        # Test non-numeric index
        result3 = parallel_command.handle_remove(["invalid"])
        assert result3 is False
        assert len(parallel_module.PARALLEL_CONFIGS) == 1
    
    def test_handle_remove_no_args(self, parallel_command):
        """Test remove command with no arguments."""
        parallel_module.PARALLEL_CONFIGS.append(ParallelConfig("agent1"))
        
        result = parallel_command.handle_remove([])
        assert result is False
        assert len(parallel_module.PARALLEL_CONFIGS) == 1
    
    def test_command_base_functionality(self, parallel_command):
        """Test that the command inherits from base Command properly."""
        assert isinstance(parallel_command, Command)
        assert parallel_command.name == "/parallel"
        assert "/par" in parallel_command.aliases
        assert "/p" in parallel_command.aliases
    
    @patch('cai.repl.commands.parallel.get_available_agents')
    def test_handle_main_command_routing(self, mock_get_agents, parallel_command):
        """Test that main handle method routes to correct subcommands."""
        mock_get_agents.return_value = {"test_agent": Mock()}
        
        # Test routing to add
        result1 = parallel_command.handle(["add", "test_agent"])
        assert result1 is True
        assert len(parallel_module.PARALLEL_CONFIGS) == 1
        
        # Test routing to list
        result2 = parallel_command.handle(["list"])
        assert result2 is True
        
        # Test routing to clear
        result3 = parallel_command.handle(["clear"])
        assert result3 is True
        assert len(parallel_module.PARALLEL_CONFIGS) == 0
    
    def test_handle_unknown_subcommand(self, parallel_command):
        """Test handling of unknown subcommands."""
        # This will use the default handle method from base class
        # which should route to handle_unknown_subcommand
        result = parallel_command.handle(["unknown_subcommand"])
        assert result is False
    
    def test_handle_no_args(self, parallel_command):
        """Test handling when no arguments provided."""
        # The base handle method should route to handle_no_args
        result = parallel_command.handle([])
        assert result is True  # handle_no_args returns True when successful


@pytest.mark.integration
class TestParallelCommandIntegration:
    """Integration tests for parallel command functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_integration(self):
        """Setup for integration tests."""
        parallel_module.PARALLEL_CONFIGS.clear()
        yield
        parallel_module.PARALLEL_CONFIGS.clear()
    
    @patch('cai.repl.commands.parallel.get_available_agents')
    def test_full_workflow(self, mock_get_agents):
        """Test a complete workflow of adding, listing, and removing configs."""
        mock_get_agents.return_value = {
            "agent1": Mock(),
            "agent2": Mock(),
            "agent3": Mock()
        }
        
        cmd = ParallelCommand()
        
        # Start with empty configs
        assert len(parallel_module.PARALLEL_CONFIGS) == 0
        
        # Add multiple configs
        cmd.handle(["add", "agent1", "--model", "gpt-4"])
        cmd.handle(["add", "agent2", "--prompt", "Test prompt"])
        cmd.handle(["add", "agent3", "--model", "claude", "--prompt", "Another prompt"])
        
        assert len(parallel_module.PARALLEL_CONFIGS) == 3
        
        # List configs (should not change count)
        cmd.handle(["list"])
        assert len(parallel_module.PARALLEL_CONFIGS) == 3
        
        # Remove one config
        cmd.handle(["remove", "2"])
        assert len(parallel_module.PARALLEL_CONFIGS) == 2
        
        # Clear all configs
        cmd.handle(["clear"])
        assert len(parallel_module.PARALLEL_CONFIGS) == 0
    
    @patch('cai.repl.commands.parallel.get_available_agents')
    def test_edge_case_combinations(self, mock_get_agents):
        """Test edge cases and unusual parameter combinations."""
        mock_get_agents.return_value = {"test_agent": Mock()}
        
        cmd = ParallelCommand()
        
        # Test partial parameters
        result1 = cmd.handle(["add", "test_agent", "--model"])
        assert result1 is True  # Should still work with incomplete args
        
        # Test empty string parameters
        result2 = cmd.handle(["add", "test_agent", "--prompt", ""])
        assert result2 is True
        
        # Test parameters in different order
        result3 = cmd.handle(["add", "test_agent", "--prompt", "Test", "--model", "gpt-4"])
        assert result3 is True
        
        assert len(parallel_module.PARALLEL_CONFIGS) == 3
    
    @patch('cai.repl.commands.parallel.get_available_agents')
    def test_handle_remove_by_id(self, mock_get_agents):
        """Test removing agents by ID."""
        mock_get_agents.return_value = {
            "agent1": Mock(),
            "agent2": Mock(),
            "agent3": Mock()
        }
        
        cmd = ParallelCommand()
        
        # Add multiple configs
        cmd.handle_add(["agent1"])
        cmd.handle_add(["agent2"])
        cmd.handle_add(["agent3"])
        
        assert len(parallel_module.PARALLEL_CONFIGS) == 3
        assert parallel_module.PARALLEL_CONFIGS[0].id == "P1"
        assert parallel_module.PARALLEL_CONFIGS[1].id == "P2"
        assert parallel_module.PARALLEL_CONFIGS[2].id == "P3"
        
        # Remove by ID
        result = cmd.handle_remove(["P2"])
        assert result is True
        assert len(parallel_module.PARALLEL_CONFIGS) == 2
        assert parallel_module.PARALLEL_CONFIGS[0].agent_name == "agent1"
        assert parallel_module.PARALLEL_CONFIGS[1].agent_name == "agent3"
        
        # Check IDs are reassigned after removal
        assert parallel_module.PARALLEL_CONFIGS[0].id == "P1"
        assert parallel_module.PARALLEL_CONFIGS[1].id == "P2"
        
        # Test invalid ID
        result2 = cmd.handle_remove(["P99"])
        assert result2 is False
        assert len(parallel_module.PARALLEL_CONFIGS) == 2
    
    @patch('cai.repl.commands.parallel.get_available_agents')
    def test_parse_agent_names_with_ids(self, mock_get_agents):
        """Test parsing agent names that includes IDs."""
        mock_agent = Mock()
        mock_agent.name = "Test Agent"
        
        mock_get_agents.return_value = {
            "test_agent": mock_agent
        }
        
        cmd = ParallelCommand()
        
        # Add agents to parallel_module.PARALLEL_CONFIGS
        cmd.handle_add(["test_agent"])
        cmd.handle_add(["test_agent"])
        
        # Mock all_histories to simulate agents with message history
        all_histories = {
            "Test Agent #1": [],
            "Test Agent #2": []
        }
        
        # Test parsing IDs
        result = cmd._parse_agent_names(["P1", "P2"], all_histories)
        assert len(result) == 2
        assert "Test Agent #1" in result
        assert "Test Agent #2" in result
        
        # Test mixed IDs and names
        result2 = cmd._parse_agent_names(["P1", "Test Agent #2"], all_histories)
        assert len(result2) == 2
    
    @patch('cai.repl.commands.parallel.get_available_agents')
    def test_merge_with_remove_sources(self, mock_get_agents):
        """Test merging agents with --remove-sources flag."""
        # This is a simplified test that just checks the remove functionality
        # The actual merge logic is complex and requires many mocks
        cmd = ParallelCommand()
        
        # Mock available agents
        mock_agent = Mock()
        mock_agent.name = "Test Agent"
        mock_get_agents.return_value = {"test_agent": mock_agent}
        
        # Add agents to parallel configs
        cmd.handle_add(["test_agent"])
        cmd.handle_add(["test_agent"])
        
        assert len(parallel_module.PARALLEL_CONFIGS) == 2
        
        # Test removal after merge
        # When we merge with --remove-sources and less than 2 agents remain,
        # all configs should be cleared
        cmd.handle_remove(["1"])
        assert len(parallel_module.PARALLEL_CONFIGS) == 1
        
        # Removing one more should clear all configs (less than 2 agents)
        # This simulates what happens after merge with --remove-sources
        cmd.handle_clear([])
        assert len(parallel_module.PARALLEL_CONFIGS) == 0
    
    @patch('cai.repl.commands.parallel.get_available_agents')
    @patch('cai.repl.commands.parallel.get_all_agent_histories')
    def test_merge_case_insensitive(self, mock_get_histories, mock_get_agents):
        """Test that agent name matching is case-insensitive in merge."""
        mock_agent = Mock()
        mock_agent.name = "Test Agent"
        
        mock_get_agents.return_value = {
            "test_agent": mock_agent
        }
        
        # Mock message histories with mixed case
        mock_get_histories.return_value = {
            "Test Agent": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"}
            ],
            "Another Agent": [
                {"role": "user", "content": "Greetings"},
                {"role": "assistant", "content": "Hello!"}
            ]
        }
        
        cmd = ParallelCommand()
        
        # Test case-insensitive parsing
        result = cmd._parse_agent_names(["test agent", "ANOTHER AGENT"], mock_get_histories.return_value)
        assert len(result) == 2
        assert "Test Agent" in result
        assert "Another Agent" in result
    
    @patch('cai.repl.commands.parallel.get_available_agents')
    def test_handle_prompt_command(self, mock_get_agents):
        """Test the prompt subcommand."""
        mock_get_agents.return_value = {
            "test_agent": Mock(name="Test Agent")
        }
        
        cmd = ParallelCommand()
        
        # Add an agent
        cmd.handle_add(["test_agent"])
        assert parallel_module.PARALLEL_CONFIGS[0].prompt is None
        
        # Set prompt using ID
        result = cmd.handle_prompt(["P1", "Focus on SQL injection"])
        assert result is True
        assert parallel_module.PARALLEL_CONFIGS[0].prompt == "Focus on SQL injection"
        
        # Update prompt
        result2 = cmd.handle_prompt(["P1", "Look for XSS vulnerabilities"])
        assert result2 is True
        assert parallel_module.PARALLEL_CONFIGS[0].prompt == "Look for XSS vulnerabilities"
        
        # Test with invalid ID
        result3 = cmd.handle_prompt(["P99", "Invalid"])
        assert result3 is False
        
        # Test with no args
        result4 = cmd.handle_prompt([])
        assert result4 is False


if __name__ == '__main__':
    pytest.main([__file__, "-v"]) 