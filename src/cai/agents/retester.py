"""Retester Agent for vulnerability verification and triage"""
import os
from dotenv import load_dotenv
from cai.sdk.agents import Agent, OpenAIChatCompletionsModel
from openai import AsyncOpenAI
from cai.util import load_prompt_template, create_system_prompt_renderer
from cai.tools.reconnaissance.generic_linux_command import (  # pylint: disable=import-error # noqa: E501
    generic_linux_command
)
from cai.tools.web.search_web import (  # pylint: disable=import-error # noqa: E501
    make_google_search
)
from cai.tools.reconnaissance.exec_code import (  # pylint: disable=import-error # noqa: E501
    execute_code
)


load_dotenv()

# Load the triage agent system prompt
retester_system_prompt = load_prompt_template("prompts/system_triage_agent.md")

tools = [
    generic_linux_command,
    execute_code
]

if os.getenv('GOOGLE_SEARCH_API_KEY') and os.getenv('GOOGLE_SEARCH_CX'):
    tools.append(make_google_search)

retester_agent = Agent(
    name="Retester Agent",
    instructions=create_system_prompt_renderer(retester_system_prompt),
    description="""Agent that specializes in vulnerability verification and 
                   triage. Expert in determining exploitability and 
                   eliminating false positives.""",
    tools=tools,
    model=OpenAIChatCompletionsModel(
        model=os.getenv('CAI_MODEL', "alias0"),
        openai_client=AsyncOpenAI(),
    )
)




