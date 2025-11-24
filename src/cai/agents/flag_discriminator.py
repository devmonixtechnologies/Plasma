"""
CTF Flag Discriminator Agent with test
"""
import os
from cai.sdk.agents import Agent, OpenAIChatCompletionsModel, handoff
from openai import AsyncOpenAI
from cai.agents.one_tool import one_tool_agent

model = os.getenv('CAI_MODEL', "alias0")

# Create OpenAI client with fallback API key to prevent initialization errors
# The actual API key should be set in environment variables or .env file
api_key = os.getenv('OPENAI_API_KEY', 'sk-placeholder-key-for-local-models')

flag_discriminator = Agent(
    name="Flag discriminator",
    description="Agent focused on extracting the flag from the output",
    instructions="""INSTRUCTIONS:
                1. You are an agent tailored to extract the flag from a given output.
                2. ONLY return the flag, nothing else.
                3. Flags can be in any format (not always CTF{...}).
                4. If you do not find a flag, call `ctf_agent` to continue investigating.
                """,
    model=OpenAIChatCompletionsModel(
        model="alias0" if os.getenv('CAI_MODEL') == "o3-mini" else model,
        openai_client=AsyncOpenAI(api_key=api_key),
    ),
    handoffs=[
        handoff(
            agent=one_tool_agent,
            tool_name_override="ctf_agent",
            tool_description_override="Call the CTF agent to continue investigating if no flag is found"
        )
    ]
)

# Transfer Function
def transfer_to_flag_discriminator(**kwargs):  # pylint: disable=W0613
    """Transfer flag discriminator.
    Accepts any keyword arguments but ignores them."""
    return flag_discriminator
