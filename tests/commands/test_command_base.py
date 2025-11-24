#!/usr/bin/env python3
"""
Test suite for the base command system functionality.
Tests the Command class, command registry, and base command handling.
"""

import os
import sys
import pytest
from unittest.mock import patch, Mock, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 
                                '..', '..', 'src'))

from cai.repl.commands.base import (
    Command, COMMANDS, COMMAND_ALIASES, 
    register_command, get_command, handle_command
)


class TestCommand:
    """Test cases for the base Command class."""
    
    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """Setup and cleanup for each test."""
        # Store original command registry
        self.original_commands = COMMANDS.copy()
        self.original_aliases = COMMAND_ALIASES.copy()
        
        yield
        
        # Restore original command registry
        COMMANDS.clear()
        COMMANDS.update(self.original_commands)
        COMMAND_ALIASES.clear()
        COMMAND_ALIASES.update(self.original_aliases)
    
    @pytest.fixture
    def sample_command(self):
        """Create a sample command for testing."""
        return Command(
            name="/test",
            description="Test command for unit testing",
            aliases=["/t", "/test-cmd"]
        )
    
    def test_command_initialization(self, sample_command):
        """Test that Command initializes correctly."""
        assert sample_command.name == "/test"
        assert sample_command.description == "Test command for unit testing"
        assert sample_command.aliases == ["/t", "/test-cmd"]
        assert isinstance(sample_command.subcommands, dict)
        assert len(sample_command.subcommands) == 0
    
    def test_command_initialization_without_aliases(self):
        """Test Command initialization without aliases."""
        cmd = Command("/test", "Test command")
        assert cmd.name == "/test"
        assert cmd.description == "Test command"
        assert cmd.aliases == []
    
    def test_add_subcommand(self, sample_command):
        """Test adding a subcommand to a command."""
        def test_handler(args):
            return True
        
        sample_command.add_subcommand(
            "test_sub", 
            "Test subcommand", 
            test_handler
        )
        
        assert "test_sub" in sample_command.subcommands
        assert sample_command.subcommands["test_sub"]["description"] == "Test subcommand"
        assert sample_command.subcommands["test_sub"]["handler"] == test_handler
    
    def test_get_subcommands(self, sample_command):
        """Test getting list of subcommand names."""
        def handler1(args):
            return True
        def handler2(args):
            return True
        
        sample_command.add_subcommand("sub1", "Description 1", handler1)
        sample_command.add_subcommand("sub2", "Description 2", handler2)
        
        subcommands = sample_command.get_subcommands()
        assert set(subcommands) == {"sub1", "sub2"}
    
    def test_get_subcommand_description(self, sample_command):
        """Test getting subcommand description."""
        def test_handler(args):
            return True
        
        sample_command.add_subcommand(
            "test_sub", 
            "Test subcommand description", 
            test_handler
        )
        
        description = sample_command.get_subcommand_description("test_sub")
        assert description == "Test subcommand description"
        
        # Test unknown subcommand
        unknown_description = sample_command.get_subcommand_description("unknown")
        assert unknown_description == ""
    
    def test_handle_with_subcommand(self, sample_command):
        """Test handling a command with a valid subcommand."""
        def test_handler(args):
            return True
        
        sample_command.add_subcommand("test_sub", "Test subcommand", test_handler)
        
        result = sample_command.handle(["test_sub"])
        assert result is True
    
    def test_handle_with_subcommand_and_args(self, sample_command):
        """Test handling a command with subcommand and additional arguments."""
        def test_handler(args):
            assert args == ["arg1", "arg2"]
            return True
        
        sample_command.add_subcommand("test_sub", "Test subcommand", test_handler)
        
        result = sample_command.handle(["test_sub", "arg1", "arg2"])
        assert result is True
    
    def test_handle_no_args(self, sample_command):
        """Test handling command with no arguments."""
        result = sample_command.handle([])
        assert result is False  # Default implementation returns False
    
    def test_handle_unknown_subcommand(self, sample_command):
        """Test handling command with unknown subcommand."""
        result = sample_command.handle(["unknown_subcommand"])
        assert result is False  # Default implementation returns False
    
    def test_handle_no_args_default_behavior(self, sample_command):
        """Test the default handle_no_args behavior."""
        result = sample_command.handle_no_args()
        assert result is False
    
    def test_handle_unknown_subcommand_default_behavior(self, sample_command):
        """Test the default handle_unknown_subcommand behavior."""
        result = sample_command.handle_unknown_subcommand("unknown")
        assert result is False


