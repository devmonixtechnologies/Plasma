"""
Help command for CAI REPL.
This module provides commands for displaying help information.
"""

from typing import List, Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
except ImportError as exc:
    raise ImportError(
        "The 'rich' package is required. Please install it with: pip install rich"
    ) from exc

from cai.repl.commands.base import COMMAND_ALIASES, COMMANDS, Command, register_command

try:
    from caiextensions.platform.base.platform_manager import PlatformManager
    HAS_PLATFORM_EXTENSIONS = True
except ImportError:
    HAS_PLATFORM_EXTENSIONS = False

from cai import is_caiextensions_platform_available

console = Console()


def create_styled_table(
    title: str, headers: List[tuple[str, str]], header_style: str = "bold white"
) -> Table:
    """Create a styled table with consistent formatting.

    Args:
        title: The table title
        headers: List of (header_name, style) tuples
        header_style: Style for the header row

    Returns:
        A configured Table instance
    """
    table = Table(title=title, show_header=True, header_style=header_style)
    for header, style in headers:
        table.add_column(header, style=style)
    return table


def create_notes_panel(
    notes: List[str], title: str = "Notes", border_style: str = "yellow"
) -> Panel:
    """Create a notes panel with consistent formatting.

    Args:
        notes: List of note strings
        title: Panel title
        border_style: Style for the panel border

    Returns:
        A configured Panel instance
    """
    notes_text = Text.from_markup("\n".join(f"• {note}" for note in notes))
    return Panel(notes_text, title=title, border_style=border_style)


