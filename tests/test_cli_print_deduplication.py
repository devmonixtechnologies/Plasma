"""Test cli_print_tool_output deduplication logic with CAI_STREAM=false"""

import os
import time
import pytest
from unittest.mock import patch
from cai.util import cli_print_tool_output


@pytest.fixture(autouse=True)
def reset_cli_print_state():
    """Reset cli_print_tool_output state before each test"""
    # Clear any existing state
    if hasattr(cli_print_tool_output, "_displayed_commands"):
        cli_print_tool_output._displayed_commands.clear()
    if hasattr(cli_print_tool_output, "_command_display_times"):
        cli_print_tool_output._command_display_times.clear()
    if hasattr(cli_print_tool_output, "_seen_calls"):
        cli_print_tool_output._seen_calls.clear()
    if hasattr(cli_print_tool_output, "_streaming_sessions"):
        cli_print_tool_output._streaming_sessions.clear()
    yield


def test_deduplication_with_streaming_disabled(capsys):
    """Test that duplicate suppression works correctly when CAI_STREAM=false"""
    os.environ["CAI_STREAM"] = "false"
    
    # First call should display
    cli_print_tool_output(
        tool_name="generic_linux_command",
        args={"command": "ls -la"},
        output="test output",
        streaming=False
    )
    
    captured = capsys.readouterr()
    assert "test output" in captured.out
    assert "generic_linux_command" in captured.out
    
    # For this test, we need to manually set the display time to be recent
    # because Rich rendering takes over 1 second
    command_key = "generic_linux_command:ls -la"
    if hasattr(cli_print_tool_output, "_command_display_times"):
        # Set the display time to be very recent (0.1 seconds ago)
        cli_print_tool_output._command_display_times[command_key] = time.time() - 0.1
    
    # Immediate duplicate should be suppressed
    cli_print_tool_output(
        tool_name="generic_linux_command",
        args={"command": "ls -la"},
        output="test output",
        streaming=False
    )
    
    captured = capsys.readouterr()
    # The output should be empty since we're suppressing the duplicate
    assert captured.out == ""  # Should be empty, duplicate suppressed
    
    # After delay, same command should display again
    time.sleep(0.6)
    cli_print_tool_output(
        tool_name="generic_linux_command",
        args={"command": "ls -la"},
        output="test output 2",
        streaming=False
    )
    
    captured = capsys.readouterr()
    assert "test output 2" in captured.out
    assert "generic_linux_command" in captured.out


def test_deduplication_with_streaming_enabled(capsys):
    """Test that duplicate suppression works correctly when CAI_STREAM=true"""
    os.environ["CAI_STREAM"] = "true"
    
    # First call should display
    cli_print_tool_output(
        tool_name="generic_linux_command",
        args={"command": "pwd"},
        output="test output",
        streaming=False
    )
    
    captured = capsys.readouterr()
    assert "test output" in captured.out
    
    # Duplicate should always be suppressed when streaming is enabled
    cli_print_tool_output(
        tool_name="generic_linux_command",
        args={"command": "pwd"},
        output="test output",
        streaming=False
    )
    
    captured = capsys.readouterr()
    assert captured.out == ""  # Should be empty, duplicate suppressed


def test_different_commands_always_display(capsys):
    """Test that different commands are not considered duplicates"""
    os.environ["CAI_STREAM"] = "false"
    
    # First command
    cli_print_tool_output(
        tool_name="generic_linux_command",
        args={"command": "ls"},
        output="output 1",
        streaming=False
    )
    
    captured = capsys.readouterr()
    assert "output 1" in captured.out
    
    # Different command should display
    cli_print_tool_output(
        tool_name="generic_linux_command",
        args={"command": "pwd"},
        output="output 2",
        streaming=False
    )
    
    captured = capsys.readouterr()
    assert "output 2" in captured.out


def test_empty_output_always_suppressed(capsys):
    """Test that empty output is always suppressed"""
    os.environ["CAI_STREAM"] = "false"
    
    cli_print_tool_output(
        tool_name="generic_linux_command",
        args={"command": "test"},
        output="",
        streaming=False
    )
    
    captured = capsys.readouterr()
    assert captured.out == ""  # Empty output should not display


def test_parallel_mode_deduplication(capsys):
    """Test deduplication in parallel mode with agent context"""
    os.environ["CAI_STREAM"] = "false"
    
    # Simulate parallel agent execution with agent context
    token_info_p1 = {
        "agent_name": "TestAgent",
        "agent_id": "P1",
        "interaction_counter": 1
    }
    
    token_info_p2 = {
        "agent_name": "TestAgent",
        "agent_id": "P2",
        "interaction_counter": 1
    }
    
    # Same command from different parallel agents should both display
    cli_print_tool_output(
        tool_name="generic_linux_command",
        args={"command": "ls"},
        output="output from P1",
        token_info=token_info_p1,
        streaming=False
    )
    
    captured = capsys.readouterr()
    assert "output from P1" in captured.out
    
    cli_print_tool_output(
        tool_name="generic_linux_command",
        args={"command": "ls"},
        output="output from P2",
        token_info=token_info_p2,
        streaming=False
    )
    
    captured = capsys.readouterr()
    assert "output from P2" in captured.out  # Different agent context, should display