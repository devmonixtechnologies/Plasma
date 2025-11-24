# Architecture Overview

CAI focuses on making cybersecurity agent **coordination** and **execution** lightweight, highly controllable, and useful for humans. To do so it builds upon 7 pillars: `Agent`s, `Tools`, `Handoffs`, `Patterns`, `Turns`, `Tracing` and `HITL`.

```
                  ┌───────────────┐           ┌───────────┐
                  │      HITL     │◀─────────▶│   Turns   │
                  └───────┬───────┘           └───────────┘
                          │
                          ▼
┌───────────┐       ┌───────────┐       ┌───────────┐      ┌───────────┐
│  Patterns │◀─────▶│  Handoffs │◀────▶ │   Agents  │◀────▶│    LLMs   │
└───────────┘       └─────┬─────┘       └───────────┘      └───────────┘
                          │                   │
                          │                   ▼
┌────────────┐       ┌────┴──────┐       ┌───────────┐
│ Extensions │◀─────▶│  Tracing  │       │   Tools   │
└────────────┘       └───────────┘       └───────────┘
                                              │
                          ┌─────────────┬─────┴────┬─────────────┐
                          ▼             ▼          ▼             ▼
                    ┌───────────┐┌───────────┐┌────────────┐┌───────────┐
                    │ LinuxCmd  ││ WebSearch ││    Code    ││ SSHTunnel │
                    └───────────┘└───────────┘└────────────┘└───────────┘
```

If you want to dive deeper into the code, check the following files as a start point for using CAI:

```
cai
├── __init__.py
│
├── cli.py                        # entrypoint for CLI
├── core.py                     # core implementation and agentic flow
├── types.py                   # main abstractions and classes
├── util.py                      # utility functions
│
├── repl                          # CLI aesthetics and commands
│   ├── commands
│   └── ui
├── agents                      # agent implementations
│   ├── one_tool.py      # agent, one agent per file
│   └── patterns            # agentic patterns, one per file
│
├── tools                        # agent tools
│   ├── common.py

caiextensions                      # out of tree Python extensions
``` 