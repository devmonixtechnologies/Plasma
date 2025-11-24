#!/usr/bin/env python3
"""
Test suite for the load command functionality.
Tests loading JSONL files into agent message histories.
"""

import json
import os
import sys
from unittest.mock import patch, MagicMock, mock_open

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from cai.repl.commands.base import Command
from cai.repl.commands.load import LoadCommand


class TestLoadCommand:
    """Test cases for LoadCommand."""

    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """Setup and cleanup for each test."""
        # Set up test environment
        os.environ["CAI_TELEMETRY"] = "false"
        os.environ["CAI_TRACING"] = "false"

        yield

    @pytest.fixture
    def load_command(self):
        """Create a LoadCommand instance for testing."""
        return LoadCommand()

    @pytest.fixture
    def sample_jsonl_messages(self):
        """Create sample messages that would be loaded from JSONL."""
        return [
            {"role": "user", "content": "Hello from JSONL"},
            {"role": "assistant", "content": "Response from JSONL"},
            {"role": "user", "content": "Another message"},
            {"role": "assistant", "content": "Another response"},
        ]

    @pytest.fixture
    def mock_agent_histories(self):
        """Create mock agent histories for testing."""
        return {
            "Default Agent": [],
            "red_teamer": [{"role": "user", "content": "Existing message"}],
            "Bug Bounty Hunter": [],
        }

    def test_command_initialization(self, load_command):
        """Test that LoadCommand initializes correctly."""
        assert load_command.name == "/load"
        assert load_command.description == "Merge a jsonl file into agent histories with duplicate control (uses logs/last if no file specified)"
        assert load_command.aliases == ["/l"]

    @patch("cai.repl.commands.load.console.input")
    @patch("cai.agents.get_agent_by_name")
    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    @patch("cai.sdk.agents.models.openai_chatcompletions.ACTIVE_MODEL_INSTANCES", {})
    @patch("cai.sdk.agents.models.openai_chatcompletions.PERSISTENT_MESSAGE_HISTORIES", {})
    @patch("cai.repl.commands.load.load_history_from_jsonl")
    def test_handle_no_args_default_file(
        self, mock_load_jsonl, mock_agent_manager, mock_get_agent, mock_input, load_command, sample_jsonl_messages
    ):
        """Test handling with no arguments (uses default file and agent)."""
        mock_input.return_value = "n"  # Don't create memory
        mock_load_jsonl.return_value = sample_jsonl_messages
        
        # Mock AGENT_MANAGER methods
        mock_agent_manager.get_active_agents.return_value = {}
        mock_agent_manager.get_registered_agents.return_value = {}
        mock_agent_manager._message_history = {}
        mock_agent_manager._agent_registry = {}
        mock_agent_manager._id_counter = 0
        mock_agent_manager.set_active_agent = MagicMock()
        
        result = load_command.handle([])
        assert result is True
        
        # Should load from default file
        mock_load_jsonl.assert_called_with("logs/last")

    @patch("cai.repl.commands.load.console.input")
    @patch("cai.agents.get_agent_by_name")
    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    @patch("cai.sdk.agents.models.openai_chatcompletions.ACTIVE_MODEL_INSTANCES", {})
    @patch("cai.sdk.agents.models.openai_chatcompletions.PERSISTENT_MESSAGE_HISTORIES", {})
    @patch("cai.repl.commands.load.load_history_from_jsonl")
    def test_handle_with_file_path_only(
        self, mock_load_jsonl, mock_agent_manager, mock_get_agent, mock_input, load_command, sample_jsonl_messages
    ):
        """Test handling with file path only (loads to default agent)."""
        mock_input.return_value = "n"  # Don't create memory
        mock_load_jsonl.return_value = sample_jsonl_messages
        
        # Mock AGENT_MANAGER methods
        mock_agent_manager.get_active_agents.return_value = {}
        mock_agent_manager.get_registered_agents.return_value = {}
        mock_agent_manager._message_history = {}
        mock_agent_manager._agent_registry = {}
        mock_agent_manager._id_counter = 0
        mock_agent_manager.set_active_agent = MagicMock()
        
        result = load_command.handle(["logs/session.jsonl"])
        assert result is True
        
        mock_load_jsonl.assert_called_with("logs/session.jsonl")

    @patch("cai.repl.commands.load.console.input")
    @patch("cai.agents.get_agent_by_name")
    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    @patch("cai.sdk.agents.models.openai_chatcompletions.ACTIVE_MODEL_INSTANCES", {})
    @patch("cai.sdk.agents.models.openai_chatcompletions.PERSISTENT_MESSAGE_HISTORIES", {})
    @patch("cai.repl.commands.load.load_history_from_jsonl")
    def test_handle_with_agent_name_only(
        self, mock_load_jsonl, mock_agent_manager, mock_get_agent, mock_input, load_command, sample_jsonl_messages
    ):
        """Test handling with agent name only (uses default file)."""
        mock_input.return_value = "n"  # Don't create memory
        mock_load_jsonl.return_value = sample_jsonl_messages
        
        # Mock AGENT_MANAGER methods
        mock_agent_manager.get_agent_by_id.return_value = None
        mock_agent_manager._message_history = {}
        mock_agent_manager._agent_registry = {}
        mock_agent_manager._id_counter = 0
        
        result = load_command.handle(["red_teamer"])
        assert result is True
        
        mock_load_jsonl.assert_called_with("logs/last")

    @patch("cai.repl.commands.load.console.input")
    @patch("cai.agents.get_agent_by_name")
    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    @patch("cai.sdk.agents.models.openai_chatcompletions.ACTIVE_MODEL_INSTANCES", {})
    @patch("cai.sdk.agents.models.openai_chatcompletions.PERSISTENT_MESSAGE_HISTORIES", {})
    @patch("cai.repl.commands.load.load_history_from_jsonl")
    def test_handle_with_agent_and_file(
        self, mock_load_jsonl, mock_agent_manager, mock_get_agent, mock_input, load_command, sample_jsonl_messages
    ):
        """Test handling with both agent name and file path."""
        mock_input.return_value = "n"  # Don't create memory
        mock_load_jsonl.return_value = sample_jsonl_messages
        
        # Mock AGENT_MANAGER methods
        mock_agent_manager.get_agent_by_id.return_value = None
        mock_agent_manager._message_history = {}
        mock_agent_manager._agent_registry = {}
        mock_agent_manager._id_counter = 0
        
        result = load_command.handle(["red_teamer", "logs/session.jsonl"])
        assert result is True
        
        mock_load_jsonl.assert_called_with("logs/session.jsonl")

    @patch("cai.repl.commands.load.console.input")
    @patch("cai.agents.get_agent_by_name")
    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    @patch("cai.sdk.agents.models.openai_chatcompletions.ACTIVE_MODEL_INSTANCES", {})
    @patch("cai.sdk.agents.models.openai_chatcompletions.PERSISTENT_MESSAGE_HISTORIES", {})
    @patch("cai.repl.commands.load.load_history_from_jsonl")
    def test_handle_agent_with_spaces(
        self, mock_load_jsonl, mock_agent_manager, mock_get_agent, mock_input, load_command, sample_jsonl_messages
    ):
        """Test handling agent names with spaces."""
        mock_input.return_value = "n"  # Don't create memory
        mock_load_jsonl.return_value = sample_jsonl_messages
        
        # Mock AGENT_MANAGER methods
        mock_agent_manager.get_agent_by_id.return_value = None
        mock_agent_manager._message_history = {}
        mock_agent_manager._agent_registry = {}
        mock_agent_manager._id_counter = 0
        
        result = load_command.handle(["Bug", "Bounty", "Hunter"])
        assert result is True
        
        mock_load_jsonl.assert_called_with("logs/last")

    @patch("cai.repl.commands.load.console.input")
    @patch("cai.agents.get_agent_by_name")
    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    @patch("cai.sdk.agents.models.openai_chatcompletions.ACTIVE_MODEL_INSTANCES", {})
    @patch("cai.sdk.agents.models.openai_chatcompletions.PERSISTENT_MESSAGE_HISTORIES", {})
    @patch("cai.repl.commands.load.load_history_from_jsonl")
    def test_handle_agent_with_spaces_and_file(
        self, mock_load_jsonl, mock_agent_manager, mock_get_agent, mock_input, load_command, sample_jsonl_messages
    ):
        """Test handling agent names with spaces plus file path."""
        mock_input.return_value = "n"  # Don't create memory
        mock_load_jsonl.return_value = sample_jsonl_messages
        
        # Mock AGENT_MANAGER methods
        mock_agent_manager.get_agent_by_id.return_value = None
        mock_agent_manager._message_history = {}
        mock_agent_manager._agent_registry = {}
        mock_agent_manager._id_counter = 0
        
        result = load_command.handle(["Bug", "Bounty", "Hunter", "logs/session.jsonl"])
        assert result is True
        
        mock_load_jsonl.assert_called_with("logs/session.jsonl")

    @patch("cai.repl.commands.load.get_all_agent_histories")
    def test_handle_all_subcommand(self, mock_get_all, load_command, mock_agent_histories):
        """Test 'all' subcommand showing available agents."""
        mock_get_all.return_value = mock_agent_histories

        result = load_command.handle(["all"])
        assert result is True
        mock_get_all.assert_called_once()

    @patch("cai.repl.commands.load.console.input")
    @patch("cai.agents.get_agent_by_name")
    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    @patch("cai.sdk.agents.models.openai_chatcompletions.ACTIVE_MODEL_INSTANCES", {})
    @patch("cai.sdk.agents.models.openai_chatcompletions.PERSISTENT_MESSAGE_HISTORIES", {})
    @patch("cai.repl.commands.load.load_history_from_jsonl")
    def test_handle_agent_subcommand(
        self, mock_load_jsonl, mock_agent_manager, mock_get_agent, mock_input, load_command, sample_jsonl_messages
    ):
        """Test 'agent' subcommand with explicit agent specification."""
        mock_input.return_value = "n"  # Don't create memory
        mock_load_jsonl.return_value = sample_jsonl_messages
        
        # Mock AGENT_MANAGER methods
        mock_agent_manager.get_agent_by_id.return_value = None
        mock_agent_manager._message_history = {}
        mock_agent_manager._agent_registry = {}
        mock_agent_manager._id_counter = 0
        
        result = load_command.handle(["agent", "red_teamer"])
        assert result is True
        
        mock_load_jsonl.assert_called_with("logs/last")

    @patch("cai.repl.commands.load.console.input")
    @patch("cai.agents.get_agent_by_name")
    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    @patch("cai.sdk.agents.models.openai_chatcompletions.ACTIVE_MODEL_INSTANCES", {})
    @patch("cai.sdk.agents.models.openai_chatcompletions.PERSISTENT_MESSAGE_HISTORIES", {})
    @patch("cai.repl.commands.load.load_history_from_jsonl")
    def test_handle_agent_subcommand_with_file(
        self, mock_load_jsonl, mock_agent_manager, mock_get_agent, mock_input, load_command, sample_jsonl_messages
    ):
        """Test 'agent' subcommand with agent and file."""
        mock_input.return_value = "n"  # Don't create memory
        mock_load_jsonl.return_value = sample_jsonl_messages
        
        # Mock AGENT_MANAGER methods
        mock_agent_manager.get_agent_by_id.return_value = None
        mock_agent_manager._message_history = {}
        mock_agent_manager._agent_registry = {}
        mock_agent_manager._id_counter = 0
        
        result = load_command.handle(["agent", "red_teamer", "logs/session.jsonl"])
        assert result is True
        
        mock_load_jsonl.assert_called_with("logs/session.jsonl")

    @patch("cai.repl.commands.load.load_history_from_jsonl")
    @patch("cai.repl.commands.load.get_agent_message_history")
    def test_load_file_not_found(self, mock_get_history, mock_load_jsonl, load_command):
        """Test handling when JSONL file is not found."""
        mock_load_jsonl.side_effect = Exception("File not found")

        result = load_command.handle(["nonexistent.jsonl"])
        assert result is False

    @patch("cai.repl.commands.load.console.input")
    @patch("cai.agents.get_agent_by_name")
    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    @patch("cai.sdk.agents.models.openai_chatcompletions.ACTIVE_MODEL_INSTANCES", {})
    @patch("cai.sdk.agents.models.openai_chatcompletions.PERSISTENT_MESSAGE_HISTORIES", {})
    @patch("cai.repl.commands.load.load_history_from_jsonl")
    def test_load_empty_file(self, mock_load_jsonl, mock_agent_manager, mock_get_agent, mock_input, load_command):
        """Test loading an empty JSONL file."""
        mock_input.return_value = "n"  # Don't create memory
        mock_load_jsonl.return_value = []
        
        # Mock AGENT_MANAGER methods
        mock_agent_manager.get_active_agents.return_value = {}
        mock_agent_manager.get_registered_agents.return_value = {}
        mock_agent_manager._message_history = {}
        mock_agent_manager._agent_registry = {}
        mock_agent_manager._id_counter = 0
        mock_agent_manager.set_active_agent = MagicMock()
        
        result = load_command.handle([])
        assert result is True

    @patch("cai.repl.commands.load.console.input")
    @patch("cai.agents.get_agent_by_name")
    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    @patch("cai.sdk.agents.models.openai_chatcompletions.ACTIVE_MODEL_INSTANCES", {})
    @patch("cai.sdk.agents.models.openai_chatcompletions.PERSISTENT_MESSAGE_HISTORIES", {})
    @patch("cai.repl.commands.load.load_history_from_jsonl")
    def test_append_to_existing_history(
        self, mock_load_jsonl, mock_agent_manager, mock_get_agent, mock_input, load_command, sample_jsonl_messages
    ):
        """Test that messages are appended to existing history."""
        mock_input.return_value = "n"  # Don't create memory
        mock_load_jsonl.return_value = sample_jsonl_messages
        existing_history = [
            {"role": "user", "content": "Existing message 1"},
            {"role": "assistant", "content": "Existing response 1"},
        ]
        
        # Mock AGENT_MANAGER methods
        mock_agent_manager.get_agent_by_id.return_value = None
        mock_agent_manager._message_history = {}
        mock_agent_manager._agent_registry = {}
        mock_agent_manager._id_counter = 0
        
        result = load_command.handle(["red_teamer"])
        assert result is True

    @patch("cai.repl.commands.load.get_all_agent_histories")
    def test_handle_all_empty_histories(self, mock_get_all, load_command):
        """Test 'all' subcommand when no agents exist."""
        mock_get_all.return_value = {}

        result = load_command.handle(["all"])
        assert result is True
    
    @patch("cai.agents.get_available_agents")
    @patch("cai.repl.commands.load.get_all_agent_histories")
    def test_handle_all_with_configured_agents_no_history(self, mock_get_all, mock_get_available, load_command):
        """Test 'all' subcommand shows configured agents even without history."""
        from cai.repl.commands.parallel import ParallelConfig, PARALLEL_CONFIGS
        
        # Mock available agents
        mock_agent = MagicMock()
        mock_agent.name = "Red Team Agent"
        mock_get_available.return_value = {"red_teamer": mock_agent}
        
        # Save original configs and clear
        original_configs = PARALLEL_CONFIGS[:]
        PARALLEL_CONFIGS.clear()
        
        try:
            # Create parallel config
            config = ParallelConfig("red_teamer")
            config.id = "P1"
            PARALLEL_CONFIGS.append(config)
            
            # No message history
            mock_get_all.return_value = {}
            
            result = load_command.handle(["all"])
            assert result is True
            # Should succeed and show configured agent
        finally:
            # Restore original configs
            PARALLEL_CONFIGS.clear()
            PARALLEL_CONFIGS.extend(original_configs)

    def test_command_base_functionality(self, load_command):
        """Test that the command inherits from base Command properly."""
        assert isinstance(load_command, Command)
        assert load_command.name == "/load"
        assert "/l" in load_command.aliases

    @patch("cai.repl.commands.load.console.input")
    @patch("cai.agents.get_agent_by_name")
    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    @patch("cai.sdk.agents.models.openai_chatcompletions.ACTIVE_MODEL_INSTANCES", {})
    @patch("cai.sdk.agents.models.openai_chatcompletions.PERSISTENT_MESSAGE_HISTORIES", {})
    @patch("cai.repl.commands.load.load_history_from_jsonl")
    def test_handle_special_characters_in_agent_name(
        self, mock_load_jsonl, mock_agent_manager, mock_get_agent, mock_input, load_command, sample_jsonl_messages
    ):
        """Test handling agent names with special characters."""
        mock_input.return_value = "n"  # Don't create memory
        mock_load_jsonl.return_value = sample_jsonl_messages
        
        # Mock AGENT_MANAGER methods
        mock_agent_manager.get_agent_by_id.return_value = None
        mock_agent_manager._message_history = {}
        mock_agent_manager._agent_registry = {}
        mock_agent_manager._id_counter = 0

        # Test with numbered agent
        result = load_command.handle(["Bug", "Bounty", "Hunter", "#1"])
        assert result is True

    @patch("cai.repl.commands.load.console.input")
    @patch("cai.agents.get_agent_by_name")
    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    @patch("cai.sdk.agents.models.openai_chatcompletions.ACTIVE_MODEL_INSTANCES", {})
    @patch("cai.sdk.agents.models.openai_chatcompletions.PERSISTENT_MESSAGE_HISTORIES", {})
    @patch("cai.repl.commands.load.load_history_from_jsonl")
    def test_file_path_detection(
        self, mock_load_jsonl, mock_agent_manager, mock_get_agent, mock_input, load_command, sample_jsonl_messages
    ):
        """Test proper file path detection in arguments."""
        mock_input.return_value = "n"  # Don't create memory
        mock_load_jsonl.return_value = sample_jsonl_messages
        
        # Mock AGENT_MANAGER methods
        mock_agent_manager.get_active_agents.return_value = {}
        mock_agent_manager.get_registered_agents.return_value = {}
        mock_agent_manager._message_history = {}
        mock_agent_manager._agent_registry = {}
        mock_agent_manager._id_counter = 0
        mock_agent_manager.set_active_agent = MagicMock()

        # Test with relative path
        result = load_command.handle(["./logs/session.jsonl"])
        assert result is True
        mock_load_jsonl.assert_called_with("./logs/session.jsonl")

        # Test with absolute path
        result = load_command.handle(["/absolute/path/session.jsonl"])
        assert result is True
        mock_load_jsonl.assert_called_with("/absolute/path/session.jsonl")
    
    @patch("cai.repl.commands.load.console.input")
    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    @patch("cai.sdk.agents.models.openai_chatcompletions.ACTIVE_MODEL_INSTANCES", {})
    @patch("cai.sdk.agents.models.openai_chatcompletions.PERSISTENT_MESSAGE_HISTORIES", {})
    @patch("cai.agents.get_available_agents")
    @patch("cai.repl.commands.load.load_history_from_jsonl")
    def test_handle_parallel_subcommand(
        self, mock_load_jsonl, mock_get_available, mock_agent_manager, mock_input, load_command
    ):
        """Test 'parallel' subcommand loads messages matching configured agents."""
        from cai.repl.commands.parallel import ParallelConfig, PARALLEL_CONFIGS
        
        # Mock available agents
        mock_agent1 = MagicMock()
        mock_agent1.name = "Red Team Agent"
        mock_agent2 = MagicMock()
        mock_agent2.name = "Blue Team Agent"
        mock_get_available.return_value = {
            "red_teamer": mock_agent1,
            "blueteam_agent": mock_agent2
        }
        
        # Mock messages with agent names
        messages_with_agents = [
            {"role": "user", "content": "Test 1"},
            {"role": "assistant", "content": "Response 1", "sender": "Red Team Agent"},
            {"role": "user", "content": "Test 2"},
            {"role": "assistant", "content": "Response 2", "sender": "Blue Team Agent"},
        ]
        mock_load_jsonl.return_value = messages_with_agents
        
        # Save original configs and clear
        original_configs = PARALLEL_CONFIGS[:]
        PARALLEL_CONFIGS.clear()
        
        try:
            # Create parallel configs
            config1 = ParallelConfig("red_teamer")
            config1.id = "P1"
            PARALLEL_CONFIGS.append(config1)
            
            config2 = ParallelConfig("blueteam_agent")
            config2.id = "P2"
            PARALLEL_CONFIGS.append(config2)
            
            # Mock AGENT_MANAGER methods
            mock_agent_manager.get_message_history.return_value = []
            mock_agent_manager._message_history = {}
            
            result = load_command.handle(["parallel"])
            assert result is True
            
            # Should load from default file
            mock_load_jsonl.assert_called_with("logs/last")
        finally:
            # Restore original configs
            PARALLEL_CONFIGS.clear()
            PARALLEL_CONFIGS.extend(original_configs)
    
    @patch("cai.repl.commands.load.console.input")
    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    @patch("cai.sdk.agents.models.openai_chatcompletions.ACTIVE_MODEL_INSTANCES", {})
    @patch("cai.sdk.agents.models.openai_chatcompletions.PERSISTENT_MESSAGE_HISTORIES", {})
    @patch("cai.agents.get_available_agents")
    @patch("cai.repl.commands.load.load_history_from_jsonl")
    def test_handle_parallel_no_agent_names(
        self, mock_load_jsonl, mock_get_available, mock_agent_manager, mock_input, load_command
    ):
        """Test 'parallel' subcommand fails when JSONL has no agent names."""
        from cai.repl.commands.parallel import ParallelConfig, PARALLEL_CONFIGS
        
        # Mock messages without agent names
        messages_no_agents = [
            {"role": "user", "content": "Test 1"},
            {"role": "assistant", "content": "Response 1"},
        ]
        mock_load_jsonl.return_value = messages_no_agents
        
        # Save original configs and clear
        original_configs = PARALLEL_CONFIGS[:]
        PARALLEL_CONFIGS.clear()
        
        try:
            # Create parallel config
            config = ParallelConfig("red_teamer")
            PARALLEL_CONFIGS.append(config)
            
            # Mock agent manager
            mock_agent_manager.get_message_history.return_value = []
            mock_agent_manager._message_history = {}
            
            result = load_command.handle(["parallel", "logs/session.jsonl"])
            assert result is False  # Should fail when no agents found
            
            mock_load_jsonl.assert_called_with("logs/session.jsonl")
        finally:
            # Restore original configs
            PARALLEL_CONFIGS.clear()
            PARALLEL_CONFIGS.extend(original_configs)
    
    @patch("cai.repl.commands.load.load_history_from_jsonl")
    def test_handle_parallel_with_file(
        self, mock_load_jsonl, load_command
    ):
        """Test 'parallel' subcommand with specific file."""
        from cai.repl.commands.parallel import PARALLEL_CONFIGS
        
        # Save original configs and clear
        original_configs = PARALLEL_CONFIGS[:]
        PARALLEL_CONFIGS.clear()
        
        try:
            # No parallel configs - should fall back to default behavior
            mock_load_jsonl.return_value = []
            
            result = load_command.handle(["parallel", "custom.jsonl"])
            # With no parallel configs, it should use default behavior
            assert result is True
            mock_load_jsonl.assert_called_with("custom.jsonl")
        finally:
            # Restore original configs
            PARALLEL_CONFIGS.clear()
            PARALLEL_CONFIGS.extend(original_configs)


