"""
A common tactic is to break down a task into a series of smaller steps. 
Each task can be performed by an agent, and the output of one agent is used as input to the next
try stream and normal
"""
import os
import sys
import time
import asyncio
from cai.sdk.agents import Runner, Agent, OpenAIChatCompletionsModel, set_tracing_disabled
from openai import AsyncOpenAI
from cai.sdk.agents import function_tool
from cai.tools.common import run_command 


@function_tool
def execute_cli_command(command: str) -> str:
    return run_command(command)


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
    )
)
async def main():
    result = await Runner.run(ctf_agent, "List the files in the current directory?")
    print("\nAgent response:")
    print(result.final_output)

async def main_streamed():
    print("\nAgent response (streaming):")
    result = Runner.run_streamed(ctf_agent, "List the files in the current directory?")

    # Process the streaming response events
    event_count = 0
    start_time = time.time()

    # Process the streaming response
    async for event in result.stream_events():
        event_count += 1
        # Add a small delay to allow the streaming panel to update properly
        await asyncio.sleep(0.01)
        
        # # Print a progress indicator
        # if event_count % 10 == 0:
        #     elapsed = time.time() - start_time
        #     sys.stdout.write(f"\rProcessed {event_count} events in {elapsed:.1f} seconds...")
        #     sys.stdout.flush()
    
    # Clear the progress line
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()

if __name__ == "__main__":
    set_tracing_disabled(True)
    asyncio.run(main()) 
    asyncio.run(main_streamed()) 