"""
A simple example to test the one_tool agent.

This script demonstrates how to initialize and run the one_tool agent
using Runner.run() with a simple hello message to verify everything
is working correctly.
"""

import os
import asyncio
import json
from dotenv import load_dotenv
from openai import AsyncOpenAI
from cai.sdk.agents import Runner, set_default_openai_client, set_tracing_disabled
from cai.agents import get_agent_by_name
from cai.util import fix_litellm_transcription_annotations, color, cli_print_agent_messages
from cai.sdk.agents.models._openai_shared import set_use_responses_by_default


# Load environment variables
load_dotenv()
#set_tracing_disabled(True) #disable tracing or OPENAI_AGENTS_DISABLE_TRACING=1

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
    
    # Run the agent with a simple test message
    result = await Runner.run(agent, "Hello! Can you list the files in the current directory?")
    
    # Print the result
    print("\nAgent response:")
    print("-" * 40)
    print(result.final_output)
    print("-" * 40)
    print("\nTest completed successfully!")

if __name__ == "__main__":
    asyncio.run(main()) 