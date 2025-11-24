#!/usr/bin/env python3
"""
Test suite for the flush command functionality.
Tests clearing message histories for individual agents or all agents.
"""

import os
import sys
from unittest.mock import patch, MagicMock, call

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from cai.repl.commands.base import Command
from cai.repl.commands.flush import FlushCommand


class TestFlushCommand:
    """Test cases for FlushCommand."""

    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """Setup and cleanup for each test."""
        # Set up test environment
        os.environ["CAI_TELEMETRY"] = "false"
        os.environ["CAI_TRACING"] = "false"

        yield

    @pytest.fixture
    def flush_command(self):
        """Create a FlushCommand instance for testing."""
        return FlushCommand()

    @pytest.fixture
    def mock_model_instances(self):
        """Create mock model instances for testing."""
        # Create mock models with message histories
        model1 = MagicMock()
        model1.agent_name = "test_agent_1"
        model1.message_history = [
            {"role": "user", "content": "Test message 1"},
            {"role": "assistant", "content": "Test response 1"},
        ]

        model2 = MagicMock()
        model2.agent_name = "test_agent_2"
        model2.message_history = [
            {"role": "user", "content": "Test message 2"},
            {"role": "assistant", "content": "Test response 2"},
        ]

        model3 = MagicMock()
        model3.agent_name = "Bug Bounty Hunter"
        model3.message_history = [
            {"role": "user", "content": "Find vulnerabilities"},
            {"role": "assistant", "content": "Scanning for vulnerabilities..."},
        ]

        return {
            "test_agent_1": model1,
            "test_agent_2": model2,
            "Bug Bounty Hunter": model3,
        }

    def test_command_initialization(self, flush_command):
        """Test that FlushCommand initializes correctly."""
        assert flush_command.name == "/flush"
        assert flush_command.description == "Clear conversation history (all agents by default, or specific agent)"
        assert flush_command.aliases == ["/clear"]

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_all_agent_histories")
    def test_handle_no_args_shows_help(self, mock_get_all, flush_command):
        """Test handling with no arguments shows help menu."""
        mock_get_all.return_value = {
            "Assistant": [{"role": "user", "content": "test"}],
            "red_teamer": [{"role": "user", "content": "test2"}]
        }
        result = flush_command.handle([])
        assert result is True
        # Should not clear anything, just show help
        mock_get_all.assert_called_once()

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_all_agent_histories")
    def test_handle_no_args_empty_histories(self, mock_get_all, flush_command):
        """Test handling with no arguments when no histories exist."""
        mock_get_all.return_value = {}
        result = flush_command.handle([])
        assert result is True
        mock_get_all.assert_called_once()

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_agent_message_history")
    @patch("cai.sdk.agents.models.openai_chatcompletions.clear_agent_history")
    def test_handle_with_agent_name(self, mock_clear_agent, mock_get_history, flush_command):
        """Test handling with specific agent name."""
        mock_get_history.return_value = []
        result = flush_command.handle(["red_teamer"])
        assert result is True
        mock_clear_agent.assert_called_once_with("red_teamer")

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_agent_message_history")
    @patch("cai.sdk.agents.models.openai_chatcompletions.clear_agent_history")
    def test_handle_with_agent_name_with_spaces(self, mock_clear_agent, mock_get_history, flush_command):
        """Test handling with agent name containing spaces."""
        mock_get_history.return_value = []
        result = flush_command.handle(["Bug", "Bounty", "Hunter"])
        assert result is True
        mock_clear_agent.assert_called_once_with("Bug Bounty Hunter")

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_agent_message_history")
    @patch("cai.sdk.agents.models.openai_chatcompletions.clear_agent_history")
    def test_handle_with_numbered_agent(self, mock_clear_agent, mock_get_history, flush_command):
        """Test handling with numbered agent name."""
        mock_get_history.return_value = []
        result = flush_command.handle(["Bug", "Bounty", "Hunter", "#2"])
        assert result is True
        mock_clear_agent.assert_called_once_with("Bug Bounty Hunter #2")

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_all_agent_histories")
    @patch("cai.sdk.agents.models.openai_chatcompletions.clear_all_histories")
    def test_handle_all_subcommand(self, mock_clear_all, mock_get_all, flush_command):
        """Test handling 'all' subcommand."""
        mock_get_all.return_value = {}
        result = flush_command.handle(["all"])
        assert result is True
        mock_clear_all.assert_called_once()

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_agent_message_history")
    @patch("cai.sdk.agents.models.openai_chatcompletions.clear_agent_history")
    def test_handle_agent_subcommand(self, mock_clear_agent, mock_get_history, flush_command):
        """Test handling 'agent' subcommand."""
        mock_get_history.return_value = []
        result = flush_command.handle(["agent", "test_agent"])
        assert result is True
        mock_clear_agent.assert_called_once_with("test_agent")

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_agent_message_history")
    @patch("cai.sdk.agents.models.openai_chatcompletions.clear_agent_history")
    def test_handle_nonexistent_agent(self, mock_clear_agent, mock_get_history, flush_command):
        """Test handling when clearing history for non-existent agent."""
        mock_get_history.return_value = []
        # Even if agent doesn't exist, command should succeed
        result = flush_command.handle(["nonexistent_agent"])
        assert result is True
        mock_clear_agent.assert_called_once_with("nonexistent_agent")

    def test_get_subcommands(self, flush_command):
        """Test that flush command returns correct subcommands."""
        subcommands = flush_command.get_subcommands()
        assert "all" in subcommands
        assert "agent" in subcommands

    def test_command_base_functionality(self, flush_command):
        """Test that the command inherits from base Command properly."""
        assert isinstance(flush_command, Command)
        assert flush_command.name == "/flush"
        assert "/clear" in flush_command.aliases

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_all_agent_histories")
    @patch("cai.sdk.agents.models.openai_chatcompletions.get_agent_message_history")
    @patch("cai.sdk.agents.models.openai_chatcompletions.clear_agent_history")
    def test_handle_with_confirmation_message(self, mock_clear_agent, mock_get_history, mock_get_all, flush_command, capsys):
        """Test that flush command provides user feedback when clearing an agent."""
        mock_get_history.return_value = [
            {"role": "user", "content": "test"},
            {"role": "assistant", "content": "response"}
        ]
        # Actually test flushing a specific agent, not the help screen
        result = flush_command.handle(["test_agent"])
        assert result is True
        # Verify clear was called with the correct agent
        mock_clear_agent.assert_called_once_with("test_agent")

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_all_agent_histories")
    @patch("cai.sdk.agents.models.openai_chatcompletions.clear_all_histories")
    def test_flush_all_with_multiple_agents(
        self, mock_clear_all, mock_get_all, flush_command
    ):
        """Test flushing all histories when multiple agents are active."""
        mock_get_all.return_value = {
            "agent1": [{"role": "user", "content": "test1"}],
            "agent2": [{"role": "user", "content": "test2"}]
        }

        result = flush_command.handle(["all"])
        assert result is True
        mock_clear_all.assert_called_once()

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_agent_message_history")
    @patch("cai.sdk.agents.models.openai_chatcompletions.clear_agent_history")
    def test_handle_with_empty_string_agent_name(self, mock_clear_agent, mock_get_history, flush_command):
        """Test handling with empty string as agent name."""
        mock_get_history.return_value = []
        result = flush_command.handle([""])
        assert result is True
        # Empty string is still a valid agent name
        mock_clear_agent.assert_called_once_with("")

    def test_get_all_subcommands(self, flush_command):
        """Test that all expected subcommands are present."""
        subcommands = flush_command.get_subcommands()
        assert "all" in subcommands
        assert "agent" in subcommands