class HelpCommand(Command):
    """Command for displaying help information."""

    def __init__(self):
        """Initialize the help command."""
        super().__init__(
            name="/help",
            description=("Display help information about commands and features"),
            aliases=["/h", "/?"],
        )

        # Add subcommands organized by category
        # Agent Management
        self.add_subcommand("agent", "Display help for agent commands", self.handle_agent)
        self.add_subcommand("parallel", "Display help for parallel execution", self.handle_parallel)
        self.add_subcommand("run", "Display help for queued execution", self.handle_run)
        
        # Memory & History
        self.add_subcommand("memory", "Display help for memory persistence", self.handle_memory)
        self.add_subcommand("history", "Display help for conversation history", self.handle_history)
        self.add_subcommand("compact", "Display help for conversation compaction", self.handle_compact)
        self.add_subcommand("flush", "Display help for clearing histories", self.handle_flush)
        self.add_subcommand("load", "Display help for loading JSONL files", self.handle_load)
        self.add_subcommand("merge", "Display help for merging agent histories", self.handle_merge_help)
        
        # Environment & Config
        self.add_subcommand("config", "Display help for configuration", self.handle_config)
        self.add_subcommand("env", "Display help for environment variables", self.handle_env)
        self.add_subcommand("workspace", "Display help for workspace management", self.handle_workspace)
        self.add_subcommand("virtualization", "Display help for Docker containers", self.handle_virtualization)
        
        # Tools & Integration
        self.add_subcommand("mcp", "Display help for Model Context Protocol", self.handle_mcp)
        self.add_subcommand("platform", "Display help for platform commands", self.handle_platform)
        self.add_subcommand("shell", "Display help for shell commands", self.handle_shell)
        
        # Utilities
        self.add_subcommand("model", "Display help for model selection", self.handle_model)
        self.add_subcommand("graph", "Display help for visualization", self.handle_graph)
        self.add_subcommand("aliases", "Display all command aliases", self.handle_aliases)
        self.add_subcommand("kill", "Display help for process management", self.handle_kill)
        
        # General
        self.add_subcommand("commands", "List all available commands", self.handle_commands)
        self.add_subcommand("quick", "Quick reference guide", self.handle_quick)
        self.add_subcommand("quickstart", "Show quickstart guide for new users", self.handle_quickstart)

    def handle_memory(self, _: Optional[List[str]] = None) -> bool:
        """Show help for memory commands."""
        # Get the memory command and show its help
        memory_cmd = next((cmd for cmd in COMMANDS.values() if cmd.name == "/memory"), None)
        if memory_cmd and hasattr(memory_cmd, "show_help"):
            memory_cmd.show_help()
            return True

        # Fallback if memory command not found or doesn't have show_help
        self.handle_help_memory()
        return True

    def handle_agent(self, _: Optional[List[str]] = None) -> bool:
        """Show help for agent management."""
        console.print(
            Panel(
                "[bold]Agent Management Commands[/bold]\n\n"
                "Agents are autonomous AI assistants specialized for different tasks.\n\n"
                "[bold yellow]Available Commands:[/bold yellow]\n"
                "• [yellow]/agent list[/yellow] - List all available agents\n"
                "• [yellow]/agent select <name>[/yellow] - Switch to a specific agent\n"
                "• [yellow]/agent info <name>[/yellow] - Show agent details and tools\n"
                "• [yellow]/agent multi[/yellow] - Enable multi-agent mode\n"
                "• [yellow]/agent current[/yellow] - Show current agent configuration\n\n"
                "[bold cyan]Examples:[/bold cyan]\n"
                "• [green]/agent list[/green] - See all available agents\n"
                "• [green]/agent select red_teamer[/green] - Switch to offensive security agent\n"
                "• [green]/agent info bug_bounter[/green] - View bug bounty agent details\n"
                "• [green]/a select 2[/green] - Select agent by number (using alias)\n\n"
                "[bold]Available Agents:[/bold]\n"
                "• [cyan]one_tool_agent[/cyan] - Basic CTF solver\n"
                "• [cyan]red_teamer[/cyan] - Offensive security specialist\n"
                "• [cyan]blue_teamer[/cyan] - Defensive security specialist\n"
                "• [cyan]bug_bounter[/cyan] - Bug bounty hunter\n"
                "• [cyan]dfir[/cyan] - Digital forensics & incident response\n"
                "• [cyan]network_traffic_analyzer[/cyan] - Network analysis\n"
                "• [cyan]flag_discriminator[/cyan] - CTF flag extraction\n"
                "• [cyan]codeagent[/cyan] - Code generation and analysis\n"
                "• [cyan]thought[/cyan] - Strategic planning\n\n"
                "[dim]Alias: /a[/dim]",
                title="Agent Commands",
                border_style="blue",
            )
        )
        return True

    def handle_graph(self, _: Optional[List[str]] = None) -> bool:
        """Show help for graph visualization."""
        console.print(
            Panel(
                "[bold]Graph Visualization Commands[/bold]\n\n"
                "Visualize agent conversation history with multi-agent support.\n\n"
                "[bold yellow]Available Commands:[/bold yellow]\n"
                "• [yellow]/graph[/yellow] - Show graph (single or all agents)\n"
                "• [yellow]/graph P1[/yellow] - Show graph for agent by ID\n"
                "• [yellow]/graph <agent_name>[/yellow] - Show graph for specific agent\n"
                "• [yellow]/graph all[/yellow] - Show graphs for all agents\n"
                "• [yellow]/graph timeline[/yellow] - Unified timeline of all agents\n"
                "• [yellow]/graph stats[/yellow] - Detailed conversation statistics\n"
                "• [yellow]/graph export <format>[/yellow] - Export data (json, dot, mermaid)\n\n"
                "[bold cyan]Features:[/bold cyan]\n"
                "• Multi-agent visualization in parallel mode\n"
                "• User messages and agent responses\n"
                "• Tool call highlighting\n"
                "• Timeline view for chronological analysis\n"
                "• Statistical insights across agents\n"
                "• Export to multiple formats\n\n"
                "[bold green]Examples:[/bold green]\n"
                "• [green]/graph[/green] - Display current graph\n"
                "• [green]/graph P2[/green] - Show graph for agent P2\n"
                "• [green]/graph red_teamer[/green] - Show red_teamer's graph\n"
                "• [green]/graph timeline[/green] - View timeline\n"
                "• [green]/graph stats[/green] - See statistics\n"
                "• [green]/graph export mermaid graph.md[/green] - Export Mermaid\n"
                "• [green]/g timeline[/green] - Using alias\n\n"
                "[bold]Export Formats:[/bold]\n"
                "• [cyan]json[/cyan] - Complete conversation data\n"
                "• [cyan]dot[/cyan] - Graphviz DOT format\n"
                "• [cyan]mermaid[/cyan] - Mermaid diagram format\n\n"
                "[dim]Alias: /g[/dim]",
                title="Graph Commands",
                border_style="blue",
            )
        )
        return True

    def handle_platform(self, _: Optional[List[str]] = None) -> bool:
        """Show help for platform-specific features."""
        platform_cmd = next((cmd for cmd in COMMANDS.values() if cmd.name == "/platform"), None)

        if platform_cmd and hasattr(platform_cmd, "show_help"):
            platform_cmd.show_help()
            return True

        console.print(
            Panel(
                "Platform commands provide access to platform-specific "
                "features.\n\n"
                "[bold]Available Commands:[/bold]\n"
                "• [yellow]/platform list[/yellow] - List available platforms\n"
                "• [yellow]/platform <platform> <command>[/yellow] - Run "
                "platform-specific command\n\n"
                "[bold]Examples:[/bold]\n"
                "• [green]/platform list[/green] - Show all available platforms\n"
                "• [green]/p list[/green] - Shorthand for platform list",
                title="Platform Commands",
                border_style="blue",
            )
        )
        return True

    def handle_shell(self, _: Optional[List[str]] = None) -> bool:
        """Show help for shell command execution."""
        console.print(
            Panel(
                "Shell commands allow you to execute system commands directly.\n\n"
                "[bold]Available Commands:[/bold]\n"
                "• [yellow]/shell <command>[/yellow] - Execute a shell command\n"
                "• [yellow]/![/yellow] - Shorthand for /shell\n\n"
                "[bold]Session Management:[/bold]\n"
                "• [yellow]/shell session list[/yellow] - List active sessions\n"
                "• [yellow]/shell session output <id>[/yellow] - Get output from "
                "a session\n"
                "• [yellow]/shell session kill <id>[/yellow] - Terminate a "
                "session\n\n"
                "[bold]Examples:[/bold]\n"
                "• [green]/shell ls -la[/green] - List files in current "
                "directory\n"
                "• [green]/! pwd[/green] - Show current working directory",
                title="Shell Commands",
                border_style="blue",
            )
        )
        return True

    def handle_env(self, _: Optional[List[str]] = None) -> bool:
        """Show help for environment variables."""
        console.print(
            Panel(
                "Environment variables control CAI's behavior.\n\n"
                "[bold]Key Variables:[/bold]\n"
                "• [yellow]CAI_MODEL[/yellow] - Default AI model (e.g., "
                "'claude-3-7-sonnet-20250219')\n"
                "• [yellow]CAI_<AGENT>_MODEL[/yellow] - Agent-specific model "
                "(e.g., CAI_REDTEAM_AGENT_MODEL)\n"
                "• [yellow]CAI_MEMORY_DIR[/yellow] - Directory for storing memory "
                "collections\n\n"
                "[bold]API Keys:[/bold]\n"
                "Set API keys as environment variables following the pattern:\n"
                "• [yellow]PROVIDER_API_KEY[/yellow] - Where PROVIDER is your model provider\n\n"
                "Examples:\n"
                "• [yellow]export OPENAI_API_KEY='your-key'[/yellow]\n"
                "• [yellow]export ANTHROPIC_API_KEY='your-key'[/yellow]\n"
                "• [yellow]export YOUR_PROVIDER_API_KEY='your-key'[/yellow]\n\n"
                "[bold]Available Commands:[/bold]\n"
                "• [yellow]/env list[/yellow] - Show all environment variables\n"
                "• [yellow]/env set <n> <value>[/yellow] - Set an environment "
                "variable\n"
                "• [yellow]/env get <n>[/yellow] - Get the value of an "
                "environment variable",
                title="Environment Variables",
                border_style="blue",
            )
        )
        return True

    def handle_aliases(self, _: Optional[List[str]] = None) -> bool:
        """Show all command aliases."""
        return self.handle_help_aliases()

    def handle_model(self, _: Optional[List[str]] = None) -> bool:
        """Show help for model selection."""
        return self.handle_help_model()

    def handle_turns(self, _: Optional[List[str]] = None) -> bool:
        """Show help for managing turns."""
        return self.handle_help_turns()

    def handle_config(self, _: Optional[List[str]] = None) -> bool:
        """Display help for config commands.

        Args:
            _: Ignored arguments

        Returns:
            True if successful
        """
        return self.handle_help_config()

    def handle_no_args(self) -> bool:
        """Handle the command when no arguments are provided."""
        return self.handle_help()

    def _print_command_table(
        self,
        title: str,
        commands: List[tuple[str, str, str]],
        header_style: str = "bold yellow",
        command_style: str = "yellow",
    ) -> None:
        """Print a table of commands with consistent formatting."""
        table = create_styled_table(
            title,
            [("Command", command_style), ("Alias", "green"), ("Description", "white")],
            header_style,
        )

        for cmd, alias, desc in commands:
            table.add_row(cmd, alias, desc)

        console.print(table)

    def handle_help(self) -> bool:
        """Display general help information.

        Returns:
            True if successful
        """
        console.print(
            Panel(
                Text.from_markup(
                    "[bold]Welcome to CAI (Cybersecurity AI)[/bold]\n\n"
                    "CAI is a powerful AI-driven security framework for penetration testing, "
                    "bug bounty hunting, and security research.\n\n"
                    "REMINDER: This is a work in progress. Please report any issues or feedback to the developer.\n"
                    "[yellow]For detailed help on any topic, use:[/yellow] [bold]/help <topic>[/bold]\n"
                    "[yellow]For a quick reference guide, use:[/yellow] [bold]/help quick[/bold]\n"
                    "[yellow]To see all commands, use:[/yellow] [bold]/help commands[/bold]"
                ),
                title="🔒 CAI Help System",
                border_style="yellow",
            )
        )

        # Command Categories
        categories = [
            ("[bold yellow]Agent Management[/bold yellow]", [
                ("[cyan]/agent[/cyan]", "Manage and switch between agents"),
                ("[cyan]/parallel[/cyan]", "Configure parallel agent execution"),
                ("[cyan]/run[/cyan]", "Queue prompts for execution"),
            ]),
            ("[bold green]Memory & History[/bold green]", [
                ("[cyan]/memory[/cyan]", "Persistent memory management"),
                ("[cyan]/history[/cyan]", "View conversation history"),
                ("[cyan]/compact[/cyan]", "Compact conversations with AI"),
                ("[cyan]/flush[/cyan]", "Clear agent histories"),
                ("[cyan]/load[/cyan]", "Load JSONL conversation files"),
                ("[cyan]/merge[/cyan]", "Merge agent histories"),
            ]),
            ("[bold blue]Environment & Config[/bold blue]", [
                ("[cyan]/config[/cyan]", "Manage environment variables"),
                ("[cyan]/env[/cyan]", "Display current environment"),
                ("[cyan]/workspace[/cyan]", "Manage working directories"),
                ("[cyan]/virtualization[/cyan]", "Docker container management"),
            ]),
            ("[bold magenta]Tools & Integration[/bold magenta]", [
                ("[cyan]/mcp[/cyan]", "Model Context Protocol servers"),
                ("[cyan]/platform[/cyan]", "Platform-specific features"),
                ("[cyan]/shell[/cyan]", "Execute shell commands"),
            ]),
            ("[bold red]Utilities[/bold red]", [
                ("[cyan]/model[/cyan]", "Change AI models"),
                ("[cyan]/graph[/cyan]", "Visualize agent interactions"),
                ("[cyan]/kill[/cyan]", "Terminate active processes"),
                ("[cyan]/exit[/cyan]", "Exit CAI"),
            ]),
        ]

        for category_name, commands in categories:
            console.print(f"\n{category_name}")
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column(style="cyan", width=25)
            table.add_column(style="white")
            for cmd, desc in commands:
                table.add_row(f"  {cmd}", desc)
            console.print(table)

        # Quick Tips
        tips = Panel(
            Text.from_markup(
                "[bold]Quick Tips:[/bold]\n"
                "• Use [bold cyan]Tab[/bold cyan] for command completion\n"
                "• Use [bold cyan]↑/↓[/bold cyan] to navigate command history\n"
                "• Use [bold cyan]Ctrl+C[/bold cyan] to interrupt running commands\n"
                "• Use [bold cyan]Ctrl+L[/bold cyan] to clear the screen\n"
                "• Most commands have aliases (e.g., [yellow]/h[/yellow] for [yellow]/help[/yellow])\n"
                "• Type [yellow]/help <command>[/yellow] for detailed command help"
            ),
            title="💡 Tips",
            border_style="cyan",
        )
        console.print("\n")
        console.print(tips)

        return True

    def handle_help_aliases(self) -> bool:
        """Show all command aliases in a well-formatted table."""
        # Create a styled header
        console.print(Panel("Command Aliases Reference", border_style="magenta", title="Aliases"))

        # Create a table for aliases
        alias_table = create_styled_table(
            "Command Aliases",
            [("Alias", "green"), ("Command", "yellow"), ("Description", "white")],
            "bold magenta",
        )

        # Add rows for each alias
        for alias, command in sorted(COMMAND_ALIASES.items()):
            cmd = COMMANDS.get(command)
            description = cmd.description if cmd else ""
            alias_table.add_row(alias, command, description)

        console.print(alias_table)

        # Add tips
        tips = [
            "Aliases can be used anywhere the full command would be used",
            ("Example: [green]/m list[/green] instead of [yellow]/memory list[/yellow]"),
        ]
        console.print("\n")
        console.print(create_notes_panel(tips, "Tips", "cyan"))

        return True

    def handle_help_memory(self) -> bool:
        """Show help for memory commands with rich formatting."""
        # Create a styled header
        header = Text("Memory Command Help", style="bold yellow")
        console.print(Panel(header, border_style="yellow"))

        # Usage table
        usage_table = create_styled_table(
            "Usage", [("Command", "yellow"), ("Description", "white")]
        )

        usage_table.add_row("/memory list", "Display all available memory collections")
        usage_table.add_row("/memory load <collection>", "Set the active memory collection")
        usage_table.add_row("/memory delete <collection>", "Delete a memory collection")
        usage_table.add_row("/memory create <collection>", "Create a new memory collection")
        usage_table.add_row("/m", "Alias for /memory")

        console.print(usage_table)

        # Examples table
        examples_table = create_styled_table(
            "Examples", [("Example", "cyan"), ("Description", "white")], "bold cyan"
        )

        examples = [
            ("/memory list", "List all available collections"),
            ("/memory load _all_", "Load the semantic memory collection"),
            ("/memory load my_ctf", "Load the episodic memory for 'my_ctf'"),
            ("/memory create new_collection", "Create a new collection named 'new_collection'"),
            ("/memory delete old_collection", "Delete the collection named 'old_collection'"),
        ]

        for example, desc in examples:
            examples_table.add_row(example, desc)

        console.print(examples_table)

        # Collection types table
        types_table = create_styled_table(
            "Collection Types", [("Type", "green"), ("Description", "white")], "bold green"
        )

        types = [
            ("_all_", "Semantic memory across all CTFs"),
            ("<CTF_NAME>", "Episodic memory for a specific CTF"),
            ("<custom_name>", "Custom memory collection"),
        ]

        for type_name, desc in types:
            types_table.add_row(type_name, desc)

        console.print(types_table)

        # Notes panel
        notes = [
            "Memory collections are stored in the Qdrant vector database",
            "The active collection is stored in the CAI_MEMORY_COLLECTION env var",
            "Episodic memory is used for specific CTFs or tasks",
            "Semantic memory (_all_) is used across all CTFs",
            "Memory is used to provide context to the agent",
        ]

        console.print(create_notes_panel(notes))

        return True

    def handle_help_model(self) -> bool:
        """Show help for model command with rich formatting."""
        # Create a styled header
        header = Text("Model Command Help", style="bold magenta")
        console.print(Panel(header, border_style="magenta"))

        # Usage table
        usage_table = create_styled_table(
            "Usage", [("Command", "magenta"), ("Description", "white")]
        )

        usage_commands = [
            ("/model", "Display current model and list available models"),
            ("/model <model_name>", "Change the model to <model_name>"),
            ("/model <number>", "Change the model using its number from the list"),
            ("/mod", "Alias for /model"),
        ]

        for cmd, desc in usage_commands:
            usage_table.add_row(cmd, desc)

        console.print(usage_table)

        # Examples table
        examples_table = create_styled_table(
            "Examples", [("Example", "cyan"), ("Description", "white")], "bold cyan"
        )

        examples = [
            ("/model 1", "Switch to the first model in the list (Claude 3.7 Sonnet)"),
            ("/model claude-3-7-sonnet-20250219", "Switch to Claude 3.7 Sonnet model"),
            ("/model o1", "Switch to OpenAI's O1 model (good for math)"),
            ("/model gpt-4o", "Switch to OpenAI's GPT-4o model"),
        ]

        for example, desc in examples:
            examples_table.add_row(example, desc)

        console.print(examples_table)

        # Model information
        console.print("\n[bold green]Model Information:[/bold green]\n")
        console.print("CAI supports hundreds of models through various providers.")
        console.print("Use [yellow]/model[/yellow] to see available models for your configured API keys.")
        console.print("\nModel categories include:")
        console.print("• Fast inference models for quick responses")
        console.print("• Reasoning models for complex analysis")
        console.print("• Code-specialized models for development")
        console.print("• Local models via Ollama")
        console.print("• Multi-provider access through aggregators")

        # Notes panel
        notes = [
            "The model change takes effect on the next agent interaction",
            "The model is stored in the CAI_MODEL environment variable",
            "Each provider requires its API key following the pattern: PROVIDER_API_KEY",
            "Use /config to see which API keys are configured",
            "Use /quickstart to check your API key setup",
            "Local models via Ollama require local installation",
        ]

        console.print(create_notes_panel(notes))

        return True

    def handle_help_turns(self) -> bool:
        """Show help for turns command with rich formatting."""
        # Create a styled header
        header = Text("Turns Command Help", style="bold magenta")
        console.print(Panel(header, border_style="magenta"))

        # Usage table
        usage_table = create_styled_table(
            "Usage", [("Command", "magenta"), ("Description", "white")]
        )

        usage_commands = [
            ("/turns", "Display current maximum number of turns"),
            ("/turns <number>", "Change the maximum number of turns"),
            ("/turns inf", "Set unlimited turns"),
            ("/t", "Alias for /turns"),
        ]

        for cmd, desc in usage_commands:
            usage_table.add_row(cmd, desc)

        console.print(usage_table)

        # Examples table
        examples_table = create_styled_table(
            "Examples", [("Example", "cyan"), ("Description", "white")], "bold cyan"
        )

        examples = [
            ("/turns", "Show current maximum turns"),
            ("/turns 10", "Set maximum turns to 10"),
            ("/turns inf", "Set unlimited turns"),
            ("/t 5", "Set maximum turns to 5 (using alias)"),
        ]

        for example, desc in examples:
            examples_table.add_row(example, desc)

        console.print(examples_table)

        # Notes panel
        notes = [
            ("The maximum turns limit controls how many responses the agent will give"),
            "Setting turns to 'inf' allows unlimited responses",
            ("The turns count is stored in the CAI_MAX_TURNS environment variable"),
            "Each agent response counts as one turn",
        ]

        console.print(create_notes_panel(notes))

        return True

    def handle_help_platform_manager(self) -> bool:
        """Show help for platform manager commands."""
        if HAS_PLATFORM_EXTENSIONS and is_caiextensions_platform_available():
            try:
                from caiextensions.platform.base import platform_manager

                platforms = platform_manager.list_platforms()

                if not platforms:
                    console.print("[yellow]No platforms registered.[/yellow]")
                    return True

                platform_table = create_styled_table(
                    "Available Platforms",
                    [("Platform", "magenta"), ("Description", "white")],
                    "bold magenta",
                )

                for platform_name in platforms:
                    platform = platform_manager.get_platform(platform_name)
                    description = getattr(platform, "description", platform_name.capitalize())
                    platform_table.add_row(platform_name, description)

                console.print(platform_table)

                # Add platform command examples
                examples = []
                for platform_name in platforms:
                    platform = platform_manager.get_platform(platform_name)
                    commands = platform.get_commands()
                    if commands:
                        command_example = f"[green]/platform {platform_name} {commands[0]}[/green] - Example {platform_name} command"
                        examples.append(command_example)

                if examples:
                    console.print(
                        Panel(
                            "\n".join(examples),
                            title="Platform Command Examples",
                            border_style="blue",
                        )
                    )

                return True
            except (ImportError, Exception) as e:
                console.print(f"[yellow]Error loading platforms: {e}[/yellow]")
                return True

        console.print("[yellow]No platform extensions available.[/yellow]")
        return True

    def handle_help_config(self) -> bool:
        """Display help for config commands.

        Returns:
            True if successful
        """
        console.print(
            Panel(
                Text.from_markup(
                    "The [bold yellow]/config[/bold yellow] command allows you "
                    "to view and configure environment variables that control "
                    "the behavior of CAI."
                ),
                title="Config Commands",
                border_style="yellow",
            )
        )

        # Create table for subcommands
        table = create_styled_table(
            "Available Subcommands", [("Command", "yellow"), ("Description", "white")]
        )

        table.add_row("/config", "List all environment variables and their current values")
        table.add_row("/config list", "List all environment variables and their current values")
        table.add_row(
            "/config get <number>", "Get the value of a specific environment variable by its number"
        )
        table.add_row(
            "/config set <number> <value>",
            "Set the value of a specific environment variable by its number",
        )

        console.print(table)

        # Create notes panel
        notes = [
            "Environment variables control various aspects of CAI behavior.",
            "Changes environment variables only affect the current session.",
            "Use the [yellow]/config list[/yellow] command to see options.",
            "Each variable is assigned a number for easy reference.",
        ]
        console.print(create_notes_panel(notes))

        return True

    def handle_parallel(self, _: Optional[List[str]] = None) -> bool:
        """Show help for parallel execution."""
        console.print(
            Panel(
                "[bold]Parallel Agent Execution[/bold]\n\n"
                "Run multiple agents concurrently for collaborative problem-solving.\n\n"
                "[bold yellow]Available Commands:[/bold yellow]\n"
                "• [yellow]/parallel[/yellow] - Show current configuration\n"
                "• [yellow]/parallel add <agent>[/yellow] - Add agent to parallel config\n"
                "• [yellow]/parallel list[/yellow] - List configured agents\n"
                "• [yellow]/parallel clear[/yellow] - Clear all configurations\n"
                "• [yellow]/parallel remove <index>[/yellow] - Remove specific agent\n"
                "• [yellow]/parallel override-models[/yellow] - Use global model for all\n"
                "• [yellow]/parallel merge <indices>[/yellow] - Merge agent histories\n"
                "• [yellow]/parallel prompt <index> <text>[/yellow] - Set custom prompt\n\n"
                "[bold cyan]Examples:[/bold cyan]\n"
                "• [green]/parallel add red_teamer[/green] - Add red team agent\n"
                "• [green]/parallel add bug_bounter custom_prompt=\"Find SQLi\"[/green]\n"
                "• [green]/parallel merge 1,2[/green] - Merge histories of P1 and P2\n"
                "• [green]/p list[/green] - Show all configured agents\n\n"
                "[bold]Notes:[/bold]\n"
                "• Agents run independently with isolated contexts\n"
                "• Each agent gets a unique ID (P1, P2, etc.)\n"
                "• Results are displayed side-by-side\n"
                "• Use CAI_PARALLEL env var to set default count\n\n"
                "[dim]Aliases: /par, /p[/dim]",
                title="Parallel Execution",
                border_style="blue",
            )
        )
        return True

    def handle_run(self, _: Optional[List[str]] = None) -> bool:
        """Show help for queued execution."""
        console.print(
            Panel(
                "[bold]Queued Prompt Execution[/bold]\n\n"
                "Queue prompts for agents in parallel mode.\n\n"
                "[bold yellow]Available Commands:[/bold yellow]\n"
                "• [yellow]/run queue <agent_id> <prompt>[/yellow] - Queue a prompt\n"
                "• [yellow]/run list[/yellow] - List all queued prompts\n"
                "• [yellow]/run clear[/yellow] - Clear all queued prompts\n"
                "• [yellow]/run remove <index>[/yellow] - Remove specific prompt\n\n"
                "[bold cyan]Examples:[/bold cyan]\n"
                "• [green]/run queue P1 \"Scan port 80\"[/green] - Queue for agent P1\n"
                "• [green]/run queue P2 \"Check for SQL injection\"[/green]\n"
                "• [green]/run list[/green] - See all queued prompts\n"
                "• [green]/r clear[/green] - Clear the queue\n\n"
                "[bold]Notes:[/bold]\n"
                "• Only available in parallel mode\n"
                "• Prompts execute when you send a message\n"
                "• Each agent processes its queue independently\n\n"
                "[dim]Alias: /r[/dim]",
                title="Run Queue Commands",
                border_style="green",
            )
        )
        return True

    def handle_history(self, _: Optional[List[str]] = None) -> bool:
        """Show help for conversation history."""
        console.print(
            Panel(
                "[bold]Conversation History Management[/bold]\n\n"
                "View and manage agent conversation histories.\n\n"
                "[bold yellow]Available Commands:[/bold yellow]\n"
                "• [yellow]/history[/yellow] - Show control panel for all agents\n"
                "• [yellow]/history all[/yellow] - Display all agent histories\n"
                "• [yellow]/history <agent>[/yellow] - Show specific agent history\n"
                "• [yellow]/history search <term>[/yellow] - Search in histories\n"
                "• [yellow]/history <agent> <index>[/yellow] - Show specific message\n"
                "• [yellow]/history export <file>[/yellow] - Export to JSON\n\n"
                "[bold cyan]Examples:[/bold cyan]\n"
                "• [green]/history[/green] - View control panel\n"
                "• [green]/history P1[/green] - Show P1's conversation\n"
                "• [green]/history search \"password\"[/green] - Search for term\n"
                "• [green]/his red_teamer 5[/green] - Show message #5\n\n"
                "[bold]Features:[/bold]\n"
                "• Token count and cost tracking\n"
                "• Message role visualization\n"
                "• Tool call details\n"
                "• Export for analysis\n\n"
                "[dim]Alias: /his[/dim]",
                title="History Commands",
                border_style="magenta",
            )
        )
        return True

    def handle_compact(self, _: Optional[List[str]] = None) -> bool:
        """Show help for conversation compaction."""
        console.print(
            Panel(
                "[bold]Conversation Compaction[/bold]\n\n"
                "Use AI to summarize and compact long conversations.\n\n"
                "[bold yellow]Available Commands:[/bold yellow]\n"
                "• [yellow]/compact[/yellow] - Compact current conversation\n"
                "• [yellow]/compact model <name>[/yellow] - Set compaction model\n"
                "• [yellow]/compact prompt <text>[/yellow] - Set custom prompt\n"
                "• [yellow]/compact status[/yellow] - Show current settings\n\n"
                "[bold cyan]Examples:[/bold cyan]\n"
                "• [green]/compact[/green] - Compact with default settings\n"
                "• [green]/compact model o3-mini[/green] - Use O3 Mini model\n"
                "• [green]/compact prompt \"Focus on vulnerabilities\"[/green]\n"
                "• [green]/cmp status[/green] - Check configuration\n\n"
                "[bold]Features:[/bold]\n"
                "• Preserves important context\n"
                "• Reduces token usage\n"
                "• Saves to memory (M-prefixed)\n"
                "• Clears history after compaction\n\n"
                "[dim]Alias: /cmp[/dim]",
                title="Compact Commands",
                border_style="yellow",
            )
        )
        return True

    def handle_flush(self, _: Optional[List[str]] = None) -> bool:
        """Show help for clearing histories."""
        console.print(
            Panel(
                "[bold]Clear Conversation Histories[/bold]\n\n"
                "Remove message histories and reset contexts.\n\n"
                "[bold yellow]Available Commands:[/bold yellow]\n"
                "• [yellow]/flush[/yellow] - Clear current agent's history\n"
                "• [yellow]/flush all[/yellow] - Clear all agent histories\n"
                "• [yellow]/flush <agent>[/yellow] - Clear specific agent\n"
                "• [yellow]/flush P1[/yellow] - Clear parallel agent P1\n\n"
                "[bold cyan]Examples:[/bold cyan]\n"
                "• [green]/flush[/green] - Clear active agent\n"
                "• [green]/flush all[/green] - Reset all agents\n"
                "• [green]/flush red_teamer[/green] - Clear red team agent\n"
                "• [green]/clear P2[/green] - Clear parallel agent P2\n\n"
                "[bold]Effects:[/bold]\n"
                "• Removes all messages\n"
                "• Resets token counts\n"
                "• Preserves agent configuration\n"
                "• Keeps MCP connections\n\n"
                "[dim]Alias: /clear[/dim]",
                title="Flush Commands",
                border_style="red",
            )
        )
        return True

    def handle_load(self, _: Optional[List[str]] = None) -> bool:
        """Show help for loading JSONL files."""
        console.print(
            Panel(
                "[bold]Load JSONL Conversation Files[/bold]\n\n"
                "Import conversation histories from JSONL files.\n\n"
                "[bold yellow]Available Commands:[/bold yellow]\n"
                "• [yellow]/load <file>[/yellow] - Load for current agent\n"
                "• [yellow]/load <file> agent <name>[/yellow] - Load for specific agent\n"
                "• [yellow]/load <file> all[/yellow] - Distribute across all agents\n"
                "• [yellow]/load <file> parallel[/yellow] - Smart parallel distribution\n\n"
                "[bold cyan]Examples:[/bold cyan]\n"
                "• [green]/load session.jsonl[/green] - Load to current agent\n"
                "• [green]/load ctf.jsonl agent red_teamer[/green] - Load to red team\n"
                "• [green]/load scan.jsonl all[/green] - Split across agents\n"
                "• [green]/l pentest.jsonl parallel[/green] - Pattern-based loading\n\n"
                "[bold]Distribution Modes:[/bold]\n"
                "• [cyan]agent[/cyan] - Load all to one agent\n"
                "• [cyan]all[/cyan] - Round-robin distribution\n"
                "• [cyan]parallel[/cyan] - Match by agent patterns\n\n"
                "[dim]Alias: /l[/dim]",
                title="Load Commands",
                border_style="green",
            )
        )
        return True

    def handle_workspace(self, _: Optional[List[str]] = None) -> bool:
        """Show help for workspace management."""
        console.print(
            Panel(
                "[bold]Workspace Management[/bold]\n\n"
                "Manage working directories and project spaces.\n\n"
                "[bold yellow]Available Commands:[/bold yellow]\n"
                "• [yellow]/workspace set <name>[/yellow] - Set workspace name\n"
                "• [yellow]/workspace get[/yellow] - Show current workspace\n"
                "• [yellow]/workspace ls[/yellow] - List workspace files\n"
                "• [yellow]/workspace exec <cmd>[/yellow] - Execute in workspace\n"
                "• [yellow]/workspace copy <src> <dst>[/yellow] - Copy files (container)\n\n"
                "[bold cyan]Examples:[/bold cyan]\n"
                "• [green]/workspace set project1[/green] - Create project1 workspace\n"
                "• [green]/workspace ls[/green] - List workspace contents\n"
                "• [green]/ws exec make build[/green] - Run command in workspace\n"
                "• [green]/ws copy /tmp/scan.txt .[/green] - Copy to workspace\n\n"
                "[bold]Features:[/bold]\n"
                "• Auto-creates directories\n"
                "• Container-aware operations\n"
                "• Integrates with logging\n"
                "• Environment variable: CAI_WORKSPACE\n\n"
                "[dim]Alias: /ws[/dim]",
                title="Workspace Commands",
                border_style="cyan",
            )
        )
        return True

    def handle_virtualization(self, _: Optional[List[str]] = None) -> bool:
        """Show help for Docker container management."""
        console.print(
            Panel(
                "[bold]Docker Container Management[/bold]\n\n"
                "Run security tools in isolated Docker environments.\n\n"
                "[bold yellow]Available Commands:[/bold yellow]\n"
                "• [yellow]/virtualization pull <image>[/yellow] - Pull Docker image\n"
                "• [yellow]/virtualization run <image>[/yellow] - Run container\n"
                "• [yellow]/virtualization run <container_id>[/yellow] - Activate existing\n\n"
                "[bold cyan]Examples:[/bold cyan]\n"
                "• [green]/virt pull kalilinux/kali-rolling[/green] - Pull Kali\n"
                "• [green]/virt run parrotsec/security[/green] - Run Parrot OS\n"
                "• [green]/virt run abc123[/green] - Activate container abc123\n\n"
                "[bold]Supported Images:[/bold]\n"
                "• [cyan]kalilinux/kali-rolling[/cyan] - Kali Linux\n"
                "• [cyan]parrotsec/security[/cyan] - Parrot Security\n"
                "• [cyan]Any security-focused image[/cyan]\n\n"
                "[bold]Features:[/bold]\n"
                "• Host networking enabled\n"
                "• Workspace mounting\n"
                "• Interactive TTY\n"
                "• Sets CAI_ACTIVE_CONTAINER\n\n"
                "[dim]Alias: /virt[/dim]",
                title="Virtualization Commands",
                border_style="blue",
            )
        )
        return True

    def handle_mcp(self, _: Optional[List[str]] = None) -> bool:
        """Show help for Model Context Protocol."""
        console.print(
            Panel(
                "[bold]Model Context Protocol (MCP)[/bold]\n\n"
                "Connect external tool servers to enhance agent capabilities.\n\n"
                "[bold yellow]Available Commands:[/bold yellow]\n"
                "• [yellow]/mcp load <type> <config>[/yellow] - Load MCP server\n"
                "• [yellow]/mcp list[/yellow] - List active servers\n"
                "• [yellow]/mcp add <server> <agent>[/yellow] - Add tools to agent\n"
                "• [yellow]/mcp remove <server>[/yellow] - Remove server\n"
                "• [yellow]/mcp tools <server>[/yellow] - List server tools\n"
                "• [yellow]/mcp status[/yellow] - Check connection status\n"
                "• [yellow]/mcp associations[/yellow] - Show agent mappings\n"
                "• [yellow]/mcp test <server>[/yellow] - Test connectivity\n\n"
                "[bold cyan]Server Types:[/bold cyan]\n"
                "• [green]sse[/green] - Server-Sent Events (HTTP)\n"
                "• [green]stdio[/green] - Standard I/O (Process)\n\n"
                "[bold cyan]Examples:[/bold cyan]\n"
                "• [green]/mcp load sse http://localhost:3000[/green]\n"
                "• [green]/mcp load stdio \"npx @modelcontextprotocol/server-sqlite\"[/green]\n"
                "• [green]/mcp add filesystem red_teamer[/green]\n"
                "• [green]/mcp tools filesystem[/green]\n\n"
                "[bold]Notes:[/bold]\n"
                "• Fresh connections per tool call\n"
                "• Auto-discovery of tools\n"
                "• Supports custom headers\n\n"
                "[dim]Alias: /m[/dim]",
                title="MCP Commands",
                border_style="magenta",
            )
        )
        return True

    def handle_kill(self, _: Optional[List[str]] = None) -> bool:
        """Show help for process management."""
        console.print(
            Panel(
                "[bold]Process Management[/bold]\n\n"
                "Terminate active processes and clean up sessions.\n\n"
                "[bold yellow]Usage:[/bold yellow]\n"
                "• [yellow]/kill[/yellow] - Kill all active processes\n\n"
                "[bold]What it terminates:[/bold]\n"
                "• SSH sessions\n"
                "• Container processes\n"
                "• Background commands\n"
                "• Hanging connections\n\n"
                "[bold cyan]Example:[/bold cyan]\n"
                "• [green]/kill[/green] - Clean up all processes\n"
                "• [green]/k[/green] - Using the alias\n\n"
                "[bold]Use when:[/bold]\n"
                "• Commands are stuck\n"
                "• Need to reset connections\n"
                "• Before switching environments\n\n"
                "[dim]Alias: /k[/dim]",
                title="Kill Command",
                border_style="red",
            )
        )
        return True

    def handle_commands(self, _: Optional[List[str]] = None) -> bool:
        """List all available commands."""
        console.print(
            Panel(
                "[bold]All Available Commands[/bold]",
                title="Command Reference",
                border_style="yellow",
            )
        )

        # Create comprehensive command table
        all_commands = [
            # Agent Management
            ("Agent Management", "yellow", [
                ("/agent", "/a", "Manage and switch agents"),
                ("/parallel", "/par, /p", "Configure parallel execution"),
                ("/run", "/r", "Queue prompts for agents"),
            ]),
            # Memory & History
            ("Memory & History", "green", [
                ("/memory", "/mem", "Persistent memory management"),
                ("/history", "/his", "View conversation history"),
                ("/compact", "/cmp", "Compact conversations"),
                ("/flush", "/clear", "Clear histories"),
                ("/load", "/l", "Load JSONL files"),
                ("/merge", "/mrg", "Merge agent histories"),
            ]),
            # Environment & Config
            ("Environment & Config", "blue", [
                ("/config", "/cfg", "Manage environment variables"),
                ("/env", "/e", "Display environment"),
                ("/workspace", "/ws", "Manage workspaces"),
                ("/virtualization", "/virt", "Docker containers"),
            ]),
            # Tools & Integration
            ("Tools & Integration", "magenta", [
                ("/mcp", "/m", "Model Context Protocol"),
                ("/platform", "/p", "Platform features (conflicts with /parallel)"),
                ("/shell", "/s, /$", "Execute shell commands"),
            ]),
            # Utilities
            ("Utilities", "cyan", [
                ("/model", "/mod", "Change AI models"),
                ("/graph", "/g", "Visualize interactions"),
                ("/help", "/h, /?", "Show help"),
                ("/kill", "/k", "Terminate processes"),
                ("/exit", "/quit, /q", "Exit CAI"),
            ]),
        ]

        for category, color, commands in all_commands:
            console.print(f"\n[bold {color}]{category}[/bold {color}]")
            table = Table(show_header=True, header_style="bold")
            table.add_column("Command", style="cyan")
            table.add_column("Aliases", style="green")
            table.add_column("Description", style="white")
            
            for cmd, aliases, desc in commands:
                table.add_row(cmd, aliases, desc)
            
            console.print(table)

        console.print("\n[dim]Use /help <command> for detailed information about any command.[/dim]")
        return True

    def handle_quick(self, _: Optional[List[str]] = None) -> bool:
        """Show quick reference guide."""
        console.print(
            Panel(
                "[bold]CAI Quick Reference[/bold]",
                title="⚡ Quick Start",
                border_style="yellow",
            )
        )

        # Essential commands
        console.print("\n[bold yellow]Essential Commands:[/bold yellow]")
        quick_ref = [
            ("[cyan]/agent list[/cyan]", "See available agents"),
            ("[cyan]/agent select red_teamer[/cyan]", "Switch to red team agent"),
            ("[cyan]/model gpt-4o[/cyan]", "Change to GPT-4"),
            ("[cyan]/shell ls -la[/cyan]", "Run shell command"),
            ("[cyan]/config[/cyan]", "View all settings"),
            ("[cyan]/help <topic>[/cyan]", "Get detailed help"),
        ]
        
        table = Table(show_header=False, box=None)
        table.add_column(width=35)
        table.add_column()
        for cmd, desc in quick_ref:
            table.add_row(f"  {cmd}", desc)
        console.print(table)

        # Common workflows
        console.print("\n[bold green]Common Workflows:[/bold green]")
        workflows = [
            ("[bold]Start a CTF:[/bold]", [
                "/agent select one_tool_agent",
                "/workspace set ctf_name",
                "Describe the challenge...",
            ]),
            ("[bold]Bug Bounty:[/bold]", [
                "/agent select bug_bounter",
                "/model claude-3-7-sonnet-20250219",
                "Test https://example.com for vulnerabilities",
            ]),
            ("[bold]Parallel Recon:[/bold]", [
                "/parallel add red_teamer",
                "/parallel add network_traffic_analyzer",
                "Scan 192.168.1.0/24",
            ]),
        ]
        
        for title, steps in workflows:
            console.print(f"\n  {title}")
            for step in steps:
                console.print(f"    [green]→[/green] {step}")

        # Keyboard shortcuts
        console.print("\n[bold blue]Keyboard Shortcuts:[/bold blue]")
        shortcuts = [
            ("[cyan]Tab[/cyan]", "Auto-complete commands"),
            ("[cyan]↑/↓[/cyan]", "Navigate history"),
            ("[cyan]Ctrl+C[/cyan]", "Interrupt execution"),
            ("[cyan]Ctrl+L[/cyan]", "Clear screen"),
            ("[cyan]Ctrl+D[/cyan]", "Exit CAI"),
        ]
        
        table = Table(show_header=False, box=None)
        table.add_column(width=20)
        table.add_column()
        for key, action in shortcuts:
            table.add_row(f"  {key}", action)
        console.print(table)

        # Pro tips
        tips = [
            "Most commands have short aliases (e.g., /a for /agent)",
            "Use $ prefix for quick shell commands: $ ls",
            "Set CAI_PARALLEL=3 to always run 3 agents",
            "Check /mcp for external tool integration",
        ]
        
        console.print("\n")
        console.print(create_notes_panel(tips, "💡 Pro Tips", "cyan"))
        
        return True

    def handle_merge_help(self, _: Optional[List[str]] = None) -> bool:
        """Show help for merge command."""
        console.print(
            Panel(
                "[bold]Merge Agent Histories[/bold]\n\n"
                "Combine message histories from multiple agents.\n\n"
                "[bold yellow]Usage:[/bold yellow]\n"
                "• [yellow]/merge <agents...> [options][/yellow] - Merge specified agents\n"
                "• [yellow]/merge all [options][/yellow] - Merge all agent histories\n\n"
                "[bold cyan]Default Behavior:[/bold cyan]\n"
                "Without --target, all source agents receive the complete\n"
                "merged history (with automatic duplicate control)\n\n"
                "[bold cyan]Options:[/bold cyan]\n"
                "• [green]--strategy <type>[/green] - Merge strategy\n"
                "  • chronological (default) - Order by timestamp\n"
                "  • by-agent - Group by agent\n"
                "  • interleaved - Preserve conversation flow\n"
                "• [green]--target <name>[/green] - Create new agent with merged history\n"
                "• [green]--remove-sources[/green] - Remove source agents after merge\n\n"
                "[bold cyan]Examples:[/bold cyan]\n"
                "• [green]/merge P1 P2[/green]\n"
                "  → P1 gets P2's messages, P2 gets P1's messages\n"
                "• [green]/merge P1 P2 --target combined[/green]\n"
                "  → Creates new 'combined' agent, P1 and P2 unchanged\n"
                "• [green]/merge all[/green]\n"
                "  → All agents get the complete combined history\n"
                "• [green]/merge all --target unified --remove-sources[/green]\n"
                "  → Creates 'unified' agent and removes all others\n\n"
                "[bold]Notes:[/bold]\n"
                "• Use agent IDs (P1, P2) or full names\n"
                "• Agent names with spaces are auto-detected\n"
                "• Duplicates are automatically filtered\n"
                "• This is an alias for /parallel merge\n\n"
                "[dim]Alias: /mrg[/dim]",
                title="Merge Command",
                border_style="green",
            )
        )
        return True

    def handle_quickstart(self, _: Optional[List[str]] = None) -> bool:
        """Show quickstart guide by calling the quickstart command."""
        from cai.repl.commands.base import handle_command
        return handle_command("/quickstart")


# Register the command
register_command(HelpCommand())
