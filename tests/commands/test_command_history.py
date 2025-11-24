#!/usr/bin/env python3
"""
Test suite for the history command functionality.
Tests all handle methods and input possibilities for the history command.
Includes multi-agent support and persistent message history features.
"""

import json
import os
import sys
from unittest.mock import patch, MagicMock, mock_open

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from cai.repl.commands.base import Command
from cai.repl.commands.history import HistoryCommand


class TestHistoryCommand:
    """Test cases for HistoryCommand."""

    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """Setup and cleanup for each test."""
        # Set up test environment
        os.environ["CAI_TELEMETRY"] = "false"
        os.environ["CAI_TRACING"] = "false"

        yield

    @pytest.fixture
    def history_command(self):
        """Create a HistoryCommand instance for testing."""
        return HistoryCommand()

    @pytest.fixture
    def sample_message_history(self):
        """Create sample message history for testing."""
        return [
            {"role": "user", "content": "Hello, can you help me with Python?"},
            {
                "role": "assistant",
                "content": "Of course! I'd be happy to help you with Python. What specific topic or problem would you like assistance with?",
            },
            {"role": "user", "content": "How do I create a list?"},
            {
                "role": "assistant",
                "content": "I'll help you create a tool to demonstrate list creation.",
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "create_example",
                            "arguments": '{"language": "python", "topic": "lists"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_123",
                "content": "# Creating lists in Python\nmy_list = [1, 2, 3]\nprint(my_list)",
            },
            {
                "role": "assistant",
                "content": "Here's how you create a list in Python: you use square brackets and separate items with commas.",
            },
        ]

    @pytest.fixture
    def multi_agent_histories(self):
        """Create message histories for multiple agents."""
        return {
            "red_teamer": [
                {"role": "user", "content": "Scan the target"},
                {"role": "assistant", "content": "I'll scan the target system."},
                {"role": "tool", "tool_call_id": "call_1", "content": "Scan results: open ports 22, 80, 443"},
            ],
            "Bug Bounty Hunter": [
                {"role": "user", "content": "Find vulnerabilities"},
                {"role": "assistant", "content": "Searching for vulnerabilities..."},
            ],
            "Bug Bounty Hunter #1": [
                {"role": "user", "content": "Test parallel instance 1"},
                {"role": "assistant", "content": "Instance 1 response"},
            ],
            "Bug Bounty Hunter #2": [
                {"role": "user", "content": "Test parallel instance 2"},
                {"role": "assistant", "content": "Instance 2 response"},
            ],
            "Assistant": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi! How can I help?"},
            ],
        }

    @pytest.fixture
    def complex_message_history(self):
        """Create complex message history with various message types."""
        return [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Execute a command for me"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_cmd_1",
                        "type": "function",
                        "function": {
                            "name": "generic_linux_command",
                            "arguments": '{"command": "ls", "args": "-la"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_cmd_1",
                "content": "total 8\ndrwxr-xr-x 2 user user 4096 Jan 1 12:00 .\ndrwxr-xr-x 3 user user 4096 Jan 1 12:00 ..",
            },
            {
                "role": "assistant",
                "content": "The directory listing shows two entries: the current directory (.) and parent directory (..).",
            },
            {"role": "user", "content": "Now run multiple commands"},
            {
                "role": "assistant",
                "content": "I'll run multiple commands for you.",
                "tool_calls": [
                    {
                        "id": "call_cmd_2",
                        "type": "function",
                        "function": {
                            "name": "generic_linux_command",
                            "arguments": '{"command": "pwd"}',
                        },
                    },
                    {
                        "id": "call_cmd_3",
                        "type": "function",
                        "function": {
                            "name": "generic_linux_command",
                            "arguments": '{"command": "whoami"}',
                        },
                    },
                ],
            },
            {"role": "tool", "tool_call_id": "call_cmd_2", "content": "/home/user"},
            {"role": "tool", "tool_call_id": "call_cmd_3", "content": "user"},
        ]

    def test_command_initialization(self, history_command):
        """Test that HistoryCommand initializes correctly."""
        assert history_command.name == "/history"
        assert (
            history_command.description
            == "Display conversation history (optionally filtered by agent name)"
        )
        assert history_command.aliases == ["/his"]

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_all_agent_histories")
    def test_handle_no_args_with_history(
        self, mock_get_all_histories, history_command, sample_message_history
    ):
        """Test handling with no arguments when history exists."""
        mock_get_all_histories.return_value = {"test_agent": sample_message_history}

        result = history_command.handle([])
        assert result is True

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_all_agent_histories")
    def test_handle_no_args_empty_history(self, mock_get_all_histories, history_command):
        """Test handling with no arguments when history is empty."""
        mock_get_all_histories.return_value = {}

        result = history_command.handle([])
        assert result is True

    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    def test_handle_with_agent_name(
        self, mock_agent_manager, history_command, sample_message_history
    ):
        """Test handling with specific agent name."""
        # Mock AGENT_MANAGER methods
        mock_agent_manager.get_all_histories.return_value = {"test_agent": sample_message_history}
        mock_agent_manager.get_message_history.return_value = sample_message_history
        mock_agent_manager.get_agent_by_id.return_value = None
        mock_agent_manager.get_id_by_name.return_value = "A1"

        result = history_command.handle(["test_agent"])
        assert result is True
        # The implementation finds the agent in all_histories and uses that directly
        # It may or may not call get_message_history depending on whether history is already found
        mock_agent_manager.get_all_histories.assert_called_once()

    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    def test_handle_with_agent_name_with_spaces(
        self, mock_agent_manager, history_command, sample_message_history
    ):
        """Test handling with agent name containing spaces."""
        # Mock AGENT_MANAGER methods
        mock_agent_manager.get_all_histories.return_value = {"Bug Bounty Hunter": sample_message_history}
        mock_agent_manager.get_message_history.return_value = sample_message_history
        mock_agent_manager.get_agent_by_id.return_value = None
        mock_agent_manager.get_id_by_name.return_value = "A1"

        # Test with multi-word agent name
        result = history_command.handle(["Bug", "Bounty", "Hunter"])
        assert result is True
        # The implementation finds the agent in all_histories, so get_all_histories is called
        mock_agent_manager.get_all_histories.assert_called()

    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    def test_handle_with_nonexistent_agent(
        self, mock_agent_manager, history_command
    ):
        """Test handling when agent doesn't have history."""
        # Mock AGENT_MANAGER methods
        mock_agent_manager.get_all_histories.return_value = {}
        mock_agent_manager.get_message_history.return_value = None
        mock_agent_manager.get_agent_by_id.return_value = None

        result = history_command.handle(["nonexistent_agent"])
        assert result is True

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_all_agent_histories")
    def test_handle_multiple_agents_history(
        self, mock_get_all_histories, history_command, sample_message_history, complex_message_history
    ):
        """Test handling history from multiple agents."""
        mock_get_all_histories.return_value = {
            "agent_1": sample_message_history,
            "agent_2": complex_message_history,
            "Bug Bounty Hunter #1": sample_message_history,
            "Red Team Agent": complex_message_history
        }

        result = history_command.handle([])
        assert result is True


    def test_get_subcommands(self, history_command):
        """Test that the history command returns the correct subcommands."""
        subcommands = history_command.get_subcommands()
        # Check for any expected subcommands - update based on implementation
        assert isinstance(subcommands, list)

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_all_agent_histories")
    def test_handle_complex_history(
        self, mock_get_all_histories, history_command, complex_message_history
    ):
        """Test handling complex message history with various message types."""
        mock_get_all_histories.return_value = {"test_agent": complex_message_history}

        result = history_command.handle([])
        assert result is True

    def test_format_message_content_simple_text(self, history_command):
        """Test formatting simple text content."""
        content = "This is a simple message"
        tool_calls = None

        result = history_command._format_message_content(content, tool_calls)
        assert result == content

    def test_format_message_content_long_text(self, history_command):
        """Test formatting long text content (should be truncated)."""
        content = (
            "This is a very long message that should be truncated because it exceeds the 300 character limit that is set in the formatting function for display purposes. "
            * 3
        )
        tool_calls = None

        result = history_command._format_message_content(content, tool_calls)
        assert len(result) <= 300
        assert result.endswith("...")

    def test_format_message_content_empty(self, history_command):
        """Test formatting empty content."""
        content = ""
        tool_calls = None

        result = history_command._format_message_content(content, tool_calls)
        assert "Empty message" in result

    def test_format_message_content_none(self, history_command):
        """Test formatting None content."""
        content = None
        tool_calls = None

        result = history_command._format_message_content(content, tool_calls)
        assert "Empty message" in result

    def test_format_message_content_with_tool_calls(self, history_command):
        """Test formatting content with tool calls."""
        content = "I'll help you with that"
        tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "test_function",
                    "arguments": '{"param1": "value1", "param2": "value2"}',
                },
            }
        ]

        result = history_command._format_message_content(content, tool_calls)
        assert "Function:" in result
        assert "test_function" in result
        assert "Args:" in result

    def test_format_message_content_with_multiple_tool_calls(self, history_command):
        """Test formatting content with multiple tool calls."""
        content = "I'll run multiple commands"
        tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "function_one", "arguments": '{"arg": "value1"}'},
            },
            {
                "id": "call_2",
                "type": "function",
                "function": {"name": "function_two", "arguments": '{"arg": "value2"}'},
            },
        ]

        result = history_command._format_message_content(content, tool_calls)
        assert "function_one" in result
        assert "function_two" in result
        assert result.count("Function:") == 2

    def test_format_message_content_with_invalid_json_args(self, history_command):
        """Test formatting content with invalid JSON in tool call arguments."""
        content = "Testing invalid JSON"
        tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {"name": "test_function", "arguments": "invalid json string"},
            }
        ]

        result = history_command._format_message_content(content, tool_calls)
        assert "Function:" in result
        assert "test_function" in result
        assert "invalid json string" in result

    def test_format_message_content_with_long_tool_args(self, history_command):
        """Test formatting content with very long tool call arguments."""
        content = "Testing long arguments"
        long_args = json.dumps(
            {
                "very_long_parameter": "This is a very long parameter value that should be truncated when displayed in the history because it exceeds the character limit"
                * 3
            }
        )
        tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {"name": "test_function", "arguments": long_args},
            }
        ]

        result = history_command._format_message_content(content, tool_calls)
        assert "Function:" in result
        assert "test_function" in result
        assert "..." in result  # Should be truncated

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_all_agent_histories")
    def test_handle_import_error(self, mock_get_all_histories, history_command):
        """Test handling when import fails."""
        # Create a new command instance and monkey patch its handle_control_panel method
        # to simulate an import error
        test_command = HistoryCommand()

        def mock_handle_control_panel_with_import_error():
            try:
                # Simulate the import failing
                raise ImportError("Mock import error")
            except ImportError:
                return False

        # Replace the method to simulate import failure
        test_command.handle_control_panel = mock_handle_control_panel_with_import_error

        result = test_command.handle([])
        assert result is False

    def test_command_base_functionality(self, history_command):
        """Test that the command inherits from base Command properly."""
        assert isinstance(history_command, Command)
        assert history_command.name == "/history"
        assert "/his" in history_command.aliases

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_all_agent_histories")
    def test_handle_with_corrupted_message(self, mock_get_all_histories, history_command):
        """Test handling when message history contains corrupted data."""
        # Create message history with missing or corrupted fields
        corrupted_history = [
            {"role": "user", "content": "Normal message"},
            {
                # Missing role field
                "content": "Message without role"
            },
            {
                "role": "assistant",
                # Missing content field
                "tool_calls": [{"id": "call_1", "function": {"name": "test"}}],
            },
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "content": None,  # None content
            },
        ]

        mock_get_all_histories.return_value = {"test_agent": corrupted_history}

        # Should handle gracefully without crashing
        result = history_command.handle([])
        assert result is True

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_all_agent_histories")
    def test_handle_with_messages_parameter(
        self, mock_get_all_histories, history_command, sample_message_history
    ):
        """Test handle method with explicit messages parameter."""
        mock_get_all_histories.return_value = {"test_agent": sample_message_history}

        # The handle method doesn't accept messages parameter anymore
        result = history_command.handle([])
        assert result is True

    # Multi-agent tests
    @patch("cai.sdk.agents.models.openai_chatcompletions.get_all_agent_histories")
    def test_handle_control_panel_multi_agent(
        self, mock_get_all_histories, history_command, multi_agent_histories
    ):
        """Test control panel display with multiple agents."""
        mock_get_all_histories.return_value = multi_agent_histories

        result = history_command.handle([])
        assert result is True

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_all_agent_histories")
    def test_handle_all_subcommand(
        self, mock_get_all_histories, history_command, multi_agent_histories
    ):
        """Test 'all' subcommand showing all agent histories."""
        mock_get_all_histories.return_value = multi_agent_histories

        result = history_command.handle(["all"])
        assert result is True

    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    def test_handle_specific_agent(
        self, mock_agent_manager, history_command, multi_agent_histories
    ):
        """Test showing history for a specific agent."""
        # Mock AGENT_MANAGER methods
        mock_agent_manager.get_all_histories.return_value = multi_agent_histories
        mock_agent_manager.get_message_history.return_value = multi_agent_histories["red_teamer"]
        mock_agent_manager.get_agent_by_id.return_value = None
        mock_agent_manager.get_id_by_name.return_value = "A1"

        result = history_command.handle(["red_teamer"])
        assert result is True
        # The implementation finds the agent in all_histories
        mock_agent_manager.get_all_histories.assert_called()

    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    def test_handle_agent_with_spaces(
        self, mock_agent_manager, history_command, multi_agent_histories
    ):
        """Test showing history for agent with spaces in name."""
        # Mock AGENT_MANAGER methods
        mock_agent_manager.get_all_histories.return_value = multi_agent_histories
        mock_agent_manager.get_message_history.return_value = multi_agent_histories["Bug Bounty Hunter"]
        mock_agent_manager.get_agent_by_id.return_value = None
        mock_agent_manager.get_id_by_name.return_value = "A1"

        # Test direct agent name
        result = history_command.handle(["Bug", "Bounty", "Hunter"])
        assert result is True
        # The implementation finds the agent in all_histories
        mock_agent_manager.get_all_histories.assert_called()

    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    def test_handle_agent_subcommand(
        self, mock_agent_manager, history_command, multi_agent_histories
    ):
        """Test 'agent' subcommand with agent name."""
        # Mock AGENT_MANAGER methods
        mock_agent_manager.get_all_histories.return_value = multi_agent_histories
        mock_agent_manager.get_message_history.return_value = multi_agent_histories["red_teamer"]
        mock_agent_manager.get_agent_by_id.return_value = None
        mock_agent_manager.get_id_by_name.return_value = "A1"

        result = history_command.handle(["agent", "red_teamer"])
        assert result is True
        # The implementation finds the agent in all_histories
        mock_agent_manager.get_all_histories.assert_called()

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_all_agent_histories")
    def test_handle_search_subcommand(
        self, mock_get_all_histories, history_command, multi_agent_histories
    ):
        """Test 'search' subcommand across all agents."""
        mock_get_all_histories.return_value = multi_agent_histories

        result = history_command.handle(["search", "vulnerabilities"])
        assert result is True

    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    def test_handle_index_subcommand(
        self, mock_agent_manager, history_command, multi_agent_histories
    ):
        """Test 'index' subcommand to show specific message."""
        # Mock AGENT_MANAGER methods
        mock_agent_manager.get_message_history.return_value = multi_agent_histories["red_teamer"]
        mock_agent_manager.get_agent_by_id.return_value = None

        result = history_command.handle(["index", "red_teamer", "2"])
        assert result is True
        mock_agent_manager.get_message_history.assert_called_with("red_teamer")

    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    def test_handle_numbered_agents(
        self, mock_agent_manager, history_command, multi_agent_histories
    ):
        """Test handling numbered agent instances (parallel execution)."""
        # Mock AGENT_MANAGER methods
        mock_agent_manager.get_all_histories.return_value = multi_agent_histories
        mock_agent_manager.get_message_history.return_value = multi_agent_histories["Bug Bounty Hunter #1"]
        mock_agent_manager.get_agent_by_id.return_value = None
        mock_agent_manager.get_id_by_name.return_value = "A1"

        result = history_command.handle(["Bug", "Bounty", "Hunter", "#1"])
        assert result is True
        # The implementation finds the agent in all_histories
        mock_agent_manager.get_all_histories.assert_called()

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_all_agent_histories")
    def test_handle_agent_name_extraction_from_messages(
        self, mock_get_all_histories, history_command
    ):
        """Test that agent names are properly extracted and displayed."""
        # Create history with agent names in assistant messages
        history_with_agent_names = [
            {"role": "user", "content": "Hello"},
            {
                "role": "assistant",
                "content": "[Red Team Agent] I can help you with security testing.",
            },
            {"role": "user", "content": "Run a scan"},
            {
                "role": "assistant",
                "content": "[Bug Bounty Hunter] Let me scan for vulnerabilities.",
                "tool_calls": [
                    {
                        "id": "call_scan",
                        "type": "function",
                        "function": {
                            "name": "nmap",
                            "arguments": '{"target": "example.com"}',
                        },
                    }
                ],
            },
        ]

        mock_get_all_histories.return_value = {
            "Multi-Agent Session": history_with_agent_names
        }

        result = history_command.handle([])
        assert result is True

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_all_agent_histories")
    def test_handle_with_very_long_agent_names(
        self, mock_get_all_histories, history_command, sample_message_history
    ):
        """Test handling agents with very long names."""
        long_agent_name = "This is a very long agent name that might cause display issues"
        mock_get_all_histories.return_value = {
            long_agent_name: sample_message_history
        }

        result = history_command.handle([])
        assert result is True

    def test_format_message_content_with_agent_prefix(
        self, history_command
    ):
        """Test formatting content that includes agent name prefixes."""
        content = "[Bug Bounty Hunter] I found a vulnerability in the login form."
        tool_calls = None

        result = history_command._format_message_content(content, tool_calls)
        assert "[Bug Bounty Hunter]" in result
        assert "vulnerability" in result

    # Note: The 'save' subcommand doesn't exist in the current implementation
    # These tests are commented out as placeholders for when/if this feature is added
    
    # @patch("builtins.open", new_callable=mock_open)
    # @patch("os.makedirs")
    # def test_handle_save_subcommand(
    #     self, mock_makedirs, mock_file, history_command, sample_message_history
    # ):
    #     """Test handling the 'save' subcommand to export history."""
    #     # This would test saving history to a file
    #     pass


