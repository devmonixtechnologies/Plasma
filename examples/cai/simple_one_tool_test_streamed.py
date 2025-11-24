"""
A simple example to test the one_tool agent with streaming.

This script demonstrates how to initialize and run the one_tool agent
using Runner.run_streamed() with a simple hello message to verify everything
is working correctly, with streaming output.
"""

import os
import asyncio
import time
import json
import sys
from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types.responses import ResponseTextDeltaEvent
from cai.sdk.agents import Runner, set_default_openai_client
from cai.agents import get_agent_by_name
from cai.util import fix_litellm_transcription_annotations, color
from cai.sdk.agents import Agent, OpenAIChatCompletionsModel
from cai.sdk.agents.models._openai_shared import set_use_responses_by_default

# Load environment variables
load_dotenv()

# NOTE: This is needed when using LiteLLM Proxy Server
#
# external_client = AsyncOpenAI(
#     base_url=os.getenv('LITELLM_BASE_URL', 'http://localhost:4000'),
#     api_key=os.getenv('LITELLM_API_KEY', 'key')
# )
# set_default_openai_client(external_client)

async def main():
    # Apply litellm patch to fix the __annotations__ error
    patch_applied = fix_litellm_transcription_annotations()
    if not patch_applied:
        print(color("Something went wrong patching LiteLLM fix_litellm_transcription_annotations", color="red"))
        
    # Force the use of OpenAIChatCompletionsModel instead of OpenAIResponsesModel
    set_use_responses_by_default(False)
        
    # Get the one_tool agent
    agent = get_agent_by_name("one_tool_agent")

    print(f"Using model: {os.getenv('CAI_MODEL', 'default')}")
    
    # Stream indicator
    print("\nAgent response (streaming):")
    print("-" * 40)
    print("Agent: ", end="", flush=True)
    
    # Run the agent with a simple test message in streaming mode
    result = Runner.run_streamed(agent, "Hello! Can you list the files in the current directory?")

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
    
    
    print("\n" + "-" * 40)
    print("\nTest completed successfully!")

if __name__ == "__main__":
    asyncio.run(main()) 