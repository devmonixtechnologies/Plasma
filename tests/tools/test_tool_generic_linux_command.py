import os
import pytest
import json
import asyncio
from unittest.mock import MagicMock

# Set test environment variables to avoid OpenAI client initialization errors
os.environ["OPENAI_API_KEY"] = "test_key_for_ci_environment"

from cai.tools.reconnaissance.generic_linux_command import generic_linux_command
from cai.sdk.agents import RunContextWrapper


@pytest.mark.asyncio
async def test_generic_linux_command_echo():
    """Test the execution of echo command using generic_linux_command."""
    args = {"command": "echo 'hello'"}
    result = await generic_linux_command.on_invoke_tool(
        RunContextWrapper(None), json.dumps(args)
    )
    assert result.strip() == 'hello'


@pytest.mark.asyncio
async def test_generic_linux_command_ls():
    """Test the execution of ls command using generic_linux_command."""
    args = {"command": "ls -l"}
    result = await generic_linux_command.on_invoke_tool(
        RunContextWrapper(None), json.dumps(args)
    )
    # Check that the output contains typical ls -l indicators
    assert "total" in result or "drwx" in result or "-rw" in result


@pytest.mark.asyncio
async def test_generic_linux_command_invalid_command():
    """Test handling of invalid command using generic_linux_command."""
    args = {"command": "invalid_command_xyz123"}
    result = await generic_linux_command.on_invoke_tool(
        RunContextWrapper(None), json.dumps(args)
    )
    # Check for common error indicators
    assert ("not found" in result.lower() or 
            "command not found" in result.lower() or
            "no such file" in result.lower())


@pytest.mark.asyncio
async def test_generic_linux_command_empty_command():
    """Test handling of empty command using generic_linux_command."""
    args = {"command": ""}
    result = await generic_linux_command.on_invoke_tool(
        RunContextWrapper(None), json.dumps(args)
    )
    assert "Error: No command provided" in result


@pytest.mark.asyncio
async def test_generic_linux_command_session_list():
    """Test session list functionality using generic_linux_command."""
    args = {"command": "session list"}
    result = await generic_linux_command.on_invoke_tool(
        RunContextWrapper(None), json.dumps(args)
    )
    assert "No active sessions" in result or "Active sessions:" in result


@pytest.mark.asyncio
async def test_generic_linux_command_env_info():
    """Test environment info functionality using generic_linux_command."""
    args = {"command": "env info"}
    result = await generic_linux_command.on_invoke_tool(
        RunContextWrapper(None), json.dumps(args)
    )
    assert "Current Environment:" in result
    assert "CTF Environment:" in result
    assert "Container:" in result
    assert "SSH:" in result
    assert "Workspace:" in result


@pytest.mark.asyncio
async def test_generic_linux_command_interactive_flag():
    """Test interactive flag functionality using generic_linux_command."""
    # Test with interactive=True but a simple command
    args = {"command": "echo 'test'", "interactive": True}
    result = await generic_linux_command.on_invoke_tool(
        RunContextWrapper(None), json.dumps(args)
    )
    # Should still work, just might have different session handling
    assert "test" in result


@pytest.mark.asyncio
async def test_generic_linux_command_with_session_id():
    """Test session_id parameter using generic_linux_command."""
    # Test with a non-existent session_id
    args = {"command": "echo 'test'", "session_id": "nonexistent123"}
    result = await generic_linux_command.on_invoke_tool(
        RunContextWrapper(None), json.dumps(args)
    )
    # Should handle gracefully - either execute or give session error
    assert isinstance(result, str)