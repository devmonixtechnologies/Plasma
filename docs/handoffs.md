# Handoffs

Handoffs allow an agent to delegate tasks to another agent. This is particularly useful in scenarios where different agents specialize in distinct areas. For example, a customer support app might have agents that each specifically handle tasks like order status, refunds, FAQs, etc.

Handoffs are represented as tools to the LLM. So if there's a handoff to an agent named `Flag Discriminator`, the tool would be called `transfer_to_flag_discriminator`.

## Creating a handoff

All agents have a [`handoffs`][cai.sdk.agents.agent.Agent.handoffs] param, which can either take an `Agent` directly, or a `Handoff` object that customizes the Handoff.

You can create a handoff using the [`handoff()`][cai.sdk.agents.handoffs.handoff] function provided. This function allows you to specify the agent to hand off to, along with optional overrides and input filters.

### Basic Usage

Here's how you can create a simple handoff:

```python
from cai.sdk.agents import Agent, handoff

crypto_agent = Agent(name="Cryptography Agent")
bash_agent = Agent(name="Bash Agent")

# (1)!
cybersecurity_lead = Agent(name="Cybersecurity Lead Agent", handoffs=[crypto_agent, handoff(bash_agent)])
```



1. You can use the agent directly (as in `crypto_agent`), or you can use the `handoff()` function.

### Customizing handoffs via the `handoff()` function

The [`handoff()`][cai.sdk.agents.handoffs.handoff] function lets you customize things.

-   `agent`: This is the agent to which things will be handed off.
-   `tool_name_override`: By default, the `Handoff.default_tool_name()` function is used, which resolves to `transfer_to_<agent_name>`. You can override this.
-   `tool_description_override`: Override the default tool description from `Handoff.default_tool_description()`
-   `on_handoff`: A callback function executed when the handoff is invoked. This is useful for things like kicking off some data fetching as soon as you know a handoff is being invoked. This function receives the agent context, and can optionally also receive LLM generated input. The input data is controlled by the `input_type` param.
-   `input_type`: The type of input expected by the handoff (optional).
-   `input_filter`: This lets you filter the input received by the next agent. See below for more.

```python
from cai.sdk.agents import Agent, handoff, RunContextWrapper

def on_handoff(ctx: RunContextWrapper[None]):
    print("Handoff called")

agent = Agent(name="My agent")

handoff_obj = handoff(
    agent=agent,
    on_handoff=on_handoff,
    tool_name_override="custom_handoff_tool",
    tool_description_override="Custom description",
)
```

## Handoff inputs

In certain situations, you want the LLM to provide some data when it calls a handoff. For example, imagine a handoff to an "Escalation agent". You might want a reason to be provided, so you can log it.

```python
from pydantic import BaseModel

from cai.sdk.agents import Agent, handoff, RunContextWrapper

class EscalationData(BaseModel):
    reason: str

async def on_handoff(ctx: RunContextWrapper[None], input_data: EscalationData):
    print(f"Escalation agent called with reason: {input_data.reason}")

agent = Agent(name="Escalation agent")

handoff_obj = handoff(
    agent=agent,
    on_handoff=on_handoff,
    input_type=EscalationData,
)
```

## Input filters

When a handoff occurs, it's as though the new agent takes over the conversation, and gets to see the entire previous conversation history. If you want to change this, you can set an [`input_filter`][cai.sdk.agents.handoffs.Handoff.input_filter]. An input filter is a function that receives the existing input via a [`HandoffInputData`][cai.sdk.agents.handoffs.HandoffInputData], and must return a new `HandoffInputData`.

There are some common patterns (for example removing all tool calls from the history), which are implemented for you in [`cai.sdk.agents.extensions.handoff_filters`][]

```python
from cai.sdk.agents import Agent, handoff
from agents.extensions import handoff_filters

network_agent = Agent(name="Network Agent")

handoff_obj = handoff(
    agent=network_agent,
    input_filter=handoff_filters.remove_all_tools, # (1)!
)
```

(1). This will automatically remove all tools from the history when `Network Agent` is called.

## Recommended prompts

To make sure that LLMs understand handoffs properly, we recommend including information about handoffs in your agents. We have a suggested prefix in [`cai.sdk.agents.extensions.handoff_prompt.RECOMMENDED_PROMPT_PREFIX`][], or you can call [`cai.sdk.agents.extensions.handoff_prompt.prompt_with_handoff_instructions`][] to automatically add recommended data to your prompts.

```python
from cai.sdk.agents import Agent
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

billing_agent = Agent(
    name="Phising Agent",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    <Fill in the rest of your prompt here>.""",
)
```

## All-in-one example

```
We will represent the following workflow. You can make it more or less complex, depending on your needs.

                     ┌───────────────────┐
                     │ Cybersecurity     │
User Request ───────►│ Lead Agent        │
                     └───────┬───────────┘
              ┌──────────────┴──────────────┐
              │                             │
    ┌─────────▼────────┐         ┌─────────▼────────┐
    │ Bash Agent       │         │ Crypto Agent     │
    └─────────┬────────┘         └──────────────────┘
              │
    ┌─────────▼────────┐
    │ Flag             │
    │ Discriminator    │
    └──────────────────┘
```


```python
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
```
