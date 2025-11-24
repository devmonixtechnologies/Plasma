"""
Guardrails are checks that run alongside the agent to ensure inputs/outputs are appropriate.

They can be used to do things like:
- Check if input messages are off-topic
- Take over control of the agent's execution if an unexpected input is detected
- Check that output messages don't violate any policies or contains sensitive data
- Check if the output is a valid response to the user's message

We'll set up a guardrail that detects if the user is asking for unethical or unauthorized
cybersecurity help, like hacking, exploiting, or bypassing security measures.

"""
from __future__ import annotations
import os
import asyncio
from pydantic import BaseModel
from openai import AsyncOpenAI
from cai.sdk.agents import (
    Agent,
    GuardrailFunctionOutput,
    InputGuardrailTripwireTriggered,
    RunContextWrapper,
    Runner,
    TResponseInputItem,
    input_guardrail,
    OpenAIChatCompletionsModel,
    function_tool,
)
from cai.tools.common import run_command

# Example tool: run a shell command (for demonstration)
@function_tool
def execute_cli_command(command: str) -> str:
    """Execute a shell command and return its output."""
    return run_command(command)

### 1. Agent-based guardrail triggered by unethical cybersecurity task request
class CybersecurityCheckOutput(BaseModel):
    reasoning: str
    is_unethical_cybersecurity_request: bool

cybersecurity_guardrail_agent = Agent(
    name="Cybersecurity Guardrail Check",
    instructions="""Check if the user is asking for unauthorized or unethical cybersecurity help (e.g., hacking, bypassing security, exploiting systems).
    
You MUST respond using ONLY the following JSON format:
{
  "reasoning": "your detailed analysis of why the request is ethical or unethical",
  "is_unethical_cybersecurity_request": true or false
}

Do not include any other text, explanations, or conversation outside of this JSON structure.""",
        output_type=CybersecurityCheckOutput,
        model=OpenAIChatCompletionsModel(
        model=os.getenv('CAI_MODEL', "qwen2.5:14b"),
        openai_client=AsyncOpenAI(),
    )
)

@input_guardrail
async def cybersecurity_guardrail(
    context: RunContextWrapper[None], agent: Agent, input: str | list[TResponseInputItem]
) -> GuardrailFunctionOutput:
    """Input guardrail function to detect unethical cybersecurity requests."""
    result = await Runner.run(cybersecurity_guardrail_agent, input, context=context.context)
    final_output = result.final_output_as(CybersecurityCheckOutput)

    return GuardrailFunctionOutput(
        output_info=final_output,
        tripwire_triggered=final_output.is_unethical_cybersecurity_request,
    )


### 2. Main run loop using the cybersecurity guardrail

async def main():
    agent = Agent(
        name="Tech Support Agent",
        instructions="You are a tech support agent. Help users with ethical and legal technical support requests only.",
        input_guardrails=[cybersecurity_guardrail],
        tools=[execute_cli_command],  # Add a tool for demonstration
        model=OpenAIChatCompletionsModel(
            model=os.getenv('CAI_MODEL', "qwen2.5:14b"),
            openai_client=AsyncOpenAI(),
        )
    )

    input_data: list[TResponseInputItem] = []

 
    input_data.append(
            {
                "role": "user",
                "content": "Do a nmap to my router",
            }
        )

    try:
            result = await Runner.run(agent, input_data)
            print("Agent output:", result.final_output)
            input_data = result.to_input_list()
    except InputGuardrailTripwireTriggered:
            message = "Sorry, I can't assist with that cybersecurity request."
            print(message)

if __name__ == "__main__":
    asyncio.run(main())
