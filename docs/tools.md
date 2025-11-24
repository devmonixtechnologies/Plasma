# Tools

Tools let agents take actions: things like fetching data, running code, calling external APIs, and even using a computer. There are three classes of tools in the CAI Agents

-   Hosted tools: these run on LLM servers alongside the AI models. CAI offers some [tools](src/cai/tools)
-   Function calling: these allow you to use any Python function as a tool.
-   Agents as tools: this allows you to use an agent as a tool, allowing Agents to call other agents without handing off to them.

## Hosted tools

CAI offers a few built-in tools when using the [`OpenAIResponsesModel`][cai.sdk.agents.models.openai_responses.OpenAIResponsesModel]. They are in [tools](src/cai/tools) and grouped in 6 major categories inspired by the security kill chain[2]:

 
1. Reconnaissance and weaponization - *reconnaissance*  (crypto, listing, etc)
2. Exploitation - *exploitation*
3. Privilege escalation - *escalation*
4. Lateral movement - *lateral*
5. Data exfiltration - *exfiltration*
6. Command and control - *control*

### C99 Tool

CAI includes integration with the C99.nl API for subdomain discovery and DNS enumeration. This tool is particularly useful for reconnaissance during security assessments.

#### Configuration

To use the C99 tool, you need to set up your API key:

```bash
# In your .env file
C99_API_KEY="your-c99-api-key-here"
```

