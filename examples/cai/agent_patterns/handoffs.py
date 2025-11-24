"""
In many situations, you have specialized sub-agents that handle specific tasks. You can use handoffs to route the task to the right agent.
"""
from __future__ import annotations
import os
import json
import random
import asyncio
from openai import AsyncOpenAI
from cai.sdk.agents import function_tool
from cai.tools.common import run_command
from cai.sdk.agents import Agent, OpenAIChatCompletionsModel, HandoffInputData, Runner, function_tool, handoff, trace
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
    ) 
    #handoff_description = "Agent focused on extracting the flag from the output" 
)

ctf_agent = Agent(
    name="CTF agent",
    description="Agent focused on conquering security challenges",
    instructions="You are a Cybersecurity expert Leader facing a CTF",
    tools=[
        execute_cli_command,
    ],
    model=OpenAIChatCompletionsModel(
        model= os.getenv('CAI_MODEL', "qwen2.5:14b"),
        openai_client=AsyncOpenAI(),
    ), 
    handoffs = [flag_discriminator]
)


# Complex way to do a handoff
async def invoke_flag_discriminator(context: RunContextWrapper[Any], args: str="") -> Agent:
    """
    This function is called when we need to hand off the task to the flag_discriminator.
    """
    # Check if args is empty
    if not args:
        print("No input provided.")
    else:
        print("Input provided, processing...")
    print(f"Passing args to flag_discriminator: {args}")
    
    # Return the agent (flag_discriminator) that will handle extracting the flag
    return flag_discriminator

# input_filter: can be used for additional data filtering during the handoff
flag_discriminator_complex_handoff = handoff(
    agent=flag_discriminator,
    input_filter = invoke_flag_discriminator
)


ctf_agent.handoffs.append(flag_discriminator_complex_handoff)

# Main function to execute the workflow
async def main():
    # Trace the entire run as a single workflow
    with trace(workflow_name="CTF Workflow"):
        # Step 1: Execute a command with the CTF agent
        result = await Runner.run(ctf_agent, input="List all files in the current directory")

        # Step 2: Ask an additional question for calling the Flag Discriminator agent
        result = await Runner.run(
            ctf_agent,
            input=result.to_input_list() + [
                {"content": "Here is some output from a task. The first file is the name of the flag", "role": "user"}
            ],
        )

    for message in result.to_input_list():
        print(json.dumps(message, indent=2))

if __name__ == "__main__":

    asyncio.run(main())