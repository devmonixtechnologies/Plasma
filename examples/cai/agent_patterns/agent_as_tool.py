"""
Agents as Tools Example.

This module demonstrates how to embed one agent as a tool within another agent's workflow.
An agent-as-tool operates independently on its provided input —without access to prior conversation history or "taking over" 
the conversation — completes its specific task, and returns the result to the calling (parent) agent.
"""
from __future__ import annotations
import os
import json
import random
import asyncio
from openai import AsyncOpenAI
from cai.sdk.agents import function_tool
from cai.tools.common import run_command
from cai.sdk.agents import Agent, OpenAIChatCompletionsModel, HandoffInputData, Runner, function_tool, handoff, trace, ItemHelpers, MessageOutputItem
from cai.sdk.agents.extensions import handoff_filters
 


@function_tool
def execute_cli_command(command: str) -> str:
    return run_command(command)


flag_discriminator = Agent(
    name="Flag discriminator",
    description="Agent focused on extracting the flag from the output",
    instructions="You are an agent tailored to extract the flag from a given output.",
    model=OpenAIChatCompletionsModel(
        model=os.getenv('CAI_MODEL', "qwen2.5:14b"),
        openai_client=AsyncOpenAI(),
    ), 
    handoff_description = "Agent focused on extracting the flag from the output" 
)

# We'll use this variable to check if the flag_discriminator agent is used
flag_discriminator_used = False

# Wrap the as_tool method to set the flag when used
def flag_discriminator_as_tool(*args, **kwargs):
    global flag_discriminator_used
    flag_discriminator_used = True
    return flag_discriminator._as_tool(*args, **kwargs)

# Patch the as_tool method
flag_discriminator._as_tool = flag_discriminator.as_tool
flag_discriminator.as_tool = flag_discriminator_as_tool

ctf_agent = Agent(
    name="CTF agent",
    description="Agent focused on conquering security challenges",
    instructions="You are a Cybersecurity expert Leader facing a CTF",
    tools=[
        execute_cli_command, 
        flag_discriminator.as_tool(
            tool_name="find_flag",
            tool_description ="Find flag in output text" 
        )
    ],
    model=OpenAIChatCompletionsModel(
        model= os.getenv('CAI_MODEL', "qwen2.5:14b"),
        openai_client=AsyncOpenAI(),
    )
)

# Main function to execute the workflow
async def main():

    result = await Runner.run(
            ctf_agent,
            input= [
                {"content": "Here is some output from a task. Find the flag: nhwitm flag{1234} mlsk. And returns only the flag", "role": "user"}
            ],
    )

    for item in result.new_items:
        if isinstance(item, MessageOutputItem):
            text = ItemHelpers.text_message_output(item)
            if text:
                print(f"Final step: {text}")

    # Print whether the flag_discriminator agent was used
    if flag_discriminator_used:
        print("Flag discriminator agent was used.")
    else:
        print("Flag discriminator agent was NOT used.")

if __name__ == "__main__":
    asyncio.run(main())