You can obtain an API key by registering at [C99.nl](https://c99.nl).

#### Usage Example

```python
from cai.sdk.agents import Agent, Runner, OpenAIChatCompletionsModel
from cai.tools.reconnaissance.c99_tool import c99_subdomain_finder
from openai import AsyncOpenAI

recon_agent = Agent(
    name="Recon Agent",
    description="Agent specialized in subdomain discovery",
    instructions="You are a reconnaissance expert focused on DNS enumeration.",
    tools=[
        c99_subdomain_finder,
    ],
    model=OpenAIChatCompletionsModel(
        model="qwen2.5:14b",
        openai_client=AsyncOpenAI(),
    )
)

async def main():
    result = await Runner.run(recon_agent, "Find all subdomains for example.com")
    print(result.final_output)
```

The C99 tool provides comprehensive subdomain enumeration capabilities, making it valuable for the reconnaissance phase of security assessments.

```python
from cai.sdk.agents import Agent, Runner, OpenAIChatCompletionsModel
from cai.tools.reconnaissance.generic_linux_command import generic_linux_command 
from openai import AsyncOpenAI

one_tool_agent = Agent(
    name="CTF agent",
    description="Agent focused on listing directories",
    instructions="You are a Cybersecurity expert Leader facing a CTF challenge.",
    tools=[
        generic_linux_command,
    ],
    model=OpenAIChatCompletionsModel(
        model="qwen2.5:14b",
        openai_client=AsyncOpenAI(),
    )
)
async def main():
    result = await Runner.run(one_tool_agent, "List all directories")
    print(result.final_output)
```

## Function tools

You can use any Python function as a tool. The CAI will setup the tool automatically:

-   The name of the tool will be the name of the Python function (or you can provide a name)
-   Tool description will be taken from the docstring of the function (or you can provide a description)
-   The schema for the function inputs is automatically created from the function's arguments
-   Descriptions for each input are taken from the docstring of the function, unless disabled

We use Python's `inspect` module to extract the function signature, along with [`griffe`](https://mkdocstrings.github.io/griffe/) to parse docstrings and `pydantic` for schema creation.

```python
import json
from typing_extensions import TypedDict, Any
from cai.sdk.agents import Agent, FunctionTool, RunContextWrapper, function_tool, OpenAIChatCompletionsModel
from openai import AsyncOpenAI

class IPAddress(TypedDict):
    ip: str


@function_tool
async def check_ip_reputation(ip_data: IPAddress) -> str:
    """Check if an IP address has a bad reputation.

    Args:
        ip_data: A dictionary with the IP address to check.
    """
    # In a real system, this would query an IP reputation API
    return "malicious" if ip_data["ip"].startswith("192.168") else "clean"


@function_tool(name_override="read_log_file")
def read_log_file(ctx: RunContextWrapper[Any], path: str, directory: str | None = None) -> str:
    """Read the contents of a log file.

    Args:
        path: The path to the log file.
        directory: The optional directory to search in.
    """
    # In a real system, this would read from the filesystem logs
    return "<log file contents: suspicious activity found>"


# Create the cybersecurity agent
agent = Agent(
    name="CyberSecBot",
    tools=[check_ip_reputation, read_log_file],
    model=OpenAIChatCompletionsModel(
        model="qwen2.5:14b",
        openai_client=AsyncOpenAI(),
    )
)

# Display metadata for each available tool
for tool in agent.tools:
    if isinstance(tool, FunctionTool):
        print(tool.name)
        print(tool.description)
        print(json.dumps(tool.params_json_schema, indent=2))
        print()
```

1.  You can use any Python types as arguments to your functions, and the function can be sync or async.
2.  Docstrings, if present, are used to capture descriptions and argument descriptions
3.  Functions can optionally take the `context` (must be the first argument). You can also set overrides, like the name of the tool, description, which docstring style to use, etc.
4.  You can pass the decorated functions to the list of tools.

??? note "Expand to see output"

    ```
    check_ip_reputation
    Check if an IP address has a bad reputation.
    {
      "$defs": {
        "IPAddress": {
          "properties": {
            "ip": {
              "title": "Ip",
              "type": "string"
            }
          },
          "required": [
            "ip"
          ],
          "title": "IPAddress",
          "type": "object",
          "additionalProperties": false
        }
      },
      "properties": {
        "ip_data": {
          "description": "A dictionary with the IP address to check.",
          "properties": {
            "ip": {
              "title": "Ip",
              "type": "string"
            }
          },
          "required": [
            "ip"
          ],
          "title": "IPAddress",
          "type": "object",
          "additionalProperties": false
        }
      },
      "required": [
        "ip_data"
      ],
      "title": "check_ip_reputation_args",
      "type": "object",
      "additionalProperties": false
    }

    read_log_file
    Read the contents of a log file.
    {
      "properties": {
        "path": {
          "description": "The path to the log file.",
          "title": "Path",
          "type": "string"
        },
        "directory": {
          "anyOf": [
            {
              "type": "string"
            },
            {
              "type": "null"
            }
          ],
          "description": "The optional directory to search in.",
          "title": "Directory"
        }
      },
      "required": [
        "path",
        "directory"
      ],
      "title": "read_log_file_args",
      "type": "object",
      "additionalProperties": false
    }
    ```

### Custom function tools

Sometimes, you don't want to use a Python function as a tool. You can directly create a [`FunctionTool`][cai.sdk.agents.tool.FunctionTool] if you prefer. You'll need to provide:

-   `name`
-   `description`
-   `params_json_schema`, which is the JSON schema for the arguments
-   `on_invoke_tool`, which is an async function that receives the context and the arguments as a JSON string, and must return the tool output as a string.

```python
from typing import Any
from pydantic import BaseModel
from cai.sdk.agents import RunContextWrapper, FunctionTool


def do_some_work(data: str) -> str:
    return "done"

class FunctionArgs(BaseModel):
    username: str
    age: int


async def run_function(ctx: RunContextWrapper[Any], args: str) -> str:
    parsed = FunctionArgs.model_validate_json(args)
    return do_some_work(data=f"{parsed.username} is {parsed.age} years old")


tool = FunctionTool(
    name="process_user",
    description="Processes extracted user data",
    params_json_schema=FunctionArgs.model_json_schema(),
    on_invoke_tool=run_function,
)
```

### Automatic argument and docstring parsing

As mentioned before, we automatically parse the function signature to extract the schema for the tool, and we parse the docstring to extract descriptions for the tool and for individual arguments. Some notes on that:

1. The signature parsing is done via the `inspect` module. We use type annotations to understand the types for the arguments, and dynamically build a Pydantic model to represent the overall schema. It supports most types, including Python primitives, Pydantic models, TypedDicts, and more.
2. We use `griffe` to parse docstrings. Supported docstring formats are `google`, `sphinx` and `numpy`. We attempt to automatically detect the docstring format, but this is best-effort and you can explicitly set it when calling `function_tool`. You can also disable docstring parsing by setting `use_docstring_info` to `False`.

The code for the schema extraction lives in [`cai.sdk.agents.function_schema`][].

## Agents as tools

In some workflows, you may want a central agent to orchestrate a network of specialized agents, instead of handing off control. You can do this by modeling agents as tools.

```python
from cai.sdk.agents import Agent, Runner, OpenAIChatCompletionsModel
from openai import AsyncOpenAI
import asyncio

# Agent that simulates scanning an IP for threats
ip_scanner_agent = Agent(
    name="IP Scanner",
    instructions="You receive an IP address and respond with its threat status (e.g., malicious or clean).",
)

# Agent that simulates analyzing a log file
log_analyzer_agent = Agent(
    name="Log Analyzer",
    instructions="You receive a log file path and respond with any suspicious findings from the logs.",
    model=OpenAIChatCompletionsModel(
        model="qwen2.5:14b",
        openai_client=AsyncOpenAI(),
    )
)

# Orchestrator agent that routes cybersecurity tasks to the correct tool
cyber_orchestrator_agent = Agent(
    name="Cyber Orchestrator",
    instructions=(
        "You are a cybersecurity assistant. Based on the user's request, you decide whether to scan an IP or analyze a log. "
        "Use the appropriate tool for each task."
    ),
    tools=[
        ip_scanner_agent.as_tool(
            tool_name="scan_ip",
            tool_description="Scan an IP address for possible threats",
        ),
        log_analyzer_agent.as_tool(
            tool_name="analyze_log",
            tool_description="Analyze a system log file for suspicious activity",
        ),
    ],
    model=OpenAIChatCompletionsModel(
        model="qwen2.5:14b",
        openai_client=AsyncOpenAI(),
    )
)

# Main function that asks the orchestrator to scan an IP
async def main():
    # Example input to scan an IP
    result = await Runner.run(cyber_orchestrator_agent, input="Scan the IP address 192.168.0.10 for threats.")
    print(result.final_output)

# Run the asynchronous main function
if __name__ == "__main__":
    asyncio.run(main())
```

## Handling errors in function tools

When you create a function tool via `@function_tool`, you can pass a `failure_error_function`. This is a function that provides an error response to the LLM in case the tool call crashes.

-   By default (i.e. if you don't pass anything), it runs a `default_tool_error_function` which tells the LLM an error occurred.
-   If you pass your own error function, it runs that instead, and sends the response to the LLM.
-   If you explicitly pass `None`, then any tool call errors will be re-raised for you to handle. This could be a `ModelBehaviorError` if the model produced invalid JSON, or a `UserError` if your code crashed, etc.

If you are manually creating a `FunctionTool` object, then you must handle errors inside the `on_invoke_tool` function.


---

[1] Arguably, the Chain-of-Thought agentic pattern is a special case of the Hierarchical agentic pattern.
[2] Kamhoua, C. A., Leslie, N. O., & Weisman, M. J. (2018). Game theoretic modeling of advanced persistent threat in internet of things. Journal of Cyber Security and Information Systems.
[3] Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2023, January). React: Synergizing reasoning and acting in language models. In International Conference on Learning Representations (ICLR).