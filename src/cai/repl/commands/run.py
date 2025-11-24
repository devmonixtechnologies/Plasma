"""
Run command for CAI CLI - Execute queued prompts in parallel mode.

This command is specifically for parallel mode, allowing users to
queue prompts for different agents and then execute them all.
"""

import os
from typing import Dict, List, Optional

from rich.console import Console
from rich.table import Table

from cai.agents import get_available_agents
from cai.repl.commands.base import Command, register_command
from cai.repl.commands.parallel import PARALLEL_CONFIGS, ParallelConfig

console = Console()

# Store queued prompts for parallel execution
QUEUED_PROMPTS: List[Dict[str, str]] = []


class RunCommand(Command):
    """Command for executing queued prompts in parallel mode."""

    def __init__(self):
        """Initialize the run command."""
        super().__init__(
            name="/run", description="Execute queued prompts in parallel mode", aliases=["/r"]
        )

        # Add subcommands
        self.add_subcommand("queue", "Queue a prompt for an agent", self.handle_queue)
        self.add_subcommand("list", "List queued prompts", self.handle_list)
        self.add_subcommand("clear", "Clear all queued prompts", self.handle_clear)
        self.add_subcommand("remove", "Remove a specific queued prompt", self.handle_remove)

    def handle(self, args: Optional[List[str]] = None) -> bool:
        """Handle the run command - execute all queued prompts.

        Args:
            args: Optional list of command arguments

        Returns:
            True if the command was handled successfully
        """
        parallel_count = int(os.getenv("CAI_PARALLEL", "1"))
        if parallel_count < 2:
            console.print("[red]Error: /run command is only available in parallel mode[/red]")
            console.print(
                "[yellow]Enable parallel mode first with appropriate environment variables[/yellow]"
            )
            return False

        if args and args[0] in ["queue", "list", "clear", "remove"]:
            # Handle subcommand
            handler = getattr(self, f"handle_{args[0]}", None)
            if handler:
                return handler(args[1:] if len(args) > 1 else None)

        # Default behavior - execute queued prompts
        if not QUEUED_PROMPTS:
            console.print(
                "[yellow]No prompts queued. Use '/run queue <agent> <prompt>' to add prompts.[/yellow]"
            )
            return True

        # Set up PARALLEL_CONFIGS from queued prompts
        PARALLEL_CONFIGS.clear()
        for prompt_data in QUEUED_PROMPTS:
            agent_key = prompt_data["agent"]
            prompt = prompt_data["prompt"]
            PARALLEL_CONFIGS.append(ParallelConfig(agent_key, None, prompt))

        console.print(f"[bold green]Executing {len(QUEUED_PROMPTS)} queued prompts...[/bold green]")

        # Clear the queue after setting up configs
        QUEUED_PROMPTS.clear()

        # Return a special marker that the CLI will recognize
        # The actual execution will happen in the main CLI loop
        console.print(
            "[cyan]Prompts configured for parallel execution. Processing will begin now.[/cyan]"
        )

        return True

    def handle_queue(self, args: Optional[List[str]] = None) -> bool:
        """Queue a prompt for a specific agent.

        Args:
            args: [agent_key, prompt...]

        Returns:
            True if successful
        """
        if not args or len(args) < 2:
            console.print("[red]Error: Agent and prompt required[/red]")
            console.print("Usage: /run queue <agent_key> <prompt>")
            return False

        agent_key = args[0]
        prompt = " ".join(args[1:])

        # Validate agent exists
        available_agents = get_available_agents()
        if agent_key not in available_agents:
            console.print(f"[red]Error: Unknown agent '{agent_key}'[/red]")
            console.print("Available agents:")
            for key in available_agents:
                console.print(f"  • {key}")
            return False

        # Add to queue
        QUEUED_PROMPTS.append({"agent": agent_key, "prompt": prompt})

        agent_name = getattr(available_agents[agent_key], "name", agent_key)
        console.print(f"[green]Queued prompt for {agent_name}:[/green] {prompt[:50]}...")
        console.print(f"[dim]Total queued: {len(QUEUED_PROMPTS)}[/dim]")

        return True

    def handle_list(self, args: Optional[List[str]] = None) -> bool:
        """List all queued prompts.

        Args:
            args: Not used

        Returns:
            True
        """
        if not QUEUED_PROMPTS:
            console.print("[yellow]No prompts queued[/yellow]")
            return True

        table = Table(title="Queued Prompts for Parallel Execution")
        table.add_column("#", style="dim", width=3)
        table.add_column("Agent", style="cyan")
        table.add_column("Prompt", style="green")

        available_agents = get_available_agents()

        for idx, prompt_data in enumerate(QUEUED_PROMPTS, 1):
            agent_key = prompt_data["agent"]
            prompt = prompt_data["prompt"]

            # Get agent display name
            if agent_key in available_agents:
                agent_name = getattr(available_agents[agent_key], "name", agent_key)
            else:
                agent_name = agent_key

            # Truncate long prompts
            prompt_display = prompt[:60] + "..." if len(prompt) > 60 else prompt

            table.add_row(str(idx), agent_name, prompt_display)

        console.print(table)
        console.print(f"\n[bold]Total queued: {len(QUEUED_PROMPTS)}[/bold]")
        console.print("[dim]Use '/run' to execute all queued prompts[/dim]")

        return True

    def handle_clear(self, args: Optional[List[str]] = None) -> bool:
        """Clear all queued prompts.

        Args:
            args: Not used

        Returns:
            True
        """
        count = len(QUEUED_PROMPTS)
        QUEUED_PROMPTS.clear()

        console.print(f"[green]Cleared {count} queued prompts[/green]")
        return True

    def handle_remove(self, args: Optional[List[str]] = None) -> bool:
        """Remove a specific queued prompt by index.

        Args:
            args: [index]

        Returns:
            True if successful
        """
        if not args:
            console.print("[red]Error: Index required[/red]")
            console.print("Usage: /run remove <index>")
            return False

        try:
            idx = int(args[0])
            if idx < 1 or idx > len(QUEUED_PROMPTS):
                raise ValueError("Index out of range")

            removed = QUEUED_PROMPTS.pop(idx - 1)
            console.print(f"[green]Removed prompt:[/green] {removed['prompt'][:50]}...")
            return True
        except ValueError:
            console.print(f"[red]Error: Invalid index '{args[0]}'[/red]")
            return False


# Register the command
register_command(RunCommand())