class TestCommandRegistry:
    """Test cases for the command registry system."""
    
    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """Setup and cleanup for each test."""
        # Store original command registry
        self.original_commands = COMMANDS.copy()
        self.original_aliases = COMMAND_ALIASES.copy()
        
        # Clear registry for clean tests
        COMMANDS.clear()
        COMMAND_ALIASES.clear()
        
        yield
        
        # Restore original command registry
        COMMANDS.clear()
        COMMANDS.update(self.original_commands)
        COMMAND_ALIASES.clear()
        COMMAND_ALIASES.update(self.original_aliases)
    
    @pytest.fixture
    def test_commands(self):
        """Create test commands for registry testing."""
        cmd1 = Command("/test1", "First test command", ["/t1"])
        cmd2 = Command("/test2", "Second test command", ["/t2", "/test-two"])
        cmd3 = Command("/test3", "Third test command")
        return [cmd1, cmd2, cmd3]
    
    def test_register_command(self, test_commands):
        """Test registering a command."""
        cmd = test_commands[0]
        register_command(cmd)
        
        assert cmd.name in COMMANDS
        assert COMMANDS[cmd.name] == cmd
        assert "/t1" in COMMAND_ALIASES
        assert COMMAND_ALIASES["/t1"] == cmd.name
    
    def test_register_multiple_commands(self, test_commands):
        """Test registering multiple commands."""
        for cmd in test_commands:
            register_command(cmd)
        
        # Check all commands are registered
        assert len(COMMANDS) == 3
        for cmd in test_commands:
            assert cmd.name in COMMANDS
            assert COMMANDS[cmd.name] == cmd
        
        # Check aliases
        assert COMMAND_ALIASES["/t1"] == "/test1"
        assert COMMAND_ALIASES["/t2"] == "/test2"
        assert COMMAND_ALIASES["/test-two"] == "/test2"
    
    def test_register_command_with_duplicate_name(self, test_commands):
        """Test registering commands with duplicate names (should overwrite)."""
        cmd1 = test_commands[0]
        cmd2 = Command("/test1", "Different description")
        
        register_command(cmd1)
        register_command(cmd2)  # Should overwrite cmd1
        
        assert COMMANDS["/test1"] == cmd2
        assert COMMANDS["/test1"].description == "Different description"
    
    def test_get_command_by_name(self, test_commands):
        """Test getting a command by its name."""
        cmd = test_commands[0]
        register_command(cmd)
        
        retrieved_cmd = get_command("/test1")
        assert retrieved_cmd == cmd
    
    def test_get_command_by_alias(self, test_commands):
        """Test getting a command by its alias."""
        cmd = test_commands[0]
        register_command(cmd)
        
        retrieved_cmd = get_command("/t1")
        assert retrieved_cmd == cmd
    
    def test_get_command_nonexistent(self):
        """Test getting a non-existent command."""
        result = get_command("/nonexistent")
        assert result is None
    
    def test_handle_command_by_name(self, test_commands):
        """Test handling a command by its name."""
        cmd = test_commands[0]
        cmd.handle = Mock(return_value=True)
        register_command(cmd)
        
        result = handle_command("/test1", ["arg1", "arg2"])
        assert result is True
        cmd.handle.assert_called_once_with(["arg1", "arg2"])
    
    def test_handle_command_by_alias(self, test_commands):
        """Test handling a command by its alias."""
        cmd = test_commands[0]
        cmd.handle = Mock(return_value=True)
        register_command(cmd)
        
        result = handle_command("/t1", ["arg1"])
        assert result is True
        cmd.handle.assert_called_once_with(["arg1"])
    
    def test_handle_command_nonexistent(self):
        """Test handling a non-existent command."""
        result = handle_command("/nonexistent", ["args"])
        assert result is False
    
    def test_handle_command_no_args(self, test_commands):
        """Test handling a command with no arguments."""
        cmd = test_commands[0]
        cmd.handle = Mock(return_value=True)
        register_command(cmd)
        
        result = handle_command("/test1")
        assert result is True
        cmd.handle.assert_called_once_with(None)