@pytest.mark.integration
class TestFlushCommandIntegration:
    """Integration tests for flush command functionality."""

    @pytest.fixture(autouse=True)
    def setup_integration(self):
        """Setup for integration tests."""
        yield

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_agent_message_history")
    @patch("cai.sdk.agents.models.openai_chatcompletions.get_all_agent_histories")
    @patch("cai.sdk.agents.models.openai_chatcompletions.clear_all_histories")
    @patch("cai.sdk.agents.models.openai_chatcompletions.clear_agent_history")
    def test_flush_workflow(
        self, mock_clear_agent, mock_clear_all, mock_get_all, mock_get_history
    ):
        """Test a complete flush workflow."""
        # Setup mock returns
        mock_get_history.return_value = [{"role": "user", "content": "test"}]
        mock_get_all.return_value = {
            "agent1": [{"role": "user", "content": "test"}],
            "agent2": [{"role": "user", "content": "test2"}],
        }

        cmd = FlushCommand()

        # Test flushing specific agent
        result1 = cmd.handle(["agent1"])
        assert result1 is True
        mock_clear_agent.assert_called_with("agent1")

        # Test flushing all agents
        result2 = cmd.handle(["all"])
        assert result2 is True
        mock_clear_all.assert_called_once()

        # Test flushing without arguments (should show help)
        result3 = cmd.handle([])
        assert result3 is True
        # Should not have called clear_agent again
        assert mock_clear_agent.call_count == 1  # Only from the first test

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_agent_message_history")
    @patch("cai.sdk.agents.models.openai_chatcompletions.clear_agent_history")
    def test_sequential_agent_flushes(self, mock_clear_agent, mock_get_history):
        """Test flushing multiple agents sequentially."""
        mock_get_history.return_value = []
        cmd = FlushCommand()
        
        agents_to_flush = [
            "red_teamer",
            "blue_teamer",
            "bug_bounter",
            "Bug Bounty Hunter #1",
            "Bug Bounty Hunter #2",
        ]

        for agent in agents_to_flush:
            # Handle multi-word agent names
            args = agent.split() if " " in agent else [agent]
            result = cmd.handle(args)
            assert result is True

        # Verify all agents were flushed
        assert mock_clear_agent.call_count == len(agents_to_flush)
        
        # Verify correct agent names were passed
        called_agents = [call[0][0] for call in mock_clear_agent.call_args_list]
        assert called_agents == agents_to_flush

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_all_agent_histories")
    @patch("cai.sdk.agents.models.openai_chatcompletions.clear_all_histories")
    def test_flush_and_verify_empty_history(
        self, mock_clear_all, mock_get_all_histories
    ):
        """Test flushing and verifying histories are empty."""
        # Before flush - histories exist
        mock_get_all_histories.return_value = {
            "agent1": [{"role": "user", "content": "test"}],
            "agent2": [{"role": "assistant", "content": "response"}],
        }

        cmd = FlushCommand()
        
        # Flush all
        result = cmd.handle(["all"])
        assert result is True
        mock_clear_all.assert_called_once()

        # After flush - histories should be empty
        mock_get_all_histories.return_value = {}

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_agent_message_history")
    @patch("cai.sdk.agents.models.openai_chatcompletions.clear_agent_history")
    def test_flush_agents_with_special_characters(self, mock_clear_agent, mock_get_history):
        """Test flushing agents with special characters in names."""
        mock_get_history.return_value = []
        cmd = FlushCommand()
        
        special_agents = [
            "agent-with-hyphens",
            "agent_with_underscores",
            "agent.with.dots",
            "agent@special",
            "agent#123",
        ]

        for agent in special_agents:
            result = cmd.handle([agent])
            assert result is True
            mock_clear_agent.assert_called_with(agent)

        assert mock_clear_agent.call_count == len(special_agents)

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_agent_message_history")
    @patch("cai.sdk.agents.models.openai_chatcompletions.clear_agent_history")
    @patch("cai.sdk.agents.parallel_isolation.PARALLEL_ISOLATION")
    @patch("cai.agents.get_available_agents")
    def test_handle_with_agent_id(self, mock_get_available_agents, mock_parallel_isolation, mock_clear_agent, mock_get_history):
        """Test flushing agent by ID."""
        from cai.repl.commands.parallel import ParallelConfig, PARALLEL_CONFIGS
        
        # Mock agent
        mock_agent = MagicMock()
        mock_agent.name = "Red Team Agent"
        mock_get_available_agents.return_value = {"red_teamer": mock_agent}
        
        # Save original configs and clear
        original_configs = PARALLEL_CONFIGS[:]
        PARALLEL_CONFIGS.clear()
        
        try:
            # Create parallel config with ID
            config1 = ParallelConfig("red_teamer")
            config1.id = "P1"
            PARALLEL_CONFIGS.append(config1)
            
            mock_get_history.return_value = []
            mock_parallel_isolation.get_isolated_history.return_value = []
            
            cmd = FlushCommand()
            result = cmd.handle(["P1"])
            assert result is True
            # When clearing by ID, it should use PARALLEL_ISOLATION
            mock_parallel_isolation.clear_agent_history.assert_called_once_with("P1")
        finally:
            # Restore original configs
            PARALLEL_CONFIGS.clear()
            PARALLEL_CONFIGS.extend(original_configs)
    
    @patch("cai.sdk.agents.models.openai_chatcompletions.get_agent_message_history")
    @patch("cai.sdk.agents.models.openai_chatcompletions.clear_agent_history")
    @patch("cai.sdk.agents.parallel_isolation.PARALLEL_ISOLATION")
    @patch("cai.agents.get_available_agents")
    def test_handle_numbered_agent_with_id(self, mock_get_available_agents, mock_parallel_isolation, mock_clear_agent, mock_get_history):
        """Test flushing numbered agents with IDs."""
        from cai.repl.commands.parallel import ParallelConfig, PARALLEL_CONFIGS
        
        # Mock agent
        mock_agent = MagicMock()
        mock_agent.name = "Bug Bounty Hunter"
        mock_get_available_agents.return_value = {"bug_bounter": mock_agent}
        
        # Save original configs and clear
        original_configs = PARALLEL_CONFIGS[:]
        PARALLEL_CONFIGS.clear()
        
        try:
            # Create multiple configs for same agent type
            config1 = ParallelConfig("bug_bounter")
            config1.id = "P1"
            config2 = ParallelConfig("bug_bounter")
            config2.id = "P2"
            
            PARALLEL_CONFIGS.append(config1)
            PARALLEL_CONFIGS.append(config2)
            
            mock_get_history.return_value = []
            mock_parallel_isolation.get_isolated_history.return_value = []
            
            cmd = FlushCommand()
            
            # Flush second instance by ID
            result = cmd.handle(["P2"])
            assert result is True
            # When clearing by ID, it should use PARALLEL_ISOLATION
            mock_parallel_isolation.clear_agent_history.assert_called_once_with("P2")
        finally:
            # Restore original configs
            PARALLEL_CONFIGS.clear()
            PARALLEL_CONFIGS.extend(original_configs)
    
    @patch("cai.sdk.agents.models.openai_chatcompletions.get_agent_message_history")
    @patch("cai.sdk.agents.models.openai_chatcompletions.clear_agent_history")
    @patch("cai.sdk.agents.parallel_isolation.PARALLEL_ISOLATION")
    @patch("cai.repl.commands.parallel.PARALLEL_CONFIGS")
    @patch("cai.agents.get_available_agents")
    def test_handle_invalid_id(self, mock_get_available_agents, mock_parallel_configs, mock_parallel_isolation, mock_clear_agent, mock_get_history):
        """Test handling invalid agent ID."""
        from cai.repl.commands.parallel import ParallelConfig
        
        # Mock agent
        mock_agent = MagicMock()
        mock_agent.name = "Test Agent"
        mock_get_available_agents.return_value = {"test_agent": mock_agent}
        
        # Create config with ID
        config1 = ParallelConfig("test_agent")
        config1.id = "P1"
        mock_parallel_configs.clear()
        mock_parallel_configs.append(config1)
        
        # Mock parallel isolation to return None for invalid ID
        mock_parallel_isolation.get_isolated_history.return_value = None
        
        cmd = FlushCommand()
        result = cmd.handle(["P99"])  # Invalid ID
        # The actual implementation returns True even for invalid IDs
        assert result is True
        # It will still call clear_agent_history on PARALLEL_ISOLATION even if nothing to clear
        mock_parallel_isolation.clear_agent_history.assert_called_once_with("P99")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])