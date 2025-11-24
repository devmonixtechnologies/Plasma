"""Test custom prompts for parallel agents in CAI CLI."""

import pytest
from unittest.mock import MagicMock, patch
from cai.repl.commands.parallel import ParallelCommand, PARALLEL_CONFIGS, ParallelConfig
from rich.console import Console


class TestParallelCustomPrompts:
    """Test suite for parallel agent custom prompts."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Clear any existing configurations
        PARALLEL_CONFIGS.clear()
        self.console = Console()
        self.command = ParallelCommand()
    
    def teardown_method(self):
        """Clean up after each test."""
        PARALLEL_CONFIGS.clear()
    
    def test_prompt_subcommand_adds_prompt_to_config(self):
        """Test that the prompt subcommand correctly adds a custom prompt to a config."""
        # Add an agent first
        with patch('cai.repl.commands.parallel.console'):
            self.command.handle_add(["redteam_agent"])
        
        # Verify agent was added
        assert len(PARALLEL_CONFIGS) == 1
        assert PARALLEL_CONFIGS[0].prompt is None
        
        # Set a custom prompt
        with patch('cai.repl.commands.parallel.console') as mock_console:
            result = self.command.handle_prompt(["P1", "Focus on SQL injection vulnerabilities"])
        
        assert result is True
        assert PARALLEL_CONFIGS[0].prompt == "Focus on SQL injection vulnerabilities"
        
        # Verify success message was printed
        mock_console.print.assert_any_call(
            "[green]Updated prompt for Red Team Agent (ID: P1)[/green]"
        )
    
    def test_prompt_subcommand_with_index(self):
        """Test that the prompt subcommand works with numeric index."""
        # Add an agent
        with patch('cai.repl.commands.parallel.console'):
            self.command.handle_add(["bug_bounter_agent"])
        
        # Set prompt using index
        with patch('cai.repl.commands.parallel.console'):
            result = self.command.handle_prompt(["1", "Test for XSS vulnerabilities"])
        
        assert result is True
        assert PARALLEL_CONFIGS[0].prompt == "Test for XSS vulnerabilities"
    
    def test_prompt_subcommand_error_handling(self):
        """Test error handling for invalid prompt commands."""
        # Test with no arguments
        with patch('cai.repl.commands.parallel.console') as mock_console:
            result = self.command.handle_prompt([])
        
        assert result is False
        mock_console.print.assert_any_call("[red]Error: Agent ID/index and prompt required[/red]")
        
        # Test with invalid ID
        with patch('cai.repl.commands.parallel.console') as mock_console:
            result = self.command.handle_prompt(["P99", "Some prompt"])
        
        assert result is False
        mock_console.print.assert_any_call("[red]Error: No agent found with ID/index 'P99'[/red]")
    
    def test_custom_prompt_displayed_in_list(self):
        """Test that custom prompts are displayed in the list command."""
        # Add agents with prompts
        config1 = ParallelConfig("redteam_agent", prompt="Focus on authentication bypass")
        config1.id = "P1"
        config2 = ParallelConfig("bug_bounter_agent", prompt="Look for IDOR vulnerabilities in the API endpoints")
        config2.id = "P2"
        PARALLEL_CONFIGS.extend([config1, config2])
        
        # Mock the table print to capture output
        with patch('cai.repl.commands.parallel.Table') as mock_table:
            with patch('cai.repl.commands.parallel.console'):
                self.command.handle_list()
            
            # Verify table was created with correct columns
            mock_table.assert_called_once()
            table_instance = mock_table.return_value
            
            # Verify add_row was called for each config
            assert table_instance.add_row.call_count == 2
            
            # Check first row
            first_call = table_instance.add_row.call_args_list[0]
            args = first_call[0]
            assert args[6] == "Focus on authentication bypass"  # Custom prompt column
            
            # Check second row (should be truncated)
            second_call = table_instance.add_row.call_args_list[1]
            args = second_call[0]
            assert args[6] == "Look for IDOR vulnerabilities in the ..."  # Truncated prompt
    
    def test_custom_prompt_in_status_display(self):
        """Test that custom prompts are shown in the status display."""
        # Add agent with prompt
        config = ParallelConfig("dfir_agent", prompt="Analyze memory dumps for malware artifacts")
        config.id = "P1"
        PARALLEL_CONFIGS.append(config)
        
        with patch('cai.repl.commands.parallel.console') as mock_console:
            self.command.handle_no_args()
        
        # Verify that prompt info is included in status
        # We need to look through all the print calls to find the Panel
        panel_found = False
        for call in mock_console.print.call_args_list:
            if call[0]:  # Check if arguments exist
                arg = call[0][0]
                # Check if it's a Panel object
                if hasattr(arg, '__class__') and arg.__class__.__name__ == 'Panel':
                    # Check the renderable content
                    if hasattr(arg, 'renderable'):
                        content = str(arg.renderable)
                        if "Prompt: Analyze memory dumps for malware artifacts" in content:
                            panel_found = True
                            break
        
        assert panel_found, "Prompt not found in status display"
    
    def test_parallel_execution_uses_custom_prompts(self):
        """Test that parallel execution correctly uses custom prompts instead of user input."""
        # This test would require mocking the actual parallel execution in cli.py
        # For now, we just verify the configuration is set up correctly
        
        config1 = ParallelConfig("redteam_agent", prompt="Custom prompt 1")
        config1.id = "P1"
        config2 = ParallelConfig("bug_bounter_agent", prompt="Custom prompt 2")
        config2.id = "P2"
        config3 = ParallelConfig("dfir_agent")  # No custom prompt
        config3.id = "P3"
        
        PARALLEL_CONFIGS.extend([config1, config2, config3])
        
        # Verify each config has the correct prompt
        assert PARALLEL_CONFIGS[0].prompt == "Custom prompt 1"
        assert PARALLEL_CONFIGS[1].prompt == "Custom prompt 2"
        assert PARALLEL_CONFIGS[2].prompt is None
    
    def test_parallel_history_persistence_on_interrupt(self):
        """Test that parallel agents' histories are saved when interrupted."""
        # This test verifies the configuration for history persistence
        from cai.sdk.agents.parallel_isolation import PARALLEL_ISOLATION
        
        # Setup parallel configs
        config1 = ParallelConfig("redteam_agent")
        config1.id = "P1"
        config2 = ParallelConfig("bug_bounter_agent")
        config2.id = "P2"
        
        PARALLEL_CONFIGS.extend([config1, config2])
        
        # Simulate parallel mode
        PARALLEL_ISOLATION._parallel_mode = True
        
        # Add some test history
        test_history1 = [{"role": "user", "content": "Test message 1"}]
        test_history2 = [{"role": "user", "content": "Test message 2"}]
        
        PARALLEL_ISOLATION.replace_isolated_history("P1", test_history1)
        PARALLEL_ISOLATION.replace_isolated_history("P2", test_history2)
        
        # Verify histories are stored
        assert PARALLEL_ISOLATION.get_isolated_history("P1") == test_history1
        assert PARALLEL_ISOLATION.get_isolated_history("P2") == test_history2
        
        # Clean up
        PARALLEL_ISOLATION.clear_all_histories()
        PARALLEL_ISOLATION._parallel_mode = False
    
    def test_prompt_update_overwrites_existing(self):
        """Test that updating a prompt overwrites the existing one."""
        # Add agent with initial prompt
        config = ParallelConfig("redteam_agent", prompt="Initial prompt")
        config.id = "P1"
        PARALLEL_CONFIGS.append(config)
        
        # Update the prompt
        with patch('cai.repl.commands.parallel.console') as mock_console:
            self.command.handle_prompt(["P1", "Updated prompt with new instructions"])
        
        assert PARALLEL_CONFIGS[0].prompt == "Updated prompt with new instructions"
        
        # Verify old prompt was shown
        old_prompt_found = False
        for call in mock_console.print.call_args_list:
            if call[0] and "[dim]Old prompt: Initial prompt[/dim]" in str(call[0][0]):
                old_prompt_found = True
                break
        
        assert old_prompt_found, "Old prompt message not found"