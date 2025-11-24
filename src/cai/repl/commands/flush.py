"""
Flush command for CAI REPL.
This module provides commands for clearing conversation history.
"""

import os
from typing import Dict, List, Optional

from rich.console import Console  # pylint: disable=import-error
from rich.panel import Panel  # pylint: disable=import-error

from cai.repl.commands.base import Command, register_command

console = Console()


class FlushCommand(Command):
    """Command to flush the conversation history."""

    def __init__(self):
        """Initialize the flush command."""
        super().__init__(
            name="/flush",
            description="Clear conversation history (all agents by default, or specific agent)",
            aliases=["/clear"],
        )

        # Add subcommands
        self.add_subcommand("all", "Clear history for all agents", self.handle_all)
        self.add_subcommand("agent", "Clear history for a specific agent", self.handle_agent)

    def handle(
        self, args: Optional[List[str]] = None, messages: Optional[List[Dict]] = None
    ) -> bool:
        """Handle the flush command.

        Args:
            args: Command arguments - can be agent name or subcommand
            messages: Optional list of conversation messages (legacy, ignored)

        Returns:
            True if the command was handled successfully
        """
        if not args:
            # No arguments - flush all histories like "/flush all"
            return self.handle_all([])

        # Check if first arg is "all" (special case)
        if args[0].lower() == "all":
            return self.handle_all(args[1:] if len(args) > 1 else [])
        
        # Check if first arg is "agent" subcommand
        if args[0].lower() == "agent":
            return self.handle_agent(args[1:] if len(args) > 1 else [])

        # Otherwise treat it as an agent name
        return self.handle_specific_agent(args)

    def handle_current_agent(self) -> bool:
        """Clear history for the current agent."""
        # Try to get current agent name from environment or default
        current_agent = os.getenv("CAI_CURRENT_AGENT", "Current Agent")

        try:
            from cai.sdk.agents.models.openai_chatcompletions import (
                clear_agent_history,
                get_agent_message_history,
            )
        except ImportError:
            console.print("[red]Error: Could not access conversation history[/red]")
            return False

        # Get initial length before clearing
        history = get_agent_message_history(current_agent)
        initial_length = len(history)

        # Clear the history
        clear_agent_history(current_agent)

        # Display information about the cleared messages
        if initial_length > 0:
            content = [
                f"Conversation history cleared for {current_agent}.",
                f"Removed {initial_length} messages.",
            ]

            console.print(
                Panel(
                    "\n".join(content),
                    title=f"[bold cyan]Context Flushed - {current_agent}[/bold cyan]",
                    border_style="blue",
                    padding=(1, 2),
                )
            )
        else:
            console.print(
                Panel(
                    f"No conversation history to clear for {current_agent}.",
                    title=f"[bold cyan]Context Flushed - {current_agent}[/bold cyan]",
                    border_style="blue",
                    padding=(1, 2),
                )
            )

        return True

    def handle_all(self, args: Optional[List[str]] = None) -> bool:
        """Clear history for all agents."""
        try:
            from cai.sdk.agents.models.openai_chatcompletions import (
                clear_all_histories,
                get_all_agent_histories,
                ACTIVE_MODEL_INSTANCES,
            )
        except ImportError:
            console.print("[red]Error: Could not access conversation history[/red]")
            return False

        # Get agent count and total messages before clearing
        all_histories = get_all_agent_histories()
        agent_count = len(all_histories)
        total_messages = sum(len(history) for history in all_histories.values())

        # Also count parallel isolation histories
        from cai.sdk.agents.parallel_isolation import PARALLEL_ISOLATION
        if PARALLEL_ISOLATION.is_parallel_mode():
            for agent_id, history in PARALLEL_ISOLATION._isolated_histories.items():
                if history:
                    agent_count += 1
                    total_messages += len(history)

        # Clear all histories from AGENT_MANAGER
        clear_all_histories()
        
        # Clear parallel isolation histories
        PARALLEL_ISOLATION.clear_all_histories()
        
        # Clear histories from all active model instances
        for key, model_ref in list(ACTIVE_MODEL_INSTANCES.items()):
            model = model_ref() if callable(model_ref) else model_ref
            if model and hasattr(model, 'message_history'):
                model.message_history.clear()

        # Display information
        if agent_count > 0:
            content = [
                f"Cleared history for all {agent_count} agents.",
                f"Total messages removed: {total_messages}",
            ]

            console.print(
                Panel(
                    "\n".join(content),
                    title="[bold cyan]All Contexts Flushed[/bold cyan]",
                    border_style="blue",
                    padding=(1, 2),
                )
            )
        else:
            console.print(
                Panel(
                    "No agent histories to clear.",
                    title="[bold cyan]All Contexts Flushed[/bold cyan]",
                    border_style="blue",
                    padding=(1, 2),
                )
            )

        return True

    def handle_agent(self, args: Optional[List[str]] = None) -> bool:
        """Clear history for a specific agent using 'agent' subcommand."""
        if not args:
            console.print("[red]Error: Agent name required[/red]")
            console.print("Usage: /flush agent <agent_name>")
            return False

        # Join all args to handle agent names with spaces
        agent_name = " ".join(args)
        return self._clear_agent(agent_name)
    
    def handle_specific_agent(self, args: List[str]) -> bool:
        """Clear history for a specific agent (direct syntax)."""
        # Check if first arg is an ID
        identifier = args[0]
        
        if identifier.upper().startswith("P") and len(identifier) >= 2 and identifier[1:].isdigit():
            # Clear by ID directly for parallel agents
            from cai.sdk.agents.parallel_isolation import PARALLEL_ISOLATION
            from cai.sdk.agents.models.openai_chatcompletions import ACTIVE_MODEL_INSTANCES
            
            agent_id = identifier.upper()
            
            # Get the history length before clearing
            initial_length = 0
            isolated_history = PARALLEL_ISOLATION.get_isolated_history(agent_id)
            if isolated_history:
                initial_length = len(isolated_history)
            
            # Clear from parallel isolation
            PARALLEL_ISOLATION.clear_agent_history(agent_id)
            
            # Clear from any active model instances with this agent_id
            for key, model_ref in list(ACTIVE_MODEL_INSTANCES.items()):
                if key[1] == agent_id:  # key is (agent_name, agent_id)
                    model = model_ref() if callable(model_ref) else model_ref
                    if model and hasattr(model, 'message_history'):
                        model.message_history.clear()
            
            # Get agent name for display
            agent_name = f"Agent {agent_id}"
            from cai.repl.commands.parallel import PARALLEL_CONFIGS
            from cai.agents import get_available_agents
            
            available_agents = get_available_agents()
            for config in PARALLEL_CONFIGS:
                if config.id and config.id == agent_id:
                    if config.agent_name in available_agents:
                        agent = available_agents[config.agent_name]
                        display_name = getattr(agent, "name", config.agent_name)
                        
                        # Count instances to get the right name
                        instance_num = 0
                        for c in PARALLEL_CONFIGS:
                            if c.agent_name == config.agent_name:
                                instance_num += 1
                                if c.id == config.id:
                                    break
                        
                        # Add instance number if there are duplicates
                        if sum(1 for c in PARALLEL_CONFIGS if c.agent_name == config.agent_name) > 1:
                            agent_name = f"{display_name} #{instance_num} [{agent_id}]"
                        else:
                            agent_name = f"{display_name} [{agent_id}]"
                        break
            
            # Display information
            if initial_length > 0:
                content = [
                    f"Conversation history cleared for {agent_name}.",
                    f"Removed {initial_length} messages.",
                ]

                console.print(
                    Panel(
                        "\n".join(content),
                        title=f"[bold cyan]Context Flushed - {agent_name}[/bold cyan]",
                        border_style="blue",
                        padding=(1, 2),
                    )
                )
            else:
                console.print(
                    Panel(
                        f"No conversation history to clear for {agent_name}.",
                        title=f"[bold cyan]Context Flushed - {agent_name}[/bold cyan]",
                        border_style="blue",
                        padding=(1, 2),
                    )
                )
            
            return True
        else:
            # Join all args to handle agent names with spaces
            agent_name = " ".join(args)
            return self._clear_agent(agent_name)
    
    def _clear_agent(self, agent_name: str) -> bool:
        """Common method to clear a specific agent's history."""
        try:
            from cai.sdk.agents.models.openai_chatcompletions import (
                clear_agent_history,
                get_agent_message_history,
                ACTIVE_MODEL_INSTANCES,
            )
        except ImportError:
            console.print("[red]Error: Could not access conversation history[/red]")
            return False

        # Get initial length before clearing
        history = get_agent_message_history(agent_name)
        initial_length = len(history)

        # Clear the history from AGENT_MANAGER
        clear_agent_history(agent_name)
        
        # Also clear from parallel isolation if present
        from cai.sdk.agents.parallel_isolation import PARALLEL_ISOLATION
        from cai.repl.commands.parallel import PARALLEL_CONFIGS
        
        # Find if this agent is in parallel configs and clear by ID
        cleared_from_parallel = False
        for idx, config in enumerate(PARALLEL_CONFIGS, 1):
            agent_id = config.id or f"P{idx}"
            # Check if the agent name matches
            from cai.agents import get_available_agents
            available = get_available_agents()
            if config.agent_name in available:
                agent_obj = available[config.agent_name]
                display_name = getattr(agent_obj, "name", config.agent_name)
                
                # Count instances to get correct numbering
                instance_num = 0
                for c in PARALLEL_CONFIGS[:idx]:
                    if c.agent_name == config.agent_name:
                        instance_num += 1
                instance_num += 1  # Current instance
                
                # Build the instance name
                if sum(1 for c in PARALLEL_CONFIGS if c.agent_name == config.agent_name) > 1:
                    instance_name = f"{display_name} #{instance_num}"
                else:
                    instance_name = display_name
                
                if agent_name == display_name or agent_name == instance_name:
                    # Clear from parallel isolation
                    isolated_history = PARALLEL_ISOLATION.get_isolated_history(agent_id)
                    if isolated_history:
                        initial_length = max(initial_length, len(isolated_history))
                    PARALLEL_ISOLATION.clear_agent_history(agent_id)
                    cleared_from_parallel = True
                    
                    # Also clear from any active model instances with this agent_id
                    for key, model_ref in list(ACTIVE_MODEL_INSTANCES.items()):
                        if key[1] == agent_id:  # key is (agent_name, agent_id)
                            model = model_ref() if callable(model_ref) else model_ref
                            if model and hasattr(model, 'message_history'):
                                model.message_history.clear()
                    break

        # If not cleared from parallel, check if it's a parallel agent by ID in agent name
        if not cleared_from_parallel and "[P" in agent_name and agent_name.endswith("]"):
            # Extract ID from agent name like "Agent Name [P1]"
            agent_id = agent_name.split("[P")[-1].rstrip("]")
            agent_id = f"P{agent_id}"
            isolated_history = PARALLEL_ISOLATION.get_isolated_history(agent_id)
            if isolated_history:
                initial_length = max(initial_length, len(isolated_history))
                PARALLEL_ISOLATION.clear_agent_history(agent_id)

        # Display information
        if initial_length > 0:
            content = [
                f"Conversation history cleared for {agent_name}.",
                f"Removed {initial_length} messages.",
            ]

            console.print(
                Panel(
                    "\n".join(content),
                    title=f"[bold cyan]Context Flushed - {agent_name}[/bold cyan]",
                    border_style="blue",
                    padding=(1, 2),
                )
            )
        else:
            console.print(
                Panel(
                    f"No conversation history to clear for {agent_name}.",
                    title=f"[bold cyan]Context Flushed - {agent_name}[/bold cyan]",
                    border_style="blue",
                    padding=(1, 2),
                )
            )

        return True
    
    def show_flush_help(self) -> bool:
        """Show help menu with available agents to flush."""
        try:
            from cai.sdk.agents.models.openai_chatcompletions import get_all_agent_histories
        except ImportError:
            console.print("[red]Error: Could not access conversation history[/red]")
            return False
        
        all_histories = get_all_agent_histories()
        
        # Also get parallel isolation histories
        from cai.sdk.agents.parallel_isolation import PARALLEL_ISOLATION
        parallel_histories = {}
        if PARALLEL_ISOLATION.is_parallel_mode():
            for agent_id, history in PARALLEL_ISOLATION._isolated_histories.items():
                if history:
                    # Try to get agent name from PARALLEL_CONFIGS
                    from cai.repl.commands.parallel import PARALLEL_CONFIGS
                    agent_name = f"Unknown Agent {agent_id}"
                    for config in PARALLEL_CONFIGS:
                        if config.id == agent_id:
                            from cai.agents import get_available_agents
                            available = get_available_agents()
                            if config.agent_name in available:
                                agent_obj = available[config.agent_name]
                                display_name = getattr(agent_obj, "name", config.agent_name)
                                # Get instance number
                                instance_num = 0
                                for c in PARALLEL_CONFIGS:
                                    if c.agent_name == config.agent_name:
                                        instance_num += 1
                                        if c.id == config.id:
                                            break
                                if sum(1 for c in PARALLEL_CONFIGS if c.agent_name == config.agent_name) > 1:
                                    agent_name = f"{display_name} #{instance_num}"
                                else:
                                    agent_name = display_name
                                break
                    parallel_histories[f"{agent_name} [{agent_id}]"] = history
        
        # Combine all histories
        combined_histories = dict(all_histories)
        combined_histories.update(parallel_histories)
        
        if not combined_histories:
            console.print("[yellow]No agents have conversation history to clear[/yellow]")
            console.print("\n[dim]Usage:[/dim]")
            console.print("[dim]  /flush <agent_name>  - Clear specific agent's history[/dim]")
            console.print("[dim]  /flush all           - Clear all agents' histories[/dim]")
            return True
        
        # Get IDs for agents if available
        from cai.repl.commands.parallel import PARALLEL_CONFIGS
        from cai.agents import get_available_agents
        
        agent_ids = {}
        if PARALLEL_CONFIGS:
            available_agents = get_available_agents()
            for config in PARALLEL_CONFIGS:
                if config.agent_name in available_agents:
                    agent = available_agents[config.agent_name]
                    display_name = getattr(agent, "name", config.agent_name)
                    
                    # Count instances to get the right name
                    total_count = sum(1 for c in PARALLEL_CONFIGS if c.agent_name == config.agent_name)
                    instance_num = 0
                    for c in PARALLEL_CONFIGS:
                        if c.agent_name == config.agent_name:
                            instance_num += 1
                            if c.id == config.id:
                                break
                    
                    # Add instance number if there are duplicates
                    if total_count > 1:
                        full_name = f"{display_name} #{instance_num}"
                    else:
                        full_name = display_name
                    
                    agent_ids[full_name] = config.id
        
        # Create a panel showing available agents
        from rich.tree import Tree
        
        tree = Tree(":wastebasket: [bold cyan]Flush Command - Available Agents[/bold cyan]")
        
        total_messages = 0
        for agent_name, history in sorted(combined_histories.items()):
            msg_count = len(history)
            total_messages += msg_count
            
            # Get ID for this agent (if it's not already in the name)
            if "[P" in agent_name and agent_name.endswith("]"):
                id_str = ""  # ID already in name
            else:
                id_str = f" [{agent_ids.get(agent_name, '')}]" if agent_name in agent_ids else ""
            
            # Add agent to tree
            if msg_count > 0:
                tree.add(f":robot: [bold green]{agent_name}{id_str}[/bold green] ({msg_count} messages)")
            else:
                tree.add(f":robot: [dim]{agent_name}{id_str}[/dim] (no messages)")
        
        console.print(tree)
        console.print(f"\n[bold]Total messages across all agents: {total_messages}[/bold]")
        
        console.print("\n[bold cyan]Usage:[/bold cyan]")
        console.print("  /flush <agent_name>  - Clear specific agent's history")
        console.print("  /flush <ID>          - Clear agent by ID (e.g., /flush P2)")
        console.print("  /flush all           - Clear all agents' histories")
        console.print("  /flush agent <name>  - Clear specific agent (explicit syntax)")
        
        # Show example for agents with spaces
        agents_with_spaces = [name for name in all_histories.keys() if " " in name]
        if agents_with_spaces:
            console.print("\n[dim]Examples for agents with spaces:[/dim]")
            for agent in agents_with_spaces[:2]:  # Show max 2 examples
                id_str = f" (or /flush {agent_ids[agent]})" if agent in agent_ids else ""
                console.print(f'[dim]  /flush {agent}{id_str}[/dim]')
        
        return True

    def handle_no_args(self, messages: Optional[List[Dict]] = None) -> bool:
        """Legacy method for backward compatibility."""
        return self.handle_current_agent()

    def _get_client(self):
        """Get the CAI client from the global namespace.

        This function avoids circular imports by accessing the client
        at runtime instead of import time.

        Returns:
            The global CAI client instance or None if not available
        """
        try:
            # Import here to avoid circular import
            from cai.repl.repl import (
                client as global_client,  # pylint: disable=import-outside-toplevel # noqa: E501
            )

            return global_client
        except (ImportError, AttributeError):
            return None


# Register the /flush command
register_command(FlushCommand())
