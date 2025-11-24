import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from cai.sdk.agents import OpenAIChatCompletionsModel,Agent,Runner
from cai.sdk.agents import set_default_openai_client, set_tracing_disabled
from openai.types.responses import ResponseTextDeltaEvent

# Load environment variables from .env file
load_dotenv()

external_client = AsyncOpenAI(
    base_url = os.getenv('LITELLM_BASE_URL', 'http://localhost:4000'),
    api_key=os.getenv('LITELLM_API_KEY', 'key'))

set_default_openai_client(external_client)
set_tracing_disabled(True)

# llm_model=os.getenv('LLM_MODEL', 'gpt-4o')
# llm_model=os.getenv('LLM_MODEL', 'claude-3-7')
llm_model=os.getenv('LLM_MODEL', 'qwen2.5:14b')

# For Qwen models, we need to skip system instructions as they're not supported
instructions = None if "qwen" in llm_model.lower() else "You are a helpful assistant"

agent = Agent(
    name="Assistant", 
    instructions=instructions,
    model=OpenAIChatCompletionsModel(
        model=llm_model,
        openai_client=external_client,
    )
)


def run_sync_haiku():
    result = Runner.run_sync(agent, "Write a haiku about recursion in programming.")
    print(result.final_output)


async def stream_jokes():
    result = Runner.run_streamed(agent, input="Please tell me 5 jokes.")
    async for event in result.stream_events():
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
            print(event.data.delta, end="", flush=True)


########################################################

# async
# import asyncio
# asyncio.run(stream_jokes())

# sync
run_sync_haiku()