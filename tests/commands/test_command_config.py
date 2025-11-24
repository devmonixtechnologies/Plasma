#!/usr/bin/env python3
"""
Test suite for the config command functionality.
Tests all handle methods and input possibilities for the config command.
"""

import os
import sys
import pytest
from unittest.mock import patch, Mock, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 
                                '..', '..', 'src'))

from cai.repl.commands.config import (
    ConfigCommand, ENV_VARS, get_env_var_value, set_env_var
)
from cai.repl.commands.base import Command


class TestConfigCommand:
    """Test cases for ConfigCommand."""
    
    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """Setup and cleanup for each test."""
        # Set up test environment
        os.environ['CAI_TELEMETRY'] = 'false'
        os.environ['CAI_TRACING'] = 'false'
        
        # Store original values of environment variables we'll modify
        self.original_env_vars = {}
        for var_info in ENV_VARS.values():
            var_name = var_info["name"]
            if var_name in os.environ:
                self.original_env_vars[var_name] = os.environ[var_name]
        
        yield
        
        # Restore original environment variables
        for var_info in ENV_VARS.values():
            var_name = var_info["name"]
            if var_name in self.original_env_vars:
                os.environ[var_name] = self.original_env_vars[var_name]
            elif var_name in os.environ:
                del os.environ[var_name]
    
    @pytest.fixture
    def config_command(self):
        """Create a ConfigCommand instance for testing."""
        return ConfigCommand()
    
    def test_command_initialization(self, config_command):
        """Test that ConfigCommand initializes correctly."""
        assert config_command.name == "/config"
        assert config_command.description == "Display and configure environment variables"
        assert config_command.aliases == ["/cfg"]
        
        # Check subcommands are registered
        expected_subcommands = ["list", "set", "get"]
        assert set(config_command.get_subcommands()) == set(expected_subcommands)
    
    def test_env_vars_structure(self):
        """Test that ENV_VARS has the expected structure."""
        assert isinstance(ENV_VARS, dict)
        assert len(ENV_VARS) > 0
        
        # Check each env var has required fields
        for num, var_info in ENV_VARS.items():
            assert isinstance(num, int)
            assert "name" in var_info
            assert "description" in var_info
            assert "default" in var_info
            
            # Check name is a string
            assert isinstance(var_info["name"], str)
            assert isinstance(var_info["description"], str)
            # default can be None or string
            assert var_info["default"] is None or isinstance(var_info["default"], str)
    
    def test_get_env_var_value_with_set_value(self):
        """Test getting environment variable value when it's set."""
        # Set a test value
        os.environ["CAI_MODEL"] = "test-model"
        
        result = get_env_var_value("CAI_MODEL")
        assert result == "test-model"
    
    def test_get_env_var_value_with_default(self):
        """Test getting environment variable value when it's not set (returns default)."""
        # Make sure the variable is not set
        if "CAI_MODEL" in os.environ:
            del os.environ["CAI_MODEL"]
        
        result = get_env_var_value("CAI_MODEL")
        # Should return the default value from ENV_VARS
        expected_default = None
        for var_info in ENV_VARS.values():
            if var_info["name"] == "CAI_MODEL":
                expected_default = var_info["default"]
                break
        
        assert result == (expected_default or "Not set")
    
    def test_get_env_var_value_unknown_variable(self):
        """Test getting value for unknown environment variable."""
        result = get_env_var_value("UNKNOWN_VARIABLE")
        assert result == "Unknown variable"
    
    def test_set_env_var(self):
        """Test setting an environment variable."""
        result = set_env_var("TEST_VAR", "test_value")
        assert result is True
        assert os.environ.get("TEST_VAR") == "test_value"
        
        # Cleanup
        if "TEST_VAR" in os.environ:
            del os.environ["TEST_VAR"]
    
    def test_handle_list(self, config_command):
        """Test listing all environment variables."""
        result = config_command.handle_list([])
        assert result is True
    
    def test_handle_no_args(self, config_command):
        """Test handling when no arguments provided (should default to list)."""
        result = config_command.handle_no_args()
        assert result is True
    
    def test_handle_get_valid_number(self, config_command):
        """Test getting a variable by valid number."""
        # Test with variable number 6 (CAI_MODEL)
        result = config_command.handle_get(["6"])
        assert result is True
    
    def test_handle_get_invalid_number(self, config_command):
        """Test getting a variable by invalid number."""
        result = config_command.handle_get(["999"])
        assert result is False
    
    def test_handle_get_non_integer(self, config_command):
        """Test getting a variable with non-integer number."""
        result = config_command.handle_get(["not_a_number"])
        assert result is False
    
    def test_handle_get_no_args(self, config_command):
        """Test get command with no arguments."""
        result = config_command.handle_get([])
        assert result is False
    
    def test_handle_set_valid_number_and_value(self, config_command):
        """Test setting a variable by valid number and value."""
        # Test with variable number 6 (CAI_MODEL)
        result = config_command.handle_set(["6", "new-test-model"])
        assert result is True
        assert os.environ.get("CAI_MODEL") == "new-test-model"
    
    def test_handle_set_invalid_number(self, config_command):
        """Test setting a variable by invalid number."""
        result = config_command.handle_set(["999", "some_value"])
        assert result is False
    
    def test_handle_set_non_integer(self, config_command):
        """Test setting a variable with non-integer number."""
        result = config_command.handle_set(["not_a_number", "some_value"])
        assert result is False
    
    def test_handle_set_no_args(self, config_command):
        """Test set command with no arguments."""
        result = config_command.handle_set([])
        assert result is False
    
    def test_handle_set_insufficient_args(self, config_command):
        """Test set command with insufficient arguments."""
        result = config_command.handle_set(["6"])  # Missing value
        assert result is False
    
    def test_handle_set_with_spaces_in_value(self, config_command):
        """Test setting a variable with value containing spaces."""
        result = config_command.handle_set(["6", "model with spaces"])
        assert result is True
        assert os.environ.get("CAI_MODEL") == "model with spaces"
    
    def test_handle_set_empty_value(self, config_command):
        """Test setting a variable with empty value."""
        result = config_command.handle_set(["6", ""])
        assert result is True
        assert os.environ.get("CAI_MODEL") == ""
    
    def test_command_base_functionality(self, config_command):
        """Test that the command inherits from base Command properly."""
        assert isinstance(config_command, Command)
        assert config_command.name == "/config"
        assert "/cfg" in config_command.aliases
    
    def test_handle_main_command_routing(self, config_command):
        """Test that main handle method routes to correct subcommands."""
        # Test routing to list (no args defaults to list)
        result1 = config_command.handle([])
        assert result1 is True
        
        # Test routing to list explicitly
        result2 = config_command.handle(["list"])
        assert result2 is True
        
        # Test routing to get
        result3 = config_command.handle(["get", "6"])
        assert result3 is True
        
        # Test routing to set
        result4 = config_command.handle(["set", "6", "test-value"])
        assert result4 is True
        assert os.environ.get("CAI_MODEL") == "test-value"
    
    def test_handle_unknown_subcommand(self, config_command):
        """Test handling of unknown subcommands."""
        result = config_command.handle(["unknown_subcommand"])
        assert result is False
    
    def test_specific_env_vars_exist(self):
        """Test that specific important environment variables are defined."""
        important_vars = [
            "CAI_MODEL", "CAI_DEBUG", "CAI_BRIEF", "CAI_MAX_TURNS",
            "CAI_TRACING", "CAI_AGENT_TYPE", "CTF_NAME", "CTF_CHALLENGE"
        ]
        
        defined_var_names = [var_info["name"] for var_info in ENV_VARS.values()]
        
        for var_name in important_vars:
            assert var_name in defined_var_names, f"{var_name} should be defined in ENV_VARS"
    
    def test_env_var_defaults_are_reasonable(self):
        """Test that environment variable defaults are reasonable."""
        # Check that important variables have reasonable defaults
        for var_info in ENV_VARS.values():
            var_name = var_info["name"]
            default = var_info["default"]
            
            # Boolean-like variables should have "true"/"false" defaults or numeric values
            # Exclude interval variables as they have numeric values
            boolean_keywords = ["debug", "brief", "tracing", "memory", "online", "offline", "inside"]
            if (any(keyword in var_name.lower() for keyword in boolean_keywords) and 
                "interval" not in var_name.lower()):
                if default is not None:
                    # Accept boolean strings or numeric values (for debug levels)
                    valid_values = ["true", "false", "0", "1", "2"]
                    assert default.lower() in valid_values, f"{var_name} should have boolean-like or numeric default"
            
            # Numeric variables should have numeric defaults
            if any(keyword in var_name.lower() for keyword in ["turns", "limit", "interval"]):
                if default is not None:
                    # Should be numeric or "inf"
                    try:
                        float(default)
                    except ValueError:
                        assert default == "inf", f"{var_name} should have numeric default or 'inf'"


