#!/usr/bin/env python3
"""
Test suite for the model command functionality.
Tests all handle methods and input possibilities for the model command.
"""

import os
import sys
import pytest
import datetime
from unittest.mock import patch, Mock, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 
                                '..', '..', 'src'))

from cai.repl.commands.model import ModelCommand, ModelShowCommand
from cai.repl.commands.base import Command


class TestModelCommand:
    """Test cases for ModelCommand."""
    
    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """Setup and cleanup for each test."""
        # Set up test environment
        os.environ['CAI_TELEMETRY'] = 'false'
        os.environ['CAI_TRACING'] = 'false'
        
        # Store original CAI_MODEL if it exists
        self.original_model = os.environ.get('CAI_MODEL')
        
        yield
        
        # Restore original CAI_MODEL or remove if it didn't exist
        if self.original_model is not None:
            os.environ['CAI_MODEL'] = self.original_model
        elif 'CAI_MODEL' in os.environ:
            del os.environ['CAI_MODEL']
    
    @pytest.fixture
    def model_command(self):
        """Create a ModelCommand instance for testing."""
        return ModelCommand()
    
    @pytest.fixture
    def model_show_command(self):
        """Create a ModelShowCommand instance for testing."""
        return ModelShowCommand()
    
    @pytest.fixture
    def mock_litellm_response(self):
        """Create a mock response for LiteLLM model data."""
        return {
            "gpt-4": {
                "input_cost_per_token": 0.00003,
                "output_cost_per_token": 0.00006,
                "max_tokens": 8192,
                "supports_function_calling": True,
                "supports_vision": False,
                "litellm_provider": "openai"
            },
            "claude-3-sonnet-20240229": {
                "input_cost_per_token": 0.000015,
                "output_cost_per_token": 0.000075,
                "max_tokens": 200000,
                "supports_function_calling": True,
                "supports_vision": True,
                "litellm_provider": "anthropic"
            },
            "deepseek/deepseek-v3": {
                "input_cost_per_token": 0.000001,
                "output_cost_per_token": 0.000002,
                "max_tokens": 128000,
                "supports_function_calling": True,
                "supports_vision": False,
                "litellm_provider": "deepseek"
            }
        }
    
    @pytest.fixture
    def mock_ollama_response(self):
        """Create a mock response for Ollama models."""
        return {
            "models": [
                {
                    "name": "llama3",
                    "size": 4661211648  # ~4.3 GB
                },
                {
                    "name": "mistral:7b",
                    "size": 7365960192  # ~6.9 GB
                }
            ]
        }
    
    def test_command_initialization(self, model_command):
        """Test that ModelCommand initializes correctly."""
        assert model_command.name == "/model"
        assert model_command.description == "View or change the current LLM model"
        assert model_command.aliases == ["/mod"]
        
        # Check that cached models and numbers are initialized
        assert hasattr(model_command, 'cached_models')
        assert hasattr(model_command, 'cached_model_numbers')
        assert hasattr(model_command, 'last_model_fetch')
    
    def test_model_show_command_initialization(self, model_show_command):
        """Test that ModelShowCommand initializes correctly."""
        assert model_show_command.name == "/model-show"
        assert model_show_command.description == "Show all available models from LiteLLM repository"
        assert model_show_command.aliases == ["/mod-show"]
    
    @patch('requests.get')
    def test_handle_no_args_with_mock_data(self, mock_get, model_command, 
                                          mock_litellm_response, mock_ollama_response):
        """Test showing current model and available models with no arguments."""
        # Mock LiteLLM response
        mock_litellm = Mock()
        mock_litellm.status_code = 200
        mock_litellm.json.return_value = mock_litellm_response
        
        # Mock Ollama response
        mock_ollama = Mock()
        mock_ollama.status_code = 200
        mock_ollama.json.return_value = mock_ollama_response
        
        # Configure the mock to return different responses based on URL
        def side_effect(url, timeout=None):
            if "litellm" in url:
                return mock_litellm
            elif "ollama" in url:
                return mock_ollama
            else:
                return Mock(status_code=404)
        
        mock_get.side_effect = side_effect
        
        # Set a model first
        os.environ['CAI_MODEL'] = 'gpt-4'
        
        result = model_command.handle([])
        assert result is True
    
    @patch('requests.get')
    def test_handle_select_model_by_name(self, mock_get, model_command, 
                                        mock_litellm_response):
        """Test selecting a model by name."""
        # Mock LiteLLM response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_litellm_response
        mock_get.return_value = mock_response
        
        result = model_command.handle(["gpt-4"])
        assert result is True
        assert os.environ.get('CAI_MODEL') == 'gpt-4'
    
    @patch('requests.get')
    def test_handle_select_model_by_number(self, mock_get, model_command, 
                                          mock_litellm_response):
        """Test selecting a model by number."""
        # Mock LiteLLM response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_litellm_response
        mock_get.return_value = mock_response
        
        # First call to populate cache
        model_command.handle([])
        
        # Then select by number
        result = model_command.handle(["1"])
        assert result is True
        assert 'CAI_MODEL' in os.environ
    
    def test_handle_select_custom_model(self, model_command):
        """Test selecting a custom model name not in the predefined list."""
        result = model_command.handle(["custom-model-name"])
        assert result is True
        assert os.environ.get('CAI_MODEL') == 'custom-model-name'
    
    @patch('requests.get')
    def test_handle_with_network_error(self, mock_get, model_command):
        """Test handling when network requests fail."""
        # Mock network failure
        mock_get.side_effect = Exception("Network error")
        
        result = model_command.handle([])
        assert result is True  # Should still work, just without external data
    
    @patch('requests.get')
    def test_handle_model_pricing_data_error(self, mock_get, model_command):
        """Test handling when LiteLLM API returns error."""
        # Mock HTTP error
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = model_command.handle([])
        assert result is True  # Should still work with built-in models
    
    def test_command_base_functionality(self, model_command):
        """Test that the command inherits from base Command properly."""
        assert isinstance(model_command, Command)
        assert model_command.name == "/model"
        assert "/mod" in model_command.aliases


class TestModelShowCommand:
    """Test cases for ModelShowCommand."""
    
    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """Setup and cleanup for each test."""
        # Set up test environment
        os.environ['CAI_TELEMETRY'] = 'false'
        os.environ['CAI_TRACING'] = 'false'
        
        yield
    
    @pytest.fixture
    def model_show_command(self):
        """Create a ModelShowCommand instance for testing."""
        return ModelShowCommand()
    
    @pytest.fixture
    def mock_litellm_response(self):
        """Create a mock response for LiteLLM model data."""
        return {
            "gpt-4": {
                "input_cost_per_token": 0.00003,
                "output_cost_per_token": 0.00006,
                "max_tokens": 8192,
                "supports_function_calling": True,
                "supports_vision": False,
                "litellm_provider": "openai"
            },
            "claude-3-sonnet-20240229": {
                "input_cost_per_token": 0.000015,
                "output_cost_per_token": 0.000075,
                "max_tokens": 200000,
                "supports_function_calling": True,
                "supports_vision": True,
                "litellm_provider": "anthropic"
            },
            "gpt-3.5-turbo": {
                "input_cost_per_token": 0.000001,
                "output_cost_per_token": 0.000002,
                "max_tokens": 4096,
                "supports_function_calling": False,
                "supports_vision": False,
                "litellm_provider": "openai"
            }
        }
    
    @pytest.fixture
    def mock_ollama_response(self):
        """Create a mock response for Ollama models."""
        return {
            "models": [
                {
                    "name": "llama3",
                    "size": 4661211648
                },
                {
                    "name": "mistral:7b",
                    "size": 7365960192
                }
            ]
        }
    
    @patch('requests.get')
    def test_handle_no_args(self, mock_get, model_show_command, 
                           mock_litellm_response, mock_ollama_response):
        """Test showing all models with no arguments."""
        # Mock LiteLLM response
        mock_litellm = Mock()
        mock_litellm.status_code = 200
        mock_litellm.json.return_value = mock_litellm_response
        
        # Mock Ollama response
        mock_ollama = Mock()
        mock_ollama.status_code = 200
        mock_ollama.json.return_value = mock_ollama_response
        
        # Configure the mock to return different responses based on URL
        def side_effect(url, timeout=None):
            if "litellm" in url:
                return mock_litellm
            elif "ollama" in url:
                return mock_ollama
            else:
                return Mock(status_code=404)
        
        mock_get.side_effect = side_effect
        
        result = model_show_command.handle([])
        assert result is True
    
    @patch('requests.get')
    def test_handle_supported_filter(self, mock_get, model_show_command, 
                                    mock_litellm_response):
        """Test showing only supported models (with function calling)."""
        # Mock LiteLLM response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_litellm_response
        mock_get.return_value = mock_response
        
        result = model_show_command.handle(["supported"])
        assert result is True
    
    @patch('requests.get')
    def test_handle_search_filter(self, mock_get, model_show_command, 
                                 mock_litellm_response):
        """Test filtering models by search term."""
        # Mock LiteLLM response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_litellm_response
        mock_get.return_value = mock_response
        
        result = model_show_command.handle(["gpt"])
        assert result is True
    
    @patch('requests.get')
    def test_handle_supported_and_search(self, mock_get, model_show_command, 
                                        mock_litellm_response):
        """Test combining supported filter with search term."""
        # Mock LiteLLM response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_litellm_response
        mock_get.return_value = mock_response
        
        result = model_show_command.handle(["supported", "claude"])
        assert result is True
    
    @patch('requests.get')
    def test_handle_network_error(self, mock_get, model_show_command):
        """Test handling when network request fails."""
        # Mock network failure
        mock_get.side_effect = Exception("Network error")
        
        result = model_show_command.handle([])
        assert result is True  # Should handle gracefully
    
    @patch('requests.get')
    def test_handle_http_error(self, mock_get, model_show_command):
        """Test handling when API returns HTTP error."""
        # Mock HTTP error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        result = model_show_command.handle([])
        assert result is True  # Should handle gracefully
    
    @patch('requests.get')
    def test_handle_with_ollama_error(self, mock_get, model_show_command, 
                                     mock_litellm_response):
        """Test handling when Ollama is not available but LiteLLM works."""
        # Mock LiteLLM success but Ollama failure
        def side_effect(url, timeout=None):
            if "litellm" in url:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_litellm_response
                return mock_response
            elif "ollama" in url:
                raise Exception("Ollama not available")
            else:
                return Mock(status_code=404)
        
        mock_get.side_effect = side_effect
        
        result = model_show_command.handle([])
        assert result is True


@pytest.mark.integration
class TestModelCommandIntegration:
    """Integration tests for model command functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_integration(self):
        """Setup for integration tests."""
        # Store original CAI_MODEL if it exists
        self.original_model = os.environ.get('CAI_MODEL')
        
        yield
        
        # Restore original CAI_MODEL or remove if it didn't exist
        if self.original_model is not None:
            os.environ['CAI_MODEL'] = self.original_model
        elif 'CAI_MODEL' in os.environ:
            del os.environ['CAI_MODEL']
    
    @patch('requests.get')
    def test_full_model_workflow(self, mock_get):
        """Test a complete workflow of listing and selecting models."""
        # Mock responses
        mock_litellm_response = {
            "gpt-4": {
                "input_cost_per_token": 0.00003,
                "output_cost_per_token": 0.00006,
                "max_tokens": 8192,
                "supports_function_calling": True
            },
            "claude-3-sonnet-20240229": {
                "input_cost_per_token": 0.000015,
                "output_cost_per_token": 0.000075,
                "max_tokens": 200000,
                "supports_function_calling": True
            }
        }
        
        mock_ollama_response = {
            "models": [
                {"name": "llama3", "size": 4661211648}
            ]
        }
        
        # Configure mock responses
        def side_effect(url, timeout=None):
            if "litellm" in url:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_litellm_response
                return mock_response
            elif "ollama" in url:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_ollama_response
                return mock_response
            else:
                return Mock(status_code=404)
        
        mock_get.side_effect = side_effect
        
        model_cmd = ModelCommand()
        model_show_cmd = ModelShowCommand()
        
        # List all models
        result1 = model_cmd.handle([])
        assert result1 is True
        
        # Show detailed model info
        result2 = model_show_cmd.handle([])
        assert result2 is True
        
        # Select a model by name
        result3 = model_cmd.handle(["gpt-4"])
        assert result3 is True
        assert os.environ.get('CAI_MODEL') == 'gpt-4'
        
        # Show current model again
        result4 = model_cmd.handle([])
        assert result4 is True
        
        # Select by number (after cache is populated)
        result5 = model_cmd.handle(["1"])
        assert result5 is True
    
    @patch('requests.get')
    def test_model_selection_edge_cases(self, mock_get):
        """Test edge cases in model selection."""
        # Mock minimal response to avoid network dependency
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"gpt-4": {}}
        mock_get.return_value = mock_response
        
        cmd = ModelCommand()
        
        # Test selecting non-existent number (large number)
        result1 = cmd.handle(["999"])
        assert result1 is True
        assert os.environ.get('CAI_MODEL') == '999'  # Should use as literal
        
        # Test selecting model with special characters
        result2 = cmd.handle(["custom/model:latest"])
        assert result2 is True
        assert os.environ.get('CAI_MODEL') == 'custom/model:latest'
        
        # Test empty model name (edge case)
        result3 = cmd.handle([""])
        assert result3 is True
        assert os.environ.get('CAI_MODEL') == ''
    
    @patch('requests.get')
    def test_model_show_filters_combination(self, mock_get):
        """Test various combinations of filters in model-show command."""
        mock_response = {
            "gpt-4": {
                "supports_function_calling": True,
                "input_cost_per_token": 0.00003,
                "output_cost_per_token": 0.00006
            },
            "gpt-3.5-turbo": {
                "supports_function_calling": False,
                "input_cost_per_token": 0.000001,
                "output_cost_per_token": 0.000002
            },
            "claude-3-sonnet": {
                "supports_function_calling": True,
                "input_cost_per_token": 0.000015,
                "output_cost_per_token": 0.000075
            }
        }
        
        mock_http_response = Mock()
        mock_http_response.status_code = 200
        mock_http_response.json.return_value = mock_response
        mock_get.return_value = mock_http_response
        
        cmd = ModelShowCommand()
        
        # Test supported only
        result1 = cmd.handle(["supported"])
        assert result1 is True
        
        # Test search only
        result2 = cmd.handle(["gpt"])
        assert result2 is True
        
        # Test supported + search
        result3 = cmd.handle(["supported", "claude"])
        assert result3 is True
        
        # Test search + supported (different order)
        result4 = cmd.handle(["claude", "supported"])
        assert result4 is True


if __name__ == '__main__':
    pytest.main([__file__, "-v"]) 