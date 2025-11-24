"""
First prototype of a reasoner agent

using reasoner as a tool call

support meta agent may better @cai.sdk.agents.meta.reasoner_support
"""
from cai.tools.misc.reasoning import think
from cai.sdk.agents import Agent, OpenAIChatCompletionsModel  # pylint: disable=import-error
from openai import AsyncOpenAI
from cai.util import load_prompt_template, create_system_prompt_renderer
import os

thought_agent_system_prompt = load_prompt_template("prompts/system_thought_router.md")

# Thought Process Agent for analysis and planning
thought_agent = Agent(
    name="ThoughtAgent",
    model=OpenAIChatCompletionsModel(
        model=os.getenv('CAI_MODEL', "alias0"),
        openai_client=AsyncOpenAI(),
    ),
    description="""Agent focused on analyzing and planning the next steps
                   in a security assessment or CTF challenge.""",
    instructions=create_system_prompt_renderer(thought_agent_system_prompt),
    tools=[think],
)