@pytest.mark.integration
class TestHistoryCommandIntegration:
    """Integration tests for history command functionality."""

    @pytest.fixture(autouse=True)
    def setup_integration(self):
        """Setup for integration tests."""
        yield

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_all_agent_histories")
    def test_full_conversation_history_workflow(self, mock_get_all_histories):
        """Test a complete conversation workflow and history display."""
        # Simulate a conversation building up over time
        conversation_steps = [
            # Step 1: Initial user message
            [{"role": "user", "content": "Hello"}],
            # Step 2: Assistant response
            [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi! How can I help you?"},
            ],
            # Step 3: User asks for help
            [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi! How can I help you?"},
                {"role": "user", "content": "Can you run a command?"},
            ],
            # Step 4: Assistant with tool call
            [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi! How can I help you?"},
                {"role": "user", "content": "Can you run a command?"},
                {
                    "role": "assistant",
                    "content": "I'll run that command for you.",
                    "tool_calls": [
                        {
                            "id": "call_cmd",
                            "type": "function",
                            "function": {
                                "name": "generic_linux_command",
                                "arguments": '{"command": "ls"}',
                            },
                        }
                    ],
                },
            ],
            # Step 5: Tool response
            [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi! How can I help you?"},
                {"role": "user", "content": "Can you run a command?"},
                {
                    "role": "assistant",
                    "content": "I'll run that command for you.",
                    "tool_calls": [
                        {
                            "id": "call_cmd",
                            "type": "function",
                            "function": {
                                "name": "generic_linux_command",
                                "arguments": '{"command": "ls"}',
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_cmd",
                    "content": "file1.txt\nfile2.txt\nfolder1/",
                },
            ],
        ]

        cmd = HistoryCommand()

        # Test history at each step
        for i, step_history in enumerate(conversation_steps):
            mock_get_all_histories.return_value = {"test_agent": step_history}

            result = cmd.handle([])
            assert result is True, f"Failed at conversation step {i + 1}"

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_all_agent_histories")
    def test_edge_case_message_combinations(self, mock_get_all_histories):
        """Test various edge case message combinations."""
        edge_cases = [
            # Empty history
            [],
            # Only system message
            [{"role": "system", "content": "You are a helpful assistant."}],
            # Only user messages
            [
                {"role": "user", "content": "First message"},
                {"role": "user", "content": "Second message"},
            ],
            # Tool call without response
            [
                {"role": "user", "content": "Run command"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_incomplete",
                            "type": "function",
                            "function": {"name": "test_command", "arguments": "{}"},
                        }
                    ],
                },
            ],
            # Tool response without call
            [
                {"role": "user", "content": "Test"},
                {"role": "tool", "tool_call_id": "orphan_call", "content": "Result"},
            ],
        ]

        cmd = HistoryCommand()

        for i, case_history in enumerate(edge_cases):
            mock_get_all_histories.return_value = {"test_agent": case_history}

            result = cmd.handle([])
            assert result is True, f"Failed at edge case {i + 1}"

    @patch("cai.sdk.agents.models.openai_chatcompletions.get_all_agent_histories")
    def test_multi_agent_conversation_flow(self, mock_get_all_histories):
        """Test a multi-agent conversation flow."""
        multi_agent_history = {
            "Red Team Agent": [
                {"role": "user", "content": "Scan the target"},
                {"role": "assistant", "content": "I'll scan the target for vulnerabilities."},
            ],
            "Bug Bounty Hunter #1": [
                {"role": "user", "content": "Check web application"},
                {"role": "assistant", "content": "I'll analyze the web application security."},
            ],
            "Blue Team Agent": [
                {"role": "user", "content": "Monitor for attacks"},
                {"role": "assistant", "content": "I'll set up monitoring for potential attacks."},
            ]
        }

        mock_get_all_histories.return_value = multi_agent_history

        cmd = HistoryCommand()
        result = cmd.handle([])
        assert result is True

    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    @patch("cai.agents.get_available_agents")
    def test_handle_agent_with_id(self, mock_get_available_agents, mock_agent_manager):
        """Test showing history for agent by ID."""
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
            
            # Mock history
            test_history = [
                {"role": "user", "content": "Test message"},
                {"role": "assistant", "content": "Test response"}
            ]
            # Mock AGENT_MANAGER methods
            mock_agent_manager.get_agent_by_id.return_value = "Red Team Agent"
            mock_agent_manager.get_message_history.return_value = test_history
            mock_agent_manager.get_id_by_name.return_value = "P1"
            
            cmd = HistoryCommand()
            result = cmd.handle(["P1"])
            assert result is True
            mock_agent_manager.get_message_history.assert_called_with("Red Team Agent")
        finally:
            # Restore original configs
            PARALLEL_CONFIGS.clear()
            PARALLEL_CONFIGS.extend(original_configs)
    
    @patch("cai.sdk.agents.models.openai_chatcompletions.get_all_agent_histories")
    @patch("cai.repl.commands.parallel.PARALLEL_CONFIGS")
    @patch("cai.agents.get_available_agents")
    def test_handle_control_panel_with_configured_agents(
        self, mock_get_available_agents, mock_parallel_configs, mock_get_all_histories
    ):
        """Test control panel shows configured agents even without history."""
        from cai.repl.commands.parallel import ParallelConfig
        
        # Mock agents
        mock_agent1 = MagicMock()
        mock_agent1.name = "Red Team Agent"
        mock_agent2 = MagicMock()
        mock_agent2.name = "Bug Bounty Hunter"
        
        mock_get_available_agents.return_value = {
            "red_teamer": mock_agent1,
            "bug_bounter": mock_agent2
        }
        
        # Create parallel configs
        config1 = ParallelConfig("red_teamer")
        config1.id = "P1"
        config2 = ParallelConfig("bug_bounter")
        config2.id = "P2"
        
        mock_parallel_configs.clear()
        mock_parallel_configs.append(config1)
        mock_parallel_configs.append(config2)
        
        # Only one agent has history
        mock_get_all_histories.return_value = {
            "Red Team Agent": [
                {"role": "user", "content": "Test"},
                {"role": "assistant", "content": "Response"}
            ]
        }
        
        cmd = HistoryCommand()
        result = cmd.handle([])
        assert result is True
        # Should still succeed and show both agents (one with history, one configured)
    
    @patch("cai.sdk.agents.simple_agent_manager.AGENT_MANAGER")
    @patch("cai.agents.get_available_agents")
    def test_handle_numbered_agent_with_id(
        self, mock_get_available_agents, mock_agent_manager
    ):
        """Test handling numbered agents (duplicates) with IDs."""
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
            
            # Mock history for second instance
            test_history = [
                {"role": "user", "content": "Instance 2 test"},
                {"role": "assistant", "content": "Instance 2 response"}
            ]
            
            # Mock AGENT_MANAGER methods
            mock_agent_manager.get_agent_by_id.return_value = "Bug Bounty Hunter"
            mock_agent_manager.get_message_history.return_value = test_history
            mock_agent_manager.get_id_by_name.return_value = "P2"
            mock_agent_manager.get_all_histories.return_value = {
                "Bug Bounty Hunter #1 [P1]": [],
                "Bug Bounty Hunter #2 [P2]": test_history
            }
            mock_agent_manager.get_registered_agents.return_value = ["Bug Bounty Hunter"]
            
            cmd = HistoryCommand()
            result = cmd.handle(["P2"])
            assert result is True
            # Should call with base agent name, not numbered instance
            mock_agent_manager.get_message_history.assert_called_with("Bug Bounty Hunter")
        finally:
            # Restore original configs
            PARALLEL_CONFIGS.clear()
            PARALLEL_CONFIGS.extend(original_configs)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])