@pytest.mark.integration
class TestConfigCommandIntegration:
    """Integration tests for config command functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_integration(self):
        """Setup for integration tests."""
        # Store original values
        self.original_env_vars = {}
        for var_info in ENV_VARS.values():
            var_name = var_info["name"]
            if var_name in os.environ:
                self.original_env_vars[var_name] = os.environ[var_name]
        
        yield
        
        # Restore original values
        for var_info in ENV_VARS.values():
            var_name = var_info["name"]
            if var_name in self.original_env_vars:
                os.environ[var_name] = self.original_env_vars[var_name]
            elif var_name in os.environ:
                del os.environ[var_name]
    
    def test_full_config_workflow(self):
        """Test a complete workflow of listing, getting, and setting variables."""
        cmd = ConfigCommand()
        
        # List all variables
        result1 = cmd.handle(["list"])
        assert result1 is True
        
        # Get a specific variable (CAI_MODEL - number 6)
        result2 = cmd.handle(["get", "6"])
        assert result2 is True
        
        # Set the variable to a new value
        result3 = cmd.handle(["set", "6", "integration-test-model"])
        assert result3 is True
        assert os.environ.get("CAI_MODEL") == "integration-test-model"
        
        # Get the variable again to verify it changed
        result4 = cmd.handle(["get", "6"])
        assert result4 is True
        
        # Set it back to default (if it had a default)
        for var_info in ENV_VARS.values():
            if var_info["name"] == "CAI_MODEL" and var_info["default"]:
                result5 = cmd.handle(["set", "6", var_info["default"]])
                assert result5 is True
                break
    
    def test_multiple_variable_modifications(self):
        """Test modifying multiple variables in sequence."""
        cmd = ConfigCommand()
        
        # Modify several variables
        modifications = [
            ("6", "test-model"),      # CAI_MODEL
            ("7", "2"),               # CAI_DEBUG
            ("8", "true"),            # CAI_BRIEF
        ]
        
        for var_num, value in modifications:
            result = cmd.handle(["set", var_num, value])
            assert result is True
            
            # Verify the change
            get_result = cmd.handle(["get", var_num])
            assert get_result is True
        
        # Verify all changes are still present
        for var_num, expected_value in modifications:
            # Find the variable name
            var_info = ENV_VARS[int(var_num)]
            var_name = var_info["name"]
            assert os.environ.get(var_name) == expected_value
    
    def test_edge_case_values(self):
        """Test setting variables with edge case values."""
        cmd = ConfigCommand()
        
        edge_cases = [
            ("6", ""),                    # Empty string
            ("6", "value with spaces"),   # Spaces
            ("6", "special!@#$%chars"),   # Special characters
            ("6", "very_long_value_that_exceeds_normal_length_expectations"),  # Long value
            ("7", "0"),                   # Zero
            ("7", "999"),                 # Large number
        ]
        
        for var_num, value in edge_cases:
            result = cmd.handle(["set", var_num, value])
            assert result is True
            
            # Find the variable name and verify
            var_info = ENV_VARS[int(var_num)]
            var_name = var_info["name"]
            assert os.environ.get(var_name) == value
    
    def test_all_env_vars_can_be_set_and_retrieved(self):
        """Test that all defined environment variables can be set and retrieved."""
        cmd = ConfigCommand()
        
        for var_num, var_info in ENV_VARS.items():
            var_name = var_info["name"]
            test_value = f"test_value_for_{var_name}"
            
            # Set the variable
            set_result = cmd.handle(["set", str(var_num), test_value])
            assert set_result is True, f"Failed to set {var_name}"
            
            # Get the variable
            get_result = cmd.handle(["get", str(var_num)])
            assert get_result is True, f"Failed to get {var_name}"
            
            # Verify the value was set correctly
            assert os.environ.get(var_name) == test_value


if __name__ == '__main__':
    pytest.main([__file__, "-v"]) 