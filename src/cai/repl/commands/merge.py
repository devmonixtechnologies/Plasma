"""
Merge command for CAI CLI - alias for /parallel merge.

Provides a shortcut to merge agent message histories without
typing the full /parallel merge command.
"""

from typing import List, Optional

from rich.console import Console

from cai.repl.commands.base import Command, register_command
from cai.repl.commands.parallel import ParallelCommand

console = Console()


class MergeCommand(Command):
    """Command to merge agent message histories - alias for /parallel merge."""

    def __init__(self):
        """Initialize the merge command."""
        super().__init__(
            name="/merge",
            description="Merge all agents' message histories by default (alias for /parallel merge all)",
            aliases=["/mrg"],
        )
        # Create a ParallelCommand instance to delegate to
        self._parallel_cmd = ParallelCommand()

    def handle(self, args: Optional[List[str]] = None) -> bool:
        """Handle the merge command by delegating to /parallel merge.
        
        Args:
            args: Arguments to pass to the merge subcommand
            
        Returns:
            True if successful
        """
        if not args:
            # No arguments - merge all by default
            return self.handle_no_args()
        
        # Delegate to ParallelCommand's handle_merge method
        return self._parallel_cmd.handle_merge(args)

    def handle_no_args(self) -> bool:
        """Handle command with no arguments - merge all agents and show help."""
        from rich.panel import Panel
        
        # First, perform the merge all operation
        console.print("[cyan]Merging all agents by default...[/cyan]\n")
        merge_result = self._parallel_cmd.handle_merge(["all"])
        
        # Then show the help menu
        console.print("\n")
        help_text = """[bold cyan]Merge Command Help[/bold cyan]

[bold]Usage:[/bold]
  /merge                      → Merge all agents (default)
  /merge <agent1> <agent2>    → Merge specific agents
  /merge all                  → Explicitly merge all agents

[bold]Examples:[/bold]
  [green]/merge[/green]
    → Merges all agents' histories together (default behavior)
    
  [green]/merge P1 P2[/green]
    → Adds P2's messages to P1 and P1's messages to P2
    
  [green]/merge P1 P3 --target combined[/green]
    → Creates new 'combined' agent with merged history
    
  [green]/merge all --target unified --remove-sources[/green]
    → Creates 'unified' agent and removes source agents

[bold]Strategies:[/bold]
  [cyan]chronological[/cyan] - Merge by timestamp (default)
  [cyan]by-agent[/cyan]      - Group messages by agent
  [cyan]interleaved[/cyan]   - Preserve conversation flow

[bold]Options:[/bold]
  [yellow]--target NAME[/yellow]      - Create new agent instead of updating sources
  [yellow]--remove-sources[/yellow]   - Remove source agents after merging

[dim]Note: You can use agent IDs (P1, P2, etc.) instead of full agent names
Agent names with spaces are automatically detected[/dim]

[yellow]This is an alias for /parallel merge[/yellow]"""
        
        console.print(Panel(help_text, border_style="blue", padding=(1, 2)))
        
        return merge_result


# Register the command
register_command(MergeCommand())