class TestCustomCommand:
    """Test cases using custom command implementations."""
    
    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """Setup and cleanup for each test."""
        # Store original command registry
        self.original_commands = COMMANDS.copy()
        self.original_aliases = COMMAND_ALIASES.copy()
        
        # Clear registry for clean tests
        COMMANDS.clear()
        COMMAND_ALIASES.clear()
        
        yield
        
        # Restore original command registry
        COMMANDS.clear()
        COMMANDS.update(self.original_commands)
        COMMAND_ALIASES.clear()
        COMMAND_ALIASES.update(self.original_aliases)
    
    def test_custom_command_with_overridden_methods(self):
        """Test a custom command with overridden handle methods."""
        
        class CustomCommand(Command):
            def __init__(self):
                super().__init__("/custom", "Custom test command", ["/c"])
                self.handle_no_args_called = False
                self.handle_unknown_subcommand_called = False
            
            def handle_no_args(self):
                self.handle_no_args_called = True
                return True
            
            def handle_unknown_subcommand(self, subcommand):
                self.handle_unknown_subcommand_called = True
                self.last_unknown_subcommand = subcommand
                return True
        
        cmd = CustomCommand()
        register_command(cmd)
        
        # Test handle_no_args
        result1 = handle_command("/custom")
        assert result1 is True
        assert cmd.handle_no_args_called is True
        
        # Test handle_unknown_subcommand
        result2 = handle_command("/custom", ["unknown"])
        assert result2 is True
        assert cmd.handle_unknown_subcommand_called is True
        assert cmd.last_unknown_subcommand == "unknown"
    
    def test_custom_command_with_subcommands(self):
        """Test a custom command with predefined subcommands."""
        
        class CustomCommandWithSubcommands(Command):
            def __init__(self):
                super().__init__("/multi", "Multi-subcommand test", ["/m"])
                self.add_subcommand("start", "Start something", self.handle_start)
                self.add_subcommand("stop", "Stop something", self.handle_stop)
                self.add_subcommand("status", "Check status", self.handle_status)
                
                self.start_called = False
                self.stop_called = False
                self.status_called = False
            
            def handle_start(self, args):
                self.start_called = True
                self.start_args = args
                return True
            
            def handle_stop(self, args):
                self.stop_called = True
                self.stop_args = args
                return True
            
            def handle_status(self, args):
                self.status_called = True
                self.status_args = args
                return True
        
        cmd = CustomCommandWithSubcommands()
        register_command(cmd)
        
        # Test each subcommand
        result1 = handle_command("/multi", ["start", "param1"])
        assert result1 is True
        assert cmd.start_called is True
        assert cmd.start_args == ["param1"]
        
        result2 = handle_command("/m", ["stop"])  # Test alias
        assert result2 is True
        assert cmd.stop_called is True
        assert cmd.stop_args is None  # When no args after subcommand, None is passed
        
        result3 = handle_command("/multi", ["status", "verbose"])
        assert result3 is True
        assert cmd.status_called is True
        assert cmd.status_args == ["verbose"]
    
    def test_command_error_handling(self):
        """Test command error handling when handlers raise exceptions."""
        
        class ErrorCommand(Command):
            def __init__(self):
                super().__init__("/error", "Error test command")
                self.add_subcommand("crash", "Crash handler", self.handle_crash)
            
            def handle_crash(self, args):
                raise ValueError("Test error")
        
        cmd = ErrorCommand()
        register_command(cmd)
        
        # The command should propagate the exception
        with pytest.raises(ValueError, match="Test error"):
            handle_command("/error", ["crash"])


