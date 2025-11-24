"""
This module demonstrates a deterministic agent pattern for solving CTF (Capture The Flag) challenges using composable AI agents.
The deterministic pattern here involves a fixed, sequential pipeline of agents, each with a well-defined role.
This pattern ensures reproducibility and traceability, as the flow of information and agent responsibilities are strictly defined and do not vary between runs.
"""

import os
import asyncio
from pydantic import BaseModel
from openai import AsyncOpenAI
from cai.sdk.agents import Agent, Runner, OpenAIChatCompletionsModel, function_tool
from cai.tools.common import run_command
from cai.sdk.agents.extensions import handoff_filters

# Function tool to execute CLI command
@function_tool
def execute_cli_command(command: str) -> str:
    return run_command(command)

# Define Flag Discriminator Agent (handles extracting flags from CTF output)
flag_discriminator = Agent(
    name="Flag discriminator",
    description="Agent focused on extracting the flag from the output",
    instructions="You are an agent tailored to extract the flag from a given output.",
    model=OpenAIChatCompletionsModel(
        model=os.getenv('CAI_MODEL', "qwen2.5:14b"),
        openai_client=AsyncOpenAI(),
    )
)

# Define CTF Agent (performs the actual challenge)
ctf_agent = Agent(
    name="CTF agent",
    description="Agent focused on conquering security challenges",
    instructions="You are a Cybersecurity expert Leader facing a CTF",
    tools=[
        execute_cli_command,
    ],
    model=OpenAIChatCompletionsModel(
        model=os.getenv('CAI_MODEL', "qwen2.5:14b"),
        openai_client=AsyncOpenAI(),
    )
)

# Main handler function for CTF process
async def main():

        # Step 1: Execute command in CTF environment
        ctf_result = await Runner.run(ctf_agent, "List directories with a simple ls command, the flag is in flag.txt")

        # Step 2: Pass result to flag discriminator
        flag_discriminator_result = await Runner.run(
            flag_discriminator,
            ctf_result.final_output,
        )

        print(f"Flag found: {flag_discriminator_result.final_output}")

if __name__ == "__main__":
    asyncio.run(main())
