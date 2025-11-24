""" 
This example demonstrates how to use handoffs and tools together

"""

from cai.sdk.agents import Agent, OpenAIChatCompletionsModel
from openai import AsyncOpenAI
from cai.sdk.agents import handoff, function_tool, trace
from cai.sdk.agents import Runner
from cai.tools.common import run_command
from cai.sdk.agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
import os
import asyncio

@function_tool
def execute_cli_command(command: str) -> str:
    """Execute a command-line command and return its output."""
    return run_command(command)


# Create the Flag Discriminator Agent (terminal agent in the chain)
flag_discriminator = Agent(
    name="Flag Discriminator Agent",
    description="Agent specialized in verifying if content matches the expected flag format in CTF challenges",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are an expert at identifying CTF flags. The final flag is the first file of a -ls command. You return the flag with this format: flag{{filename}}""",
    handoff_description="Specialized agent in determining whether the content corresponds to the flag of the CTF challenge",
    handoffs=[],
    model=OpenAIChatCompletionsModel(
        model=os.getenv('CAI_MODEL', "qwen2.5:72b"),
        openai_client=AsyncOpenAI(),
    )
)

# Create the Bash Agent (can hand off to Flag Discriminator)
bash_agent = Agent(
    name="Bash Agent",
    description="Agent specialized in Bash commands and Linux operations",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a Bash and Linux expert. Use your knowledge to navigate the file system and execute commands.
    The final flag is the first element listed in the directory. 
    When you find the name of the file, handoff to the Flag Discriminator Agent for verification.""",
    tools=[execute_cli_command],
    handoffs=[handoff(flag_discriminator)],
    handoff_description="Specialized agent in Bash commands and Linux operations",
    model=OpenAIChatCompletionsModel(
        model=os.getenv('CAI_MODEL', "qwen2.5:14b"),
        openai_client=AsyncOpenAI(),
    )
)

# Create the Crypto Agent
crypto_agent = Agent(
    name="Cryptography Agent",
    description="Agent specialized in cryptography, ciphers, and encoding/decoding",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a cryptography expert. Help decipher and decode encrypted messages or files.""",
    tools=[execute_cli_command],
    handoffs=[],
    handoff_description="Specialized agent in cryptography and codebreaking",
    model=OpenAIChatCompletionsModel(
        model=os.getenv('CAI_MODEL', "qwen2.5:14b"),
        openai_client=AsyncOpenAI(),
    )
)

# Create the Cybersecurity Lead Agent (can hand off to both Bash and Crypto)
cybersecurity_lead = Agent(
    name="Cybersecurity Lead Agent",
    description="Lead agent focused on conquering security challenges by delegating to specialist agents",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    You are a Cybersecurity expert Leader facing cybersecurity challenges. 
    - Hand off to the Bash Agent when you need to execute Linux commands or navigate the file system.
    - Hand off to the Cryptography Agent when you encounter encrypted data or codes that need deciphering.""",
    tools=[execute_cli_command],
    handoffs=[
        handoff(bash_agent),
        handoff(crypto_agent)
    ],
    handoff_description="Lead agent in cybersecurity operations",
    model=OpenAIChatCompletionsModel(
        model=os.getenv('CAI_MODEL', "qwen2.5:14b"),
        openai_client=AsyncOpenAI(),
    )
)


async def main():
    # Trace the entire run as a single workflow
    with trace(workflow_name="CTF Workflow"):
        # Run with cybersecurity_lead directly
        result = await Runner.run(cybersecurity_lead, "List directories to find the flag")

    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())