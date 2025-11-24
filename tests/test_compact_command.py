"""
Tests for the enhanced compact command with AI summarization.
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock
from cai.repl.commands.compact import CompactCommand
from cai.sdk.agents.models.openai_chatcompletions import get_agent_message_history, get_all_agent_histories

class TestCompactCommand:
    """Test the CompactCommand class."""
    
    @pytest.fixture
    def compact_command(self):
        """Create a CompactCommand instance."""
        cmd = CompactCommand()
        return cmd
    
    def test_command_initialization(self, compact_command):
        """Test command is properly initialized."""
        assert compact_command.name == "/compact"
        assert "/cmp" in compact_command.aliases
        assert len(compact_command.subcommands) >= 3  # Should have model, prompt, status subcommands
        assert compact_command.compact_model is None  # Default to current model
    
    def test_handle_model(self, compact_command):
        """Test setting the compact model."""
        # Set a specific model
        result = compact_command.handle_model(["gpt-3.5-turbo"])
        assert result is True
        assert compact_command.compact_model == "gpt-3.5-turbo"
        
        # Set to default
        result = compact_command.handle_model(["default"])
        assert result is True
        assert compact_command.compact_model is None
        
        # No args shows current model
        result = compact_command.handle_model([])
        assert result is True
    
    def test_handle_prompt(self, compact_command):
        """Test setting the custom prompt."""
        # Set a custom prompt
        result = compact_command.handle_prompt(["Summarize the key CTF findings"])
        assert result is True
        assert compact_command.custom_prompt == "Summarize the key CTF findings"
        
        # Clear prompt by setting empty
        result = compact_command.handle_prompt([""])
        assert result is True
        assert compact_command.custom_prompt == ""
    
    def test_handle_status(self, compact_command):
        """Test status display."""
        # Set some custom settings
        compact_command.compact_model = "gpt-3.5-turbo"
        compact_command.custom_prompt = "Test prompt"
        
        result = compact_command.handle_status([])
        assert result is True
    
    @patch.object(CompactCommand, '_perform_compaction')
    def test_command_with_args(self, mock_perform, compact_command):
        """Test compact command with model and prompt arguments."""
        # Mock the actual compaction to avoid dependencies
        mock_perform.return_value = True
        
        # Test with model override
        result = compact_command.handle(["--model", "gpt-4"])
        assert result is True
        mock_perform.assert_called_with("gpt-4", None)
        
        # Test with prompt override
        result = compact_command.handle(["--prompt", "Custom prompt"])
        assert result is True
        mock_perform.assert_called_with(None, "Custom prompt")
    

