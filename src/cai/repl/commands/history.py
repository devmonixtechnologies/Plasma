"""
History command for CAI REPL.
This module provides commands for displaying conversation history with agent-based filtering.
"""

import json
from typing import Any, Dict, List, Optional

from rich.console import Console  # pylint: disable=import-error
from rich.panel import Panel  # pylint: disable=import-error
from rich.table import Table  # pylint: disable=import-error
from rich.tree import Tree  # pylint: disable=import-error

from cai.repl.commands.base import Command, register_command

console = Console()


class HistoryCommand(Command):
    """Command for displaying conversation history with agent filtering."""

    def __init__(self):
        """Initialize the history command."""
        super().__init__(
            name="/history",
            description="Display conversation history (optionally filtered by agent name)",
            aliases=["/his"],
        )

        # Add subcommands
        self.add_subcommand("all", "Show history from all agents", self.handle_all)
        self.add_subcommand("agent", "Show history for a specific agent", self.handle_agent)
        self.add_subcommand("search", "Search messages across all agents", self.handle_search)
        self.add_subcommand(
            "index", "Show message by index and optionally filter by role", self.handle_index
        )

    def handle(self, args: Optional[List[str]] = None) -> bool:
        """Handle the history command.

        Args:
            args: Command arguments - can be agent name, ID, or subcommand

        Returns:
            True if the command was handled successfully, False otherwise
        """
        if not args:
            # No arguments - show control panel with all agents
            return self.handle_control_panel()

        # Check if first arg is a subcommand
        subcommand = args[0].lower()
        if subcommand in self.subcommands:
            handler = self.subcommands[subcommand]["handler"]
            return handler(args[1:] if len(args) > 1 else [])

        # Check if it's an ID (P1, P2, etc.)
        first_arg = args[0]
        if first_arg.upper().startswith("P") and len(first_arg) >= 2 and first_arg[1:].isdigit():
            # Direct ID lookup
            return self.handle_agent(args)

        # Otherwise treat it as an agent name
        return self.handle_agent(args)

    def handle_control_panel(self) -> bool:
        """Show a control panel view of all agents and their message counts."""
        try:
            from cai.sdk.agents.models.openai_chatcompletions import get_all_agent_histories
            from cai.sdk.agents.simple_agent_manager import AGENT_MANAGER
            from cai.repl.commands.parallel import PARALLEL_CONFIGS
            from cai.agents import get_available_agents
            import os
        except ImportError:
            console.print("[red]Error: Could not access conversation history[/red]")
            return False

        # Get all histories from AGENT_MANAGER
        all_histories = AGENT_MANAGER.get_all_histories()
        registered_agents = AGENT_MANAGER.get_registered_agents()
        
        # Check if we're in parallel mode with isolation
        from cai.sdk.agents.parallel_isolation import PARALLEL_ISOLATION
        
        # Check if we have parallel configs AND isolated histories (don't rely on _parallel_mode flag)
        has_isolated_histories = len(PARALLEL_ISOLATION._isolated_histories) > 0
        
        # Clean up any duplicate registrations before displaying
        if PARALLEL_CONFIGS:
            # In parallel mode, ensure each ID is only registered to one agent
            id_to_correct_agent = {}
            for config in PARALLEL_CONFIGS:
                if config.id:
                    # Resolve the correct agent name for this config
                    if config.agent_name.endswith("_pattern"):
                        from cai.agents.patterns import get_pattern
                        pattern = get_pattern(config.agent_name)
                        if pattern and hasattr(pattern, 'entry_agent'):
                            correct_name = getattr(pattern.entry_agent, "name", config.agent_name)
                            id_to_correct_agent[config.id] = correct_name
                    else:
                        available_agents = get_available_agents()
                        if config.agent_name in available_agents:
                            agent = available_agents[config.agent_name]
                            correct_name = getattr(agent, "name", config.agent_name)
                            id_to_correct_agent[config.id] = correct_name
            
            # Remove any incorrect registrations
            for agent_name, agent_id in list(AGENT_MANAGER._agent_registry.items()):
                if agent_id in id_to_correct_agent and agent_name != id_to_correct_agent[agent_id]:
                    del AGENT_MANAGER._agent_registry[agent_name]
        
        if PARALLEL_CONFIGS and has_isolated_histories:
            # In parallel mode, we should primarily use isolated histories
            # Clear all_histories and rebuild from isolated histories
            all_histories = {}
            
            for idx, config in enumerate(PARALLEL_CONFIGS, 1):
                agent_id = config.id or f"P{idx}"
                
                isolated_history = PARALLEL_ISOLATION.get_isolated_history(agent_id)
                
                # Always create entry, even if history is empty
                if isolated_history is None:
                    isolated_history = []
                    
                # Find the display name for this agent
                available_agents = get_available_agents()
                if config.agent_name in available_agents:
                    agent = available_agents[config.agent_name]
                    display_name = getattr(agent, "name", config.agent_name)
                    
                    # Count instances for numbering
                    total_count = sum(1 for c in PARALLEL_CONFIGS if c.agent_name == config.agent_name)
                    if total_count > 1:
                        # Find instance number
                        instance_num = 0
                        for c in PARALLEL_CONFIGS:
                            if c.agent_name == config.agent_name:
                                instance_num += 1
                                if c.id == config.id:
                                    break
                        display_name = f"{display_name} #{instance_num}"
                    
                    # Add agent ID to display name
                    full_display_name = f"{display_name} [{agent_id}]"
                    all_histories[full_display_name] = isolated_history
        
        # Get the current agent from environment
        current_agent_type = os.getenv("CAI_AGENT_TYPE", "one_tool_agent")
        parallel_count = int(os.getenv("CAI_PARALLEL", "1"))
        
        # Create a unified view of all agents that should be shown
        agents_to_show = {}
        seen_agent_names = set()  # Track which agent names we've already added
        
        # First, add all registered agents from AGENT_MANAGER
        for display_name, history in all_histories.items():
            agents_to_show[display_name] = {
                'history': history,
                'source': 'manager',
                'is_registered': True
            }
            # Extract base name for tracking
            base_name = display_name.split(" [")[0] if "[" in display_name else display_name
            seen_agent_names.add(base_name)
        
        # If in parallel mode, ensure all configured agents are shown
        if parallel_count > 1 and PARALLEL_CONFIGS:
            available_agents = get_available_agents()
            
            # Count instances of each agent type for proper numbering
            agent_counts = {}
            for config in PARALLEL_CONFIGS:
                agent_counts[config.agent_name] = agent_counts.get(config.agent_name, 0) + 1
            
            agent_instances = {}
            
            for idx, config in enumerate(PARALLEL_CONFIGS, 1):
                if config.agent_name in available_agents:
                    agent = available_agents[config.agent_name]
                    base_name = getattr(agent, "name", config.agent_name)
                    
                    # Generate display name with instance number if needed
                    if agent_counts[config.agent_name] > 1:
                        if config.agent_name not in agent_instances:
                            agent_instances[config.agent_name] = 0
                        agent_instances[config.agent_name] += 1
                        full_display_name = f"{base_name} #{agent_instances[config.agent_name]}"
                    else:
                        full_display_name = base_name
                    
                    # Always use the ID from config
                    agent_id = config.id or f"P{idx}"
                    display_name = f"{full_display_name} [{agent_id}]"
                    
                    # Check if we already have this agent in our view
                    if display_name not in agents_to_show:
                        # Get history from AGENT_MANAGER if available
                        history = AGENT_MANAGER.get_message_history(base_name) or []
                        
                        agents_to_show[display_name] = {
                            'history': history,
                            'source': 'parallel_config',
                            'is_registered': base_name in registered_agents,
                            'config': config,
                            'agent_id': agent_id
                        }
        
        # If in single agent mode, ensure the current agent is shown
        elif parallel_count == 1:
            # Check if we should show the current agent
            current_agent = AGENT_MANAGER.get_active_agent()
            if current_agent:
                agent_name = getattr(current_agent, 'name', current_agent_type)
                agent_id = AGENT_MANAGER.get_agent_id()
                display_name = f"{agent_name} [{agent_id}]"
                
                if display_name not in agents_to_show:
                    history = AGENT_MANAGER.get_message_history(agent_name) or []
                    agents_to_show[display_name] = {
                        'history': history,
                        'source': 'active',
                        'is_registered': True
                    }
                    
                    # Also ensure this agent is properly registered in AGENT_MANAGER
                    # This handles the startup case where the agent might not be fully registered
                    if agent_id == "P1" and not AGENT_MANAGER.get_agent_by_id("P1"):
                        AGENT_MANAGER._agent_registry[agent_name] = "P1"
        
        if not agents_to_show:
            console.print("[yellow]No agents configured[/yellow]")
            console.print("[dim]Start a conversation or configure agents to see history[/dim]")
            return True
        
        # Create a tree view showing all agents
        tree = Tree(":robot: [bold cyan]Agent History Control Panel[/bold cyan]")
        
        total_messages = 0
        
        # Sort agents by ID for consistent display
        def get_sort_key(item):
            display_name = item[0]
            # Extract ID from display name
            if "[" in display_name and "]" in display_name:
                agent_id = display_name[display_name.rindex("[")+1:display_name.rindex("]")]
                # Sort P1, P2, etc. numerically
                if agent_id.startswith("P") and agent_id[1:].isdigit():
                    return (0, int(agent_id[1:]))
            return (1, display_name)
        
        # Show agents with their histories
        for display_name, agent_info in sorted(agents_to_show.items(), key=lambda x: get_sort_key(x)):
            history = agent_info['history']
            msg_count = len(history)
            total_messages += msg_count
            
            # Extract agent ID from display name
            agent_id = None
            if "[" in display_name and "]" in display_name:
                agent_id = display_name[display_name.rindex("[")+1:display_name.rindex("]")]
            
            # Determine status
            status_parts = []
            if msg_count == 0:
                status_parts.append("[yellow](no messages)[/yellow]")
            
            # Check if this agent is currently active
            is_current = False
            agent_base_name = display_name.split(" [")[0] if "[" in display_name else display_name
            
            # Remove instance number for comparison
            if " #" in agent_base_name:
                agent_base_name = agent_base_name.split(" #")[0]
            
            if parallel_count == 1:
                # In single agent mode, check if this is the active agent
                current_id = AGENT_MANAGER.get_agent_id()
                if agent_id == current_id:
                    is_current = True
            else:
                # In parallel mode, check if it's in the current parallel configs
                if agent_info.get('source') == 'parallel_config':
                    is_current = True
            
            if is_current:
                status_parts.append("[green](active)[/green]")
            elif agent_info.get('is_registered'):
                status_parts.append("[blue](registered)[/blue]")
            
            # Check for model override in config
            if 'config' in agent_info and agent_info['config'].model:
                status_parts.append(f"[blue](model: {agent_info['config'].model})[/blue]")
            
            status = " ".join(status_parts)
            
            # Count messages by role
            role_counts = {}
            for msg in history:
                role = msg.get("role", "unknown")
                role_counts[role] = role_counts.get(role, 0) + 1
            
            # Check if agent has applied memory
            base_agent_name = display_name.split(" [")[0] if "[" in display_name else display_name
            # Remove instance number for memory check
            if " #" in base_agent_name:
                base_agent_name = base_agent_name.split(" #")[0]
            
            # Import COMPACTED_SUMMARIES and APPLIED_MEMORY_IDS from compact module
            memory_indicator = ""
            try:
                from cai.repl.commands.memory import COMPACTED_SUMMARIES, APPLIED_MEMORY_IDS
                
                # Check if agent has a memory applied
                if base_agent_name in COMPACTED_SUMMARIES:
                    # Check if we have a stored memory ID for this agent
                    if base_agent_name in APPLIED_MEMORY_IDS:
                        memory_id = APPLIED_MEMORY_IDS[base_agent_name]
                        memory_indicator = f" [magenta](Memory: {memory_id})[/magenta]"
                    else:
                        memory_indicator = " [magenta](Memory: Applied)[/magenta]"
            except ImportError:
                pass
            
            # Create agent branch with appropriate styling
            if is_current:
                branch_text = f":robot: [bold cyan]{display_name}[/bold cyan] ({msg_count} messages) {status}{memory_indicator}"
            else:
                branch_text = f":gear: [green]{display_name}[/green] ({msg_count} messages) {status}{memory_indicator}"
            agent_branch = tree.add(branch_text)
            
            # Add role breakdown if there are messages
            if role_counts:
                for role, count in sorted(role_counts.items()):
                    role_style = {
                        "user": "cyan",
                        "assistant": "yellow",
                        "system": "blue",
                        "tool": "magenta",
                    }.get(role, "white")
                    agent_branch.add(f"[{role_style}]{role}[/{role_style}]: {count}")
            else:
                agent_branch.add(f"[dim]No messages yet[/dim]")
        
        console.print(tree)
        console.print(f"\n[bold]Total messages across all agents: {total_messages}[/bold]")
        
        # Show usage hints
        console.print("\n[dim]Commands:[/dim]")
        console.print("[dim]  • /history <ID>              - View specific agent by ID (e.g., P1)[/dim]")
        console.print("[dim]  • /history agent <name>      - View by agent name[/dim]")
        console.print("[dim]  • /history search <term>     - Search across all agents[/dim]")
        console.print("[dim]  • /history index <ID> <num>  - View specific message by index[/dim]")

        return True

    def handle_all(self, args: Optional[List[str]] = None) -> bool:
        """Show history from all agents in chronological order."""
        from cai.sdk.agents.simple_agent_manager import AGENT_MANAGER
        
        all_histories = AGENT_MANAGER.get_all_histories()

        if not all_histories:
            console.print("[yellow]No agents have conversation history[/yellow]")
            return True

        # Combine all messages with agent tags
        all_messages = []
        for display_name, history in all_histories.items():
            for msg in history:
                msg_copy = msg.copy()
                msg_copy["_agent"] = display_name
                all_messages.append(msg_copy)

        # Display in a table
        table = Table(title="All Agent Conversations", show_header=True, header_style="bold yellow")
        table.add_column("#", style="dim")
        table.add_column("Agent", style="magenta")
        table.add_column("Role", style="cyan")
        table.add_column("Content", style="green")

        for idx, msg in enumerate(all_messages, 1):
            agent_name = msg.get("_agent", "Unknown")
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls", None)

            # Create formatted content based on message type
            if role == "tool":
                # Format tool response with tool_call_id
                tool_call_id = msg.get("tool_call_id", "unknown")
                formatted_content = f"[dim]Tool ID: {tool_call_id}[/dim]\n{content[:300] if len(content) > 300 else content}"
            else:
                formatted_content = self._format_message_content(content, tool_calls)

            # Color the role based on type
            role_style = {
                "user": "cyan",
                "assistant": "yellow",
                "system": "blue",
                "tool": "magenta",
            }.get(role, "white")

            table.add_row(
                str(idx), agent_name, f"[{role_style}]{role}[/{role_style}]", formatted_content
            )

        console.print(table)
        return True

    def handle_agent(self, args: Optional[List[str]] = None) -> bool:
        """Show history for a specific agent."""
        if not args:
            console.print("[red]Error: Agent name or ID required[/red]")
            console.print("Usage: /history agent <agent_name>")
            console.print("       /history <ID>")
            return False

        # Join all args to handle agent names with spaces
        agent_identifier = " ".join(args)
        
        from cai.sdk.agents.simple_agent_manager import AGENT_MANAGER
        from cai.sdk.agents.parallel_isolation import PARALLEL_ISOLATION
        from cai.repl.commands.parallel import PARALLEL_CONFIGS
        
        agent_name = None
        agent_id = None
        history = None
        
        # First try direct ID lookup (P1, P2, etc.)
        if agent_identifier.upper().startswith("P") and len(agent_identifier) >= 2 and agent_identifier[1:].isdigit():
            agent_id = agent_identifier.upper()
            
            # Check if we're in parallel mode and have isolated history
            if PARALLEL_ISOLATION.is_parallel_mode() and PARALLEL_ISOLATION.has_isolated_histories():
                isolated_history = PARALLEL_ISOLATION.get_isolated_history(agent_id)
                if isolated_history is not None:
                    # Find the agent name from PARALLEL_CONFIGS
                    for idx, config in enumerate(PARALLEL_CONFIGS, 1):
                        config_id = config.id or f"P{idx}"
                        if config_id == agent_id:
                            from cai.agents import get_available_agents
                            available_agents = get_available_agents()
                            if config.agent_name in available_agents:
                                agent = available_agents[config.agent_name]
                                agent_name = getattr(agent, "name", config.agent_name)
                                # Add instance number if needed
                                total_count = sum(1 for c in PARALLEL_CONFIGS if c.agent_name == config.agent_name)
                                if total_count > 1:
                                    instance_num = 0
                                    for c in PARALLEL_CONFIGS:
                                        if c.agent_name == config.agent_name:
                                            instance_num += 1
                                            if c.id == config.id:
                                                break
                                    agent_name = f"{agent_name} #{instance_num}"
                                history = isolated_history
                                break
            
            # If not found in isolated histories, try AGENT_MANAGER
            if history is None:
                agent_name = AGENT_MANAGER.get_agent_by_id(agent_id)
                if agent_name:
                    history = AGENT_MANAGER.get_message_history(agent_name)
                else:
                    # Check if the current active agent has this ID (startup case)
                    current_agent = AGENT_MANAGER.get_active_agent()
                    current_id = AGENT_MANAGER.get_agent_id()
                    if current_agent and current_id == agent_id:
                        # Get the agent name from the agent object
                        agent_name = getattr(current_agent, 'name', 'Unknown')
                        history = AGENT_MANAGER.get_message_history(agent_name)
                        # Make sure this agent is registered in AGENT_MANAGER
                        if not AGENT_MANAGER.get_agent_by_id(agent_id):
                            # Register the current agent with its ID
                            AGENT_MANAGER._agent_registry[agent_name] = agent_id
                    else:
                        # Additional check: In single agent mode, if asking for P1 and we have an active agent
                        # This handles the case where the default agent is loaded but not yet fully registered
                        if agent_id == "P1" and not PARALLEL_CONFIGS:
                            current_agent = AGENT_MANAGER.get_active_agent()
                            if current_agent:
                                # Get the agent name and register it properly
                                agent_name = getattr(current_agent, 'name', 'Unknown')
                                # Force registration with P1 ID
                                AGENT_MANAGER._agent_registry[agent_name] = "P1"
                                AGENT_MANAGER._agent_id = "P1"
                                history = AGENT_MANAGER.get_message_history(agent_name)
                            else:
                                # Last resort: check if there's any agent with history in single agent mode
                                all_histories = AGENT_MANAGER._message_history
                                for name, hist in all_histories.items():
                                    if hist:  # Found an agent with history
                                        agent_name = name
                                        history = hist
                                        # Register it with P1
                                        AGENT_MANAGER._agent_registry[agent_name] = "P1"
                                        break
                                
                                if not history:
                                    console.print(f"[yellow]No agent found with ID '{agent_id}'[/yellow]")
                                    return True
                        else:
                            console.print(f"[yellow]No agent found with ID '{agent_id}'[/yellow]")
                            return True
        else:
            # Try to find by name in all histories
            all_histories = AGENT_MANAGER.get_all_histories()
            
            # First try exact match
            if agent_identifier in all_histories:
                agent_name = agent_identifier
                history = all_histories[agent_identifier]
            else:
                # Try to find by name in display format
                for display_name, history_data in all_histories.items():
                    # Extract agent name from display format "Agent Name [ID]"
                    if '[' in display_name:
                        name_part = display_name.split('[')[0].strip()
                        id_part = display_name[display_name.rindex("[")+1:display_name.rindex("]")]
                    else:
                        name_part = display_name
                        id_part = None
                    
                    if name_part.lower() == agent_identifier.lower():
                        agent_name = name_part
                        agent_id = id_part
                        history = history_data
                        break
        
        if not agent_name:
            console.print(f"[yellow]No agent found matching '{agent_identifier}'[/yellow]")
            return True

        # Always try to get history from AGENT_MANAGER to ensure consistency
        # This also satisfies test expectations
        if agent_name and history is None:
            manager_history = AGENT_MANAGER.get_message_history(agent_name)
            if manager_history is not None:
                history = manager_history

        if not history:
            # Get the agent ID if we don't have it
            if not agent_id:
                agent_id = AGENT_MANAGER.get_id_by_name(agent_name) or "Unknown"
            
            console.print(Panel(
                f"[yellow]No conversation history yet[/yellow]",
                title=f"[cyan]{agent_name} [{agent_id}][/cyan]",
                border_style="blue"
            ))
            return True
        
        # Get the agent ID if we don't have it
        if not agent_id:
            agent_id = AGENT_MANAGER.get_id_by_name(agent_name) or "Unknown"

        # Create a table for the history
        table = Table(
            title=f"Conversation History: {agent_name} [{agent_id}]",
            show_header=True,
            header_style="bold yellow",
        )
        table.add_column("#", style="dim")
        table.add_column("Role", style="cyan")
        table.add_column("Content", style="green")

        # Add messages to the table
        for idx, msg in enumerate(history, 1):
            try:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                tool_calls = msg.get("tool_calls", None)

                # Create formatted content based on message type
                if role == "tool":
                    # Format tool response with tool_call_id
                    tool_call_id = msg.get("tool_call_id", "unknown")
                    # Try to find the corresponding tool call in previous messages
                    tool_name = "unknown_tool"
                    for prev_msg in history[: idx - 1]:
                        if prev_msg.get("role") == "assistant" and prev_msg.get("tool_calls"):
                            for tc in prev_msg.get("tool_calls", []):
                                if tc.get("id") == tool_call_id:
                                    tool_name = tc.get("function", {}).get("name", "unknown_tool")
                                    break
                    formatted_content = f"[dim]Tool: {tool_name} (ID: {tool_call_id})[/dim]\n{content[:500] if len(content) > 500 else content}"
                else:
                    formatted_content = self._format_message_content(content, tool_calls)

                # Color the role based on type
                role_style = {
                    "user": "cyan",
                    "assistant": "yellow",
                    "system": "blue",
                    "tool": "magenta",
                }.get(role, "white")

                # Add a newline between each role for better readability
                if idx > 1:
                    table.add_row("", "", "")

                table.add_row(str(idx), f"[{role_style}]{role}[/{role_style}]", formatted_content)
            except Exception as e:
                # Log error but continue with next message
                console.print(f"[red]Error displaying message {idx}: {e}[/red]")
                continue

        console.print(table)
        return True

    def handle_search(self, args: Optional[List[str]] = None) -> bool:
        """Search for messages containing specific terms across all agents."""
        if not args:
            console.print("[red]Error: Search term required[/red]")
            console.print("Usage: /history search <search_term>")
            return False

        search_term = " ".join(args).lower()

        from cai.sdk.agents.simple_agent_manager import AGENT_MANAGER
        
        all_histories = AGENT_MANAGER.get_all_histories()

        if not all_histories:
            console.print("[yellow]No agents have conversation history[/yellow]")
            return True

        # Search across all agents
        found_messages = []
        for display_name, history in all_histories.items():
            for idx, msg in enumerate(history):
                content = str(msg.get("content", "")).lower()
                tool_calls = msg.get("tool_calls", [])

                # Search in content
                if search_term in content:
                    found_messages.append((display_name, idx + 1, msg))
                    continue

                # Search in tool calls
                if tool_calls:
                    for tc in tool_calls:
                        func_details = tc.get("function", {})
                        func_name = func_details.get("name", "").lower()
                        func_args = str(func_details.get("arguments", "")).lower()

                        if search_term in func_name or search_term in func_args:
                            found_messages.append((display_name, idx + 1, msg))
                            break

        if not found_messages:
            console.print(f"[yellow]No messages found containing '{search_term}'[/yellow]")
            return True

        # Display search results
        console.print(
            f"\n[bold green]Found {len(found_messages)} messages containing '{search_term}':[/bold green]\n"
        )

        for agent_name, msg_idx, msg in found_messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls", None)

            # Create formatted content based on message type
            if role == "tool":
                # Format tool response with tool_call_id
                tool_call_id = msg.get("tool_call_id", "unknown")
                formatted_content = f"[dim]Tool ID: {tool_call_id}[/dim]\n{content}"
            else:
                formatted_content = self._format_message_content(content, tool_calls)

            # Highlight search term
            highlighted_content = formatted_content.replace(
                search_term, f"[bold red]{search_term}[/bold red]"
            ).replace(search_term.capitalize(), f"[bold red]{search_term.capitalize()}[/bold red]")

            panel = Panel(
                highlighted_content,
                title=f"[cyan]{agent_name}[/cyan] - Message #{msg_idx} ({role})",
                border_style="blue",
            )
            console.print(panel)

        return True

    def _format_message_content(self, content: Any, tool_calls: List[Dict[str, Any]]) -> str:
        """Format message content for display, handling both text and tool calls.

        Args:
            content: Text content of the message
            tool_calls: List of tool calls if present

        Returns:
            Formatted string representation of the message content
        """
        if tool_calls:
            # Format tool calls into a readable string
            result = []
            for tc in tool_calls:
                func_details = tc.get("function", {})
                func_name = func_details.get("name", "unknown_function")

                # Format arguments (pretty-print JSON if possible)
                args_str = func_details.get("arguments", "{}")
                try:
                    # Parse and re-format JSON for better readability
                    args_dict = json.loads(args_str)
                    args_formatted = json.dumps(args_dict, indent=2)
                    # Limit to first 200 chars for display
                    if len(args_formatted) > 200:
                        args_formatted = args_formatted[:197] + "..."
                except (json.JSONDecodeError, TypeError):
                    # If not valid JSON, use as is
                    args_formatted = args_str
                    if len(args_formatted) > 200:
                        args_formatted = args_formatted[:197] + "..."

                result.append(f"Function: [bold blue]{func_name}[/bold blue]")
                result.append(f"Args: {args_formatted}")

            return "\n".join(result)
        elif content:
            # Regular text content (truncate if too long)
            if len(content) > 300:
                return content[:297] + "..."
            return content
        else:
            # No content or tool calls (empty message)
            return "[dim italic]Empty message[/dim italic]"

    def handle_index(self, args: Optional[List[str]] = None) -> bool:
        """Show message by index and optionally filter by role.

        Usage: /history index <agent_name> <index> [role]
        """
        if not args or len(args) < 2:
            console.print("[red]Error: Agent name and index required[/red]")
            console.print("Usage: /history index <agent_name> <index> [role]")
            console.print("Example: /history index red_teamer 5")
            console.print('Example: /history index "Bug Bounter #1" 5 user')
            return False

        # Find where the index is (it should be a number)
        index_pos = -1
        for i, arg in enumerate(args):
            if arg.isdigit():
                index_pos = i
                break

        if index_pos < 1:  # Need at least one arg before the index for agent name
            console.print("[red]Error: Could not parse agent name and index[/red]")
            return False

        # Agent name is everything before the index
        agent_name = " ".join(args[:index_pos])

        try:
            index = int(args[index_pos]) - 1  # Convert to 0-based index
            if index < 0:
                console.print("[red]Error: Index must be positive[/red]")
                return False
        except ValueError:
            console.print("[red]Error: Invalid index number[/red]")
            return False

        role_filter = args[index_pos + 1].lower() if len(args) > index_pos + 1 else None

        from cai.sdk.agents.simple_agent_manager import AGENT_MANAGER
        
        # Get agent name by ID if an ID was provided
        if agent_name.upper().startswith("P") and len(agent_name) >= 2 and agent_name[1:].isdigit():
            agent_id = agent_name.upper()
            real_agent_name = AGENT_MANAGER.get_agent_by_id(agent_id)
            if real_agent_name:
                agent_name = real_agent_name
            else:
                console.print(f"[yellow]No agent found with ID '{agent_id}'[/yellow]")
                return True

        history = AGENT_MANAGER.get_message_history(agent_name)

        if not history:
            console.print(f"[yellow]No conversation history for agent '{agent_name}'[/yellow]")
            return True

        # Filter by role if specified
        if role_filter:
            filtered_messages = [
                (i, msg)
                for i, msg in enumerate(history)
                if msg.get("role", "").lower() == role_filter
            ]
            if not filtered_messages:
                console.print(f"[yellow]No messages with role '{role_filter}' found[/yellow]")
                return True

            # Check if index is valid for filtered messages
            if index >= len(filtered_messages):
                console.print(
                    f"[red]Error: Index {index + 1} out of range. "
                    f"Agent '{agent_name}' has {len(filtered_messages)} "
                    f"messages with role '{role_filter}'[/red]"
                )
                return False

            original_index, msg = filtered_messages[index]
            display_index = original_index + 1
        else:
            # No role filter
            if index >= len(history):
                console.print(
                    f"[red]Error: Index {index + 1} out of range. "
                    f"Agent '{agent_name}' has {len(history)} messages[/red]"
                )
                return False

            msg = history[index]
            display_index = index + 1

        # Display the message
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        tool_calls = msg.get("tool_calls", None)

        # Create formatted content based on message type
        if role == "tool":
            tool_call_id = msg.get("tool_call_id", "unknown")
            # Try to find the corresponding tool call
            tool_name = "unknown_tool"
            for i in range(index):
                prev_msg = history[i]
                if prev_msg.get("role") == "assistant" and prev_msg.get("tool_calls"):
                    for tc in prev_msg.get("tool_calls", []):
                        if tc.get("id") == tool_call_id:
                            tool_name = tc.get("function", {}).get("name", "unknown_tool")
                            break
            formatted_content = f"[dim]Tool: {tool_name} (ID: {tool_call_id})[/dim]\n{content}"
        else:
            formatted_content = self._format_message_content(content, tool_calls)

        # Color the role based on type
        role_style = {
            "user": "cyan",
            "assistant": "yellow",
            "system": "blue",
            "tool": "magenta",
        }.get(role, "white")

        # Create a panel for the single message
        panel = Panel(
            formatted_content,
            title=f"[cyan]{agent_name}[/cyan] - Message #{display_index} ([{role_style}]{role}[/{role_style}])",
            border_style="blue",
        )
        console.print(panel)

        return True


# Register the command
register_command(HistoryCommand())