@pytest.mark.integration
class TestCommandIntegration:
    """Integration tests for the command system."""
    
    @pytest.fixture(autouse=True)
    def setup_integration(self):
        """Setup for integration tests."""
        # Store original command registry
        self.original_commands = COMMANDS.copy()
        self.original_aliases = COMMAND_ALIASES.copy()
        
        # Clear registry for clean tests
        COMMANDS.clear()
        COMMAND_ALIASES.clear()
        
        yield
        
        # Restore original command registry
        COMMANDS.clear()
        COMMANDS.update(self.original_commands)
        COMMAND_ALIASES.clear()
        COMMAND_ALIASES.update(self.original_aliases)
    
    def test_complete_command_lifecycle(self):
        """Test the complete lifecycle of commands."""
        # Create multiple commands with various features
        class Command1(Command):
            def __init__(self):
                super().__init__("/cmd1", "First command", ["/c1"])
                self.add_subcommand("action", "Do action", self.handle_action)
                self.action_count = 0
            
            def handle_action(self, args):
                self.action_count += 1
                return True
        
        class Command2(Command):
            def __init__(self):
                super().__init__("/cmd2", "Second command", ["/c2", "/second"])
                self.call_count = 0
            
            def handle_no_args(self):
                self.call_count += 1
                return True
        
        # Register commands
        cmd1 = Command1()
        cmd2 = Command2()
        register_command(cmd1)
        register_command(cmd2)
        
        # Test command registry state
        assert len(COMMANDS) == 2
        assert len(COMMAND_ALIASES) == 3
        
        # Test various command executions
        assert handle_command("/cmd1", ["action"]) is True
        assert cmd1.action_count == 1
        
        assert handle_command("/c1", ["action"]) is True  # Using alias
        assert cmd1.action_count == 2
        
        assert handle_command("/cmd2") is True
        assert cmd2.call_count == 1
        
        assert handle_command("/c2") is True  # Using alias
        assert cmd2.call_count == 2
        
        assert handle_command("/second") is True  # Using second alias
        assert cmd2.call_count == 3
        
        # Test non-existent command
        assert handle_command("/nonexistent") is False
    
    def test_command_alias_conflicts(self):
        """Test handling of alias conflicts (last registered wins)."""
        cmd1 = Command("/cmd1", "First command", ["/shared"])
        cmd2 = Command("/cmd2", "Second command", ["/shared"])  # Same alias
        
        register_command(cmd1)
        register_command(cmd2)  # This should overwrite the alias
        
        # The alias should point to the last registered command
        assert COMMAND_ALIASES["/shared"] == "/cmd2"
        
        retrieved_cmd = get_command("/shared")
        assert retrieved_cmd == cmd2
    
    def test_complex_subcommand_routing(self):
        """Test complex subcommand routing scenarios."""
        
        class ComplexCommand(Command):
            def __init__(self):
                super().__init__("/complex", "Complex command")
                self.add_subcommand("sub1", "Subcommand 1", self.handle_sub1)
                self.add_subcommand("sub2", "Subcommand 2", self.handle_sub2)
                
                self.results = {}
            
            def handle_sub1(self, args):
                self.results["sub1"] = args
                return True
            
            def handle_sub2(self, args):
                self.results["sub2"] = args
                return False  # Return False to test error handling
            
            def handle_unknown_subcommand(self, subcommand):
                self.results["unknown"] = subcommand
                return True
        
        cmd = ComplexCommand()
        register_command(cmd)
        
        # Test subcommand 1
        result1 = handle_command("/complex", ["sub1", "arg1", "arg2"])
        assert result1 is True
        assert cmd.results["sub1"] == ["arg1", "arg2"]
        
        # Test subcommand 2 (returns False)
        result2 = handle_command("/complex", ["sub2", "test"])
        assert result2 is False
        assert cmd.results["sub2"] == ["test"]
        
        # Test unknown subcommand
        result3 = handle_command("/complex", ["unknown_sub"])
        assert result3 is True
        assert cmd.results["unknown"] == "unknown_sub"


if __name__ == '__main__':
    pytest.main([__file__, "-v"]) 