@pytest.mark.integration
class TestLoadCommandIntegration:
    """Integration tests for load command functionality."""

    @pytest.fixture(autouse=True)
    def setup_integration(self):
        """Setup for integration tests."""
        yield

    @patch("cai.repl.commands.load.console.input")
    @patch("cai.agents.get_agent_by_name")
    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    @patch("cai.sdk.agents.models.openai_chatcompletions.ACTIVE_MODEL_INSTANCES", {})
    @patch("cai.sdk.agents.models.openai_chatcompletions.PERSISTENT_MESSAGE_HISTORIES", {})
    @patch("cai.repl.commands.load.load_history_from_jsonl")
    @patch("cai.repl.commands.load.get_all_agent_histories")
    def test_full_load_workflow(
        self, mock_get_all, mock_load_jsonl, mock_agent_manager, mock_get_agent, mock_input
    ):
        """Test a complete load workflow."""
        mock_input.return_value = "n"  # Don't create memory
        # Start with empty histories
        mock_get_all.return_value = {}
        
        # Load messages for first agent
        messages1 = [
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": "Response 1"},
        ]
        mock_load_jsonl.return_value = messages1
        
        # Mock AGENT_MANAGER methods
        mock_agent_manager.get_agent_by_id.return_value = None
        mock_agent_manager._message_history = {}
        mock_agent_manager._agent_registry = {}
        
        cmd = LoadCommand()
        
        # Load to first agent
        result = cmd.handle(["red_teamer", "session1.jsonl"])
        assert result is True
        
        # Load messages for second agent
        messages2 = [
            {"role": "user", "content": "Message 2"},
            {"role": "assistant", "content": "Response 2"},
        ]
        mock_load_jsonl.return_value = messages2
        
        result = cmd.handle(["Bug", "Bounty", "Hunter", "session2.jsonl"])
        assert result is True
        
        # Check all agents
        mock_get_all.return_value = {
            "red_teamer": messages1,
            "Bug Bounty Hunter": messages2,
        }
        
        result = cmd.handle(["all"])
        assert result is True
    
    @patch("cai.repl.commands.load.console.input")
    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    @patch("cai.agents.get_available_agents")
    @patch("cai.repl.commands.load.load_history_from_jsonl")
    def test_load_by_agent_id(self, mock_load_jsonl, mock_get_available, mock_agent_manager, mock_input):
        """Test loading into agent by ID."""
        from cai.repl.commands.parallel import ParallelConfig, PARALLEL_CONFIGS
        
        # Mock agent
        mock_agent = MagicMock()
        mock_agent.name = "Red Team Agent"
        mock_get_available.return_value = {"red_teamer": mock_agent}
        
        # Save original configs and clear
        original_configs = PARALLEL_CONFIGS[:]
        PARALLEL_CONFIGS.clear()
        
        try:
            # Create parallel config with ID
            config = ParallelConfig("red_teamer")
            config.id = "P1"
            PARALLEL_CONFIGS.append(config)
            
            # Setup mocks
            mock_load_jsonl.return_value = [{"role": "user", "content": "Test"}]
            
            # Mock AGENT_MANAGER methods
            mock_agent_manager.get_agent_by_id.return_value = "Red Team Agent"
            mock_agent_manager.get_message_history.return_value = []
            mock_agent_manager.get_id_by_name.return_value = "P1"
            mock_agent_manager._message_history = {}
            mock_agent_manager._agent_registry = {}
            
            cmd = LoadCommand()
            result = cmd.handle(["P1", "session.jsonl"])
            assert result is True
            
            # Should load to correct agent
            mock_load_jsonl.assert_called_with("session.jsonl")
            # Should have gotten message history for resolved agent
            mock_agent_manager.get_message_history.assert_called_with("Red Team Agent")
        finally:
            # Restore original configs
            PARALLEL_CONFIGS.clear()
            PARALLEL_CONFIGS.extend(original_configs)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])