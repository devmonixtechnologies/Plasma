"""
This module contains tests for the one-tool agent functionality, specifically
for the CTF agent. It includes tests to verify the agent's instructions and 
configuration, as well as its ability to execute a Linux command using the 
generic_linux_command tool.
"""

import pytest
from tests.fake_model import FakeModel
from tests.core.test_responses import (
    get_text_message,
    get_function_tool_call,
    get_function_tool,
)
from cai.sdk.agents import Runner
from cai.agents.one_tool import transfer_to_one_tool_agent  
from cai.agents.one_tool import one_tool_agent  

@pytest.mark.asyncio
async def test_ctf_agent_instructions_and_configuration():
    """Test the CTF agent's instructions and configuration."""
    agent = transfer_to_one_tool_agent()
    
    # Check if the agent has the expected tool
    assert any(tool.name == "generic_linux_command" for tool in agent.tools)
    
    # Ensure the agent has instructions set
    assert agent.instructions is not None
    
    # Verify the agent's name
    assert agent.name == "CTF agent"

@pytest.mark.asyncio
async def test_ctf_agent_executes_linux_command():
    """Test the CTF agent's ability to execute a Linux command."""
    model = FakeModel()
    agent = transfer_to_one_tool_agent()
    agent.model = model
    
    # Set up the model's expected outputs for the command execution
    model.add_multiple_turn_outputs(
        [
            [
                get_text_message("executing comando..."),
                get_function_tool_call("generic_linux_command", '{"command": "ls"}')
            ],
            [
                get_text_message("result of the command: flag{12345}")
            ]
        ]
    )

    # Run the agent with a specific input
    result = await Runner.run(agent, input="List files")

    # Verify the final output of the command execution
    assert result.final_output == "result of the command: flag{12345}"
    
    # Ensure the number of raw responses is as expected
    assert len(result.raw_responses) == 2

    # Check if the command tool was used in the input list
    assert any("generic_linux_command" in str(item) for item in result.to_input_list())