# Core API Reference

## Agent

The `Agent` class is the main abstraction for implementing AI agents in CAI.

```python
from cai import Agent

class MyAgent(Agent):
    def __init__(self):
        super().__init__()
        # Initialize your agent here
        
    async def run(self, input_data):
        # Implement your agent's logic here
        pass
```

### Key Methods

- `__init__()`: Initialize the agent
- `run(input_data)`: Main execution method
- `add_tool(tool)`: Add a tool to the agent
- `remove_tool(tool_name)`: Remove a tool from the agent

## Tools

Tools are the building blocks that agents use to interact with the world.

```python
from cai import Tool

class MyTool(Tool):
    def __init__(self):
        super().__init__(
            name="my_tool",
            description="Description of what the tool does"
        )
    
    async def execute(self, **kwargs):
        # Implement tool logic here
        pass
```

### Built-in Tools

- `LinuxCmd`: Execute Linux commands
- `WebSearch`: Perform web searches
- `Code`: Execute code
- `SSHTunnel`: Create SSH tunnels

## Patterns

Patterns are reusable agent behaviors that can be composed together.

```python
from cai import Pattern

class MyPattern(Pattern):
    def __init__(self):
        super().__init__()
        
    async def execute(self, context):
        # Implement pattern logic here
        pass
```

## Handoffs

Handoffs allow agents to transfer control to other agents or human operators.

```python
from cai import Handoff

class MyHandoff(Handoff):
    def __init__(self):
        super().__init__()
        
    async def execute(self, context):
        # Implement handoff logic here
        pass
```

## Tracing

Tracing provides visibility into agent execution.

```python
from cai import Tracer

tracer = Tracer()
tracer.start_trace()
# ... agent execution ...
tracer.end_trace()
```

## HITL (Human In The Loop)

HITL allows human operators to interact with agents during execution.

```python
from cai import HITL

class MyHITL(HITL):
    def __init__(self):
        super().__init__()
        
    async def execute(self, context):
        # Implement HITL logic here
        pass
``` 