"""
Tests for the cost command.
"""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from cai.repl.commands.cost import CostCommand
from cai.sdk.agents.global_usage_tracker import GlobalUsageTracker


class TestCostCommand:
    """Test cases for the cost command."""

    @pytest.fixture
    def cost_command(self):
        """Create a cost command instance."""
        return CostCommand()

    @pytest.fixture
    def mock_console(self):
        """Mock the console for testing output."""
        with patch("cai.repl.commands.cost.console") as mock:
            # Set default width for console
            mock.width = 80
            yield mock

    @pytest.fixture
    def temp_usage_file(self):
        """Create a temporary usage file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            usage_data = {
                "global_totals": {
                    "total_cost": 1.234567,
                    "total_input_tokens": 50000,
                    "total_output_tokens": 25000,
                    "total_requests": 100,
                    "total_sessions": 10
                },
                "model_usage": {
                    "gpt-4": {
                        "total_cost": 0.8,
                        "total_input_tokens": 30000,
                        "total_output_tokens": 15000,
                        "total_requests": 60
                    },
                    "claude-3-opus": {
                        "total_cost": 0.434567,
                        "total_input_tokens": 20000,
                        "total_output_tokens": 10000,
                        "total_requests": 40
                    }
                },
                "daily_usage": {
                    "2025-01-15": {
                        "total_cost": 0.5,
                        "total_input_tokens": 20000,
                        "total_output_tokens": 10000,
                        "total_requests": 40
                    },
                    "2025-01-14": {
                        "total_cost": 0.734567,
                        "total_input_tokens": 30000,
                        "total_output_tokens": 15000,
                        "total_requests": 60
                    }
                },
                "sessions": [
                    {
                        "session_id": "test-session-001",
                        "start_time": "2025-01-14T10:00:00",
                        "end_time": "2025-01-14T11:30:00",
                        "total_cost": 0.5,
                        "total_input_tokens": 10000,
                        "total_output_tokens": 5000,
                        "total_requests": 20,
                        "models_used": ["gpt-4", "claude-3-opus"]
                    },
                    {
                        "session_id": "test-session-002",
                        "start_time": "2025-01-15T14:00:00",
                        "end_time": None,  # Active session
                        "total_cost": 0.234567,
                        "total_input_tokens": 5000,
                        "total_output_tokens": 2500,
                        "total_requests": 10,
                        "models_used": ["gpt-4"]
                    }
                ]
            }
            json.dump(usage_data, f)
            yield f.name
        
        # Cleanup
        Path(f.name).unlink(missing_ok=True)

    def test_command_initialization(self, cost_command):
        """Test that the cost command is properly initialized."""
        assert cost_command.name == "/cost"
        assert cost_command.description == "View usage costs and statistics"
        assert "/costs" in cost_command.aliases
        assert "/usage" in cost_command.aliases
        
        # Check subcommands
        assert "summary" in cost_command.subcommands
        assert "models" in cost_command.subcommands
        assert "daily" in cost_command.subcommands
        assert "sessions" in cost_command.subcommands
        assert "reset" in cost_command.subcommands

    def test_handle_no_args_calls_summary(self, cost_command, mock_console):
        """Test that handle with no args calls handle_summary."""
        with patch.object(cost_command, 'handle_summary', return_value=True) as mock_summary:
            result = cost_command.handle([])
            assert result is True
            mock_summary.assert_called_once_with()

    def test_handle_summary_subcommand(self, cost_command, mock_console):
        """Test handling the summary subcommand."""
        # Patch the handler in the subcommands dictionary
        original_handler = cost_command.subcommands["summary"]["handler"]
        mock_summary = Mock(return_value=True)
        cost_command.subcommands["summary"]["handler"] = mock_summary
        
        try:
            result = cost_command.handle(["summary"])
            assert result is True
            mock_summary.assert_called_once_with([])
        finally:
            # Restore original handler
            cost_command.subcommands["summary"]["handler"] = original_handler

    def test_handle_models_subcommand(self, cost_command, mock_console):
        """Test handling the models subcommand."""
        # Patch the handler in the subcommands dictionary
        original_handler = cost_command.subcommands["models"]["handler"]
        mock_models = Mock(return_value=True)
        cost_command.subcommands["models"]["handler"] = mock_models
        
        try:
            result = cost_command.handle(["models"])
            assert result is True
            mock_models.assert_called_once_with([])
        finally:
            # Restore original handler
            cost_command.subcommands["models"]["handler"] = original_handler

    @patch('cai.repl.commands.cost.console')
    @patch('cai.repl.commands.cost.GLOBAL_USAGE_TRACKER')
    @patch('cai.repl.commands.cost.COST_TRACKER')
    def test_handle_summary_with_data(self, mock_cost_tracker, mock_global_tracker, 
                                     mock_console_direct, cost_command, mock_console, temp_usage_file):
        """Test handle_summary with actual usage data."""
        # Mock console width
        mock_console_direct.width = 120
        
        # Mock COST_TRACKER
        mock_cost_tracker.session_total_cost = 0.123456
        mock_cost_tracker.current_agent_total_cost = 0.05
        mock_cost_tracker.current_agent_input_tokens = 1000
        mock_cost_tracker.current_agent_output_tokens = 500
        
        # Mock GLOBAL_USAGE_TRACKER
        mock_global_tracker.enabled = True
        # We don't need to actually read the file since we're mocking the response
        mock_global_tracker.get_summary.return_value = {
            "global_totals": {
                "total_cost": 1.234567,
                "total_input_tokens": 50000,
                "total_output_tokens": 25000,
                "total_requests": 100,
                "total_sessions": 10
            },
            "top_models": [
                ("gpt-4", 0.8),
                ("claude-3-opus", 0.434567)
            ]
        }
        
        # Call handle_summary
        result = cost_command.handle_summary()
        assert result is True
        
        # Verify console output was called - simplified test 
        # Just verify the method was called, not the specific content
        assert mock_console_direct.print.called
        assert mock_console_direct.print.call_count >= 2  # At least header prints

    @patch('cai.repl.commands.cost.GLOBAL_USAGE_TRACKER')
    def test_handle_models_with_data(self, mock_global_tracker, cost_command, 
                                    mock_console, temp_usage_file):
        """Test handle_models with usage data."""
        mock_global_tracker.enabled = True
        with open(temp_usage_file) as f:
            usage_data = json.load(f)
        mock_global_tracker.usage_data = usage_data
        
        # Call handle_models
        result = cost_command.handle_models()
        assert result is True
        
        # Verify table was created
        assert mock_console.print.called
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Model Usage Statistics" in str(call) for call in print_calls)

    @patch('cai.repl.commands.cost.GLOBAL_USAGE_TRACKER')
    def test_handle_daily_with_data(self, mock_global_tracker, cost_command, 
                                   mock_console, temp_usage_file):
        """Test handle_daily with usage data."""
        mock_global_tracker.enabled = True
        with open(temp_usage_file) as f:
            usage_data = json.load(f)
        mock_global_tracker.usage_data = usage_data
        
        # Call handle_daily
        result = cost_command.handle_daily()
        assert result is True
        
        # Verify table was created
        assert mock_console.print.called
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Daily Usage Statistics" in str(call) for call in print_calls)

    @patch('cai.repl.commands.cost.GLOBAL_USAGE_TRACKER')
    def test_handle_sessions_with_data(self, mock_global_tracker, cost_command, 
                                      mock_console, temp_usage_file):
        """Test handle_sessions with usage data."""
        mock_global_tracker.enabled = True
        with open(temp_usage_file) as f:
            usage_data = json.load(f)
        mock_global_tracker.usage_data = usage_data
        
        # Call handle_sessions
        result = cost_command.handle_sessions()
        assert result is True
        
        # Verify table was created
        assert mock_console.print.called
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Recent" in str(call) and "Sessions" in str(call) for call in print_calls)

    @patch('cai.repl.commands.cost.GLOBAL_USAGE_TRACKER')
    def test_handle_sessions_with_limit(self, mock_global_tracker, cost_command, 
                                       mock_console, temp_usage_file):
        """Test handle_sessions with a custom limit."""
        mock_global_tracker.enabled = True
        with open(temp_usage_file) as f:
            usage_data = json.load(f)
        
        # Add more sessions for testing
        for i in range(3, 15):
            usage_data["sessions"].append({
                "session_id": f"test-session-{i:03d}",
                "start_time": f"2025-01-{15+i}T10:00:00",
                "end_time": f"2025-01-{15+i}T11:00:00",
                "total_cost": 0.1 * i,
                "total_requests": 5 * i,
                "models_used": ["gpt-4"]
            })
        
        mock_global_tracker.usage_data = usage_data
        
        # Call handle_sessions with limit
        result = cost_command.handle_sessions(["5"])
        assert result is True
        
        # Verify correct number of sessions shown
        assert mock_console.print.called
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Recent 5 Sessions" in str(call) for call in print_calls)

    @patch('cai.repl.commands.cost.GLOBAL_USAGE_TRACKER')
    def test_handle_reset_no_data(self, mock_global_tracker, cost_command, mock_console):
        """Test handle_reset when no usage data exists."""
        mock_global_tracker.enabled = True
        
        with patch('cai.repl.commands.cost.Path') as mock_path:
            mock_path.home.return_value = Path("/home/test")
            mock_usage_file = MagicMock()
            mock_usage_file.exists.return_value = False
            mock_path.return_value.__truediv__.return_value.__truediv__.return_value = mock_usage_file
            
            result = cost_command.handle_reset()
            assert result is True
            
            # Verify appropriate message
            mock_console.print.assert_any_call("[yellow]No usage data to reset[/yellow]")

    @patch('cai.repl.commands.cost.GLOBAL_USAGE_TRACKER')
    def test_handle_reset_with_confirmation(self, mock_global_tracker, cost_command, 
                                          mock_console, temp_usage_file):
        """Test handle_reset with user confirmation."""
        mock_global_tracker.enabled = True
        mock_global_tracker.get_summary.return_value = {
            "global_totals": {
                "total_cost": 1.234567,
                "total_sessions": 10
            }
        }
        
        # Mock user input for confirmation
        mock_console.input.return_value = "RESET"
        
        with patch('cai.repl.commands.cost.Path') as mock_path:
            mock_path.home.return_value = Path(tempfile.gettempdir())
            mock_usage_file = MagicMock()
            mock_usage_file.exists.return_value = True
            mock_usage_file.with_name.return_value = Path("/tmp/backup.json")
            mock_path.return_value.__truediv__.return_value.__truediv__.return_value = mock_usage_file
            
            with patch('cai.repl.commands.cost.shutil.copy2') as mock_copy:
                result = cost_command.handle_reset()
                assert result is True
                
                # Verify backup was created
                mock_copy.assert_called_once()
                
                # Verify file was deleted
                mock_usage_file.unlink.assert_called_once()
                
                # Verify success message
                assert any("reset" in str(call).lower() for call in mock_console.print.call_args_list)

    @patch('cai.repl.commands.cost.GLOBAL_USAGE_TRACKER')
    def test_handle_reset_cancelled(self, mock_global_tracker, cost_command, 
                                   mock_console, temp_usage_file):
        """Test handle_reset when user cancels."""
        mock_global_tracker.enabled = True
        mock_global_tracker.get_summary.return_value = {
            "global_totals": {
                "total_cost": 1.234567,
                "total_sessions": 10
            }
        }
        
        # Mock user input for cancellation
        mock_console.input.return_value = "no"
        
        with patch('cai.repl.commands.cost.Path') as mock_path:
            mock_path.home.return_value = Path(tempfile.gettempdir())
            mock_usage_file = MagicMock()
            mock_usage_file.exists.return_value = True
            mock_path.return_value.__truediv__.return_value.__truediv__.return_value = mock_usage_file
            
            result = cost_command.handle_reset()
            assert result is True
            
            # Verify file was NOT deleted
            mock_usage_file.unlink.assert_not_called()
            
            # Verify cancellation message
            mock_console.print.assert_any_call("[yellow]Reset cancelled[/yellow]")

    @patch('cai.repl.commands.cost.GLOBAL_USAGE_TRACKER')
    def test_tracking_disabled(self, mock_global_tracker, cost_command, mock_console):
        """Test behavior when tracking is disabled."""
        mock_global_tracker.enabled = False
        
        # Test all subcommands
        for subcommand in ["models", "daily", "sessions", "reset"]:
            mock_console.reset_mock()
            result = cost_command.handle([subcommand])
            assert result is True
            mock_console.print.assert_any_call("[yellow]Usage tracking is disabled[/yellow]")

    def test_get_session_summary(self, cost_command):
        """Test _get_session_summary method."""
        with patch('cai.repl.commands.cost.COST_TRACKER') as mock_tracker:
            mock_tracker.session_total_cost = 0.5
            mock_tracker.current_agent_total_cost = 0.2
            mock_tracker.current_agent_input_tokens = 1000
            mock_tracker.current_agent_output_tokens = 500
            
            summary = cost_command._get_session_summary()
            
            assert "$0.500000" in summary
            assert "$0.200000" in summary
            assert "1,000" in summary
            assert "500" in summary
            assert "1,500" in summary  # Total tokens

    def test_get_global_summary_disabled(self, cost_command):
        """Test _get_global_summary when tracking is disabled."""
        with patch('cai.repl.commands.cost.GLOBAL_USAGE_TRACKER') as mock_tracker:
            mock_tracker.enabled = False
            
            summary = cost_command._get_global_summary()
            
            assert "Usage tracking is disabled" in summary
            assert "CAI_DISABLE_USAGE_TRACKING=false" in summary

    def test_show_top_models_mini(self, cost_command, mock_console):
        """Test _show_top_models_mini method."""
        with patch('cai.repl.commands.cost.GLOBAL_USAGE_TRACKER') as mock_tracker:
            mock_tracker.enabled = True
            mock_tracker.get_summary.return_value = {
                "top_models": [
                    ("gpt-4", 1.0),
                    ("claude-3", 0.5),
                    ("gpt-3.5", 0.25)
                ]
            }
            
            cost_command._show_top_models_mini()
            
            # Verify output
            assert mock_console.print.called
            print_calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("Top Models by Cost" in str(call) for call in print_calls)
            assert any("gpt-4" in str(call) for call in print_calls)
            assert any("$1.0000" in str(call) for call in print_calls)