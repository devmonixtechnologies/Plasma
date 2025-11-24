"""
Agent "command" for CAI CLI abstraction

Provides commands for managing and switching between agents.
"""

# Standard library imports
import os
from typing import List, Optional

# Third-party imports
from rich.console import Console  # pylint: disable=import-error
from rich.markdown import Markdown  # pylint: disable=import-error
from rich.table import Table  # pylint: disable=import-error

# Local imports
from cai.agents import get_agent_module, get_available_agents
from cai.repl.commands.base import Command, register_command
from cai.sdk.agents import Agent
from cai.util import visualize_agent_graph

console = Console()


class AgentCommand(Command):
    """Command for managing and switching between agents."""

    def __init__(self):
        """Initialize the agent command."""
        # Initialize with basic parameters
        super().__init__(
            name="/agent", description="Manage and switch between agents", aliases=["/a"]
        )

        # Add subcommands manually
        self._subcommands = {
            "list": "List available agents",
            "select": "Select an agent by name or number",
            "info": "Show information about an agent",
            "multi": "Enable multi-agent mode",
            "current": "Show current agent configuration",
        }

    def _get_model_display(self, agent_name: str, agent: Agent) -> str:
        """Get the display string for an agent's model.

        Args:
            agent_name: Name of the agent
            agent: Agent instance

        Returns:
            String to display for the agent's model
        """
        # For code agent, always show the model
        if agent_name == "code":
            return agent.model

        # For other agents, check if CTF_MODEL is set
        ctf_model = os.getenv("CTF_MODEL")
        if ctf_model and agent.model == ctf_model:
            # Don't show default model for CTF_MODEL in table
            # but show "Default CTF Model" in info
            return ""

        # Show the model from environment variable if available
        env_var_name = f"CAI_{agent_name.upper()}_MODEL"
        model_env = os.getenv(env_var_name)
        if model_env:
            return model_env

        return agent.model

    def _get_model_display_for_info(self, agent_name: str, agent: Agent) -> str:
        """Get the display string for an agent's model in the info view.

        Args:
            agent_name: Name of the agent
            agent: Agent instance

        Returns:
            String to display for the agent's model in the info view
        """
        # For code agent, always show the model
        if agent_name == "code":
            return agent.model

        # For other agents, check if CTF_MODEL is set
        ctf_model = os.getenv("CTF_MODEL")
        if ctf_model and agent.model == ctf_model:
            # Show "Default CTF Model" in info
            return "Default CTF Model"

        # Show the model from environment variable if available
        env_var_name = f"CAI_{agent_name.upper()}_MODEL"
        model_env = os.getenv(env_var_name)
        if model_env:
            return model_env

        return agent.model

    def get_subcommands(self) -> List[str]:
        """Get list of subcommand names.

        Returns:
            List of subcommand names
        """
        return list(self._subcommands.keys())

    def get_subcommand_description(self, subcommand: str) -> str:
        """Get description for a subcommand.

        Args:
            subcommand: Name of the subcommand

        Returns:
            Description of the subcommand
        """
        return self._subcommands.get(subcommand, "")

    def handle(self, args: Optional[List[str]] = None) -> bool:
        """Handle the agent command.

        Args:
            args: Optional list of command arguments

        Returns:
            True if the command was handled successfully, False otherwise
        """
        if not args:
            return self.handle_current(args)

        subcommand = args[0]
        if subcommand in self._subcommands:
            handler = getattr(self, f"handle_{subcommand}", None)
            if handler:
                return handler(args[1:] if len(args) > 1 else None)

        # If not a subcommand, try to select an agent by name
        return self.handle_select(args)

    def handle_list(self, args: Optional[List[str]] = None) -> bool:  # pylint: disable=unused-argument # noqa: E501
        """Handle /agent list command.

        Args:
            args: Optional list of command arguments (not used)

        Returns:
            True if the command was handled successfully
        """
        # Create agents table
        agents_table = Table(title="Available Agents")
        agents_table.add_column("#", style="dim")
        agents_table.add_column("Name", style="cyan")
        agents_table.add_column("Key", style="magenta")
        agents_table.add_column("Module", style="green")
        agents_table.add_column("Description", style="green")

        # Retrieve all registered agents
        agents_to_display = get_available_agents()

        # Filter out ONLY parallel pattern pseudo-agents before displaying
        actual_idx = 1
        for agent_key, agent in agents_to_display.items():
            # Skip only parallel patterns in the main table
            if hasattr(agent, "_pattern"):
                pattern = agent._pattern
                if hasattr(pattern, "type"):
                    pattern_type_value = getattr(pattern.type, 'value', str(pattern.type))
                    if pattern_type_value == "parallel":
                        continue
                
            # Human-friendly name (falls back to the dict key)
            display_name = getattr(agent, "name", agent_key)

            # Use provided description, otherwise derive from instructions
            description = getattr(agent, "description", "") or ""
            if not description and hasattr(agent, "instructions"):
                instr = agent.instructions
                description = instr(context_variables={}) if callable(instr) else instr
            if isinstance(description, str):
                description = " ".join(description.split())
                # Extended description to show at least 200 characters
                if len(description) > 200:
                    description = description[:197] + "..."

            # Module where this agent lives
            module_name = get_agent_module(agent_key)

            # Add a row with all collected info
            agents_table.add_row(str(actual_idx), display_name, agent_key, module_name, description)
            actual_idx += 1

        console.print(agents_table)
        
        # Create patterns table with IDs - filter for parallel patterns only
        patterns_in_agents = [(k, v) for k, v in agents_to_display.items() if hasattr(v, "_pattern")]
        
        # Filter for parallel patterns only
        parallel_patterns = []
        for k, v in patterns_in_agents:
            pattern = v._pattern
            # Check if it's a parallel pattern
            if hasattr(pattern, "type"):
                pattern_type_value = getattr(pattern.type, 'value', str(pattern.type))
                if pattern_type_value == "parallel":
                    parallel_patterns.append((k, v))
        
        if parallel_patterns:
            patterns_table = Table(title="Available Parallel Patterns")
            patterns_table.add_column("#", style="dim")
            patterns_table.add_column("Name", style="cyan")
            patterns_table.add_column("Type", style="yellow")
            patterns_table.add_column("Key", style="magenta")
            patterns_table.add_column("Module", style="green")
            patterns_table.add_column("Description", style="green")
            
            # Start numbering after regular agents - use actual_idx which tracks displayed agents
            pattern_start_idx = actual_idx
            
            for idx, (pattern_key, pattern_agent) in enumerate(parallel_patterns, pattern_start_idx):
                pattern = pattern_agent._pattern
                
                # Pattern display name (from pattern object)
                pattern_display_name = getattr(pattern, "name", pattern_key)
                
                # Pattern type
                pattern_type = getattr(pattern_agent, "pattern_type", "unknown")
                
                # Pattern description
                description = str(getattr(pattern, "description", ""))
                if isinstance(description, str):
                    description = " ".join(description.split())
                    # Extended description to show at least 200 characters
                    if len(description) > 200:
                        description = description[:197] + "..."
                
                # Get the module name for this pattern
                # Try to find the pattern in the patterns directory
                module_name = "patterns." + pattern_key.replace("_pattern", "")
                # Check if the pattern is defined in a specific module
                if pattern_key == "blue_team_red_team_shared_context":
                    module_name = "patterns.red_blue_team"
                elif pattern_key == "blue_team_red_team_split_context":
                    module_name = "patterns.red_blue_team_split"
                
                patterns_table.add_row(
                    str(idx),
                    pattern_display_name,
                    pattern_type,
                    pattern_key,  # The actual key used to reference the pattern
                    module_name,
                    description
                )
            
            console.print("\n")
            console.print(patterns_table)
            console.print("\n[dim]Use '/agent <#>' or '/agent <pattern_name>' to load a pattern[/dim]")
        
        return True

    def handle_select(self, args: Optional[List[str]] = None) -> bool:  # pylint: disable=too-many-branches,line-too-long # noqa: E501
        """Handle /agent select command.

        Args:
            args: Optional list of command arguments

        Returns:
            True if the command was handled successfully, False otherwise
        """
        if not args:
            console.print("[red]Error: No agent specified[/red]")
            console.print("Usage: /agent select <agent_key|number|pattern>")
            return False

        agent_id = args[0]
        
        agents_to_display = get_available_agents()
        
        # Check if agent_id is a number
        if agent_id.isdigit():
            index = int(agent_id)
            
            # Build two lists: regular agents and parallel patterns
            regular_agents = []
            parallel_patterns = []
            
            for key, agent_obj in agents_to_display.items():
                if hasattr(agent_obj, "_pattern"):
                    pattern = agent_obj._pattern
                    if hasattr(pattern, "type"):
                        pattern_type_value = getattr(pattern.type, 'value', str(pattern.type))
                        if pattern_type_value == "parallel":
                            parallel_patterns.append((key, agent_obj))
                        else:
                            # Non-parallel patterns (swarm, etc.) go in regular agents
                            regular_agents.append((key, agent_obj))
                else:
                    # Regular agents and old-style patterns
                    regular_agents.append((key, agent_obj))
            
            # Determine which list to use based on the index
            total_regular = len(regular_agents)
            
            if 1 <= index <= total_regular:
                # It's a regular agent
                selected_agent_key, selected_agent = regular_agents[index - 1]
                agent_name = getattr(selected_agent, "name", selected_agent_key)
                agent = selected_agent
            elif total_regular + 1 <= index <= total_regular + len(parallel_patterns):
                # It's a parallel pattern
                pattern_idx = index - total_regular - 1
                selected_agent_key, selected_agent = parallel_patterns[pattern_idx]
                agent_name = getattr(selected_agent, "name", selected_agent_key)
                agent = selected_agent
            else:
                console.print(f"[red]Error: Invalid agent number: {agent_id}[/red]")
                console.print(f"[dim]Valid range: 1-{total_regular} for agents, {total_regular + 1}-{total_regular + len(parallel_patterns)} for patterns[/dim]")
                return False
        else:
            # Treat as agent key
            selected_agent_key = None
            for key, agent_obj in agents_to_display.items():
                if key == agent_id:
                    agent = agent_obj
                    selected_agent_key = key
                    agent_name = getattr(agent_obj, "name", key)
                    break
            else:
                console.print(f"[red]Error: Unknown agent key: {agent_id}[/red]")
                return False
        
        # Check if this is a pattern pseudo-agent
        if hasattr(agent, "_pattern"):
            pattern = agent._pattern
            
            # Handle different pattern types
            if hasattr(pattern, "type"):
                pattern_type = pattern.type
                # Get the string value if it's an enum
                if hasattr(pattern_type, 'value'):
                    pattern_type_str = pattern_type.value
                else:
                    pattern_type_str = str(pattern_type)
                
                # Handle parallel patterns
                if pattern_type_str == "parallel":
                    # This is a parallel pattern, load it into parallel configs
                    from cai.agents.patterns import get_pattern
                    from cai.repl.commands.parallel import PARALLEL_CONFIGS, PARALLEL_AGENT_INSTANCES
                    from cai.sdk.agents.simple_agent_manager import AGENT_MANAGER
                    
                    # Get current history before switching to parallel mode
                    current_history = []
                    
                    # First check for pending history transfer
                    if hasattr(AGENT_MANAGER, '_pending_history_transfer') and AGENT_MANAGER._pending_history_transfer:
                        current_history = AGENT_MANAGER._pending_history_transfer
                        AGENT_MANAGER._pending_history_transfer = None
                    else:
                        # Try to get history from ALL message histories first
                        # This ensures we get history even from non-active agents
                        for agent_name, hist in AGENT_MANAGER._message_history.items():
                            if hist:
                                current_history = hist
                                break
                        
                        # If still no history, try the current active agent
                        if not current_history:
                            current_agent = AGENT_MANAGER.get_active_agent()
                            if current_agent:
                                # Get the agent's name
                                agent_name = getattr(current_agent, 'name', None)
                                if agent_name:
                                    hist = AGENT_MANAGER.get_message_history(agent_name)
                                    if hist:
                                        current_history = hist
                        
                        # Special handling: if we still don't have history but have an active agent
                        # This can happen when the default agent is loaded at startup
                        if not current_history and current_agent:
                            # Try to get history from the model directly
                            if hasattr(current_agent, 'model') and hasattr(current_agent.model, 'message_history'):
                                current_history = current_agent.model.message_history
                    
                    if hasattr(pattern, "configs") and pattern.configs is not None:
                        # Clear existing configs and instances
                        PARALLEL_CONFIGS.clear()
                        PARALLEL_AGENT_INSTANCES.clear()
                        
                        # Store any pending history before clearing
                        if current_history:
                            AGENT_MANAGER._pending_history_transfer = current_history
                        
                        # Clear ALL agents from manager before setting up parallel mode
                        # This ensures no single agent lingers when switching to parallel
                        AGENT_MANAGER.clear_all_agents_except_pending_history()
                        
                        # Force clear the entire agent registry to prevent any stale entries
                        # This is critical to avoid duplicate P1 registrations
                        AGENT_MANAGER._agent_registry.clear()
                        AGENT_MANAGER._parallel_agents.clear()
                        AGENT_MANAGER._active_agent = None
                        AGENT_MANAGER._active_agent_name = None
                        AGENT_MANAGER._agent_id = "P1"
                        AGENT_MANAGER._id_counter = 0
                        
                        # Check if configs is iterable
                        try:
                            # Load pattern configs
                            for idx, config in enumerate(pattern.configs, 1):
                                config.id = f"P{idx}"
                                PARALLEL_CONFIGS.append(config)
                            
                            # Check for pending history transfer after clearing
                            if hasattr(AGENT_MANAGER, '_pending_history_transfer') and AGENT_MANAGER._pending_history_transfer:
                                current_history = AGENT_MANAGER._pending_history_transfer
                                AGENT_MANAGER._pending_history_transfer = None
                            
                            # Transfer history to parallel isolation system
                            if current_history and len(PARALLEL_CONFIGS) > 0:
                                from cai.sdk.agents.parallel_isolation import PARALLEL_ISOLATION
                                agent_ids = [config.id for config in PARALLEL_CONFIGS]
                                
                                # Check if pattern requires different contexts
                                if "different contexts" in (pattern.description or "").lower():
                                    # Only transfer to the first agent (P1), others start empty
                                    PARALLEL_ISOLATION._parallel_mode = True
                                    # Clear any existing histories first
                                    PARALLEL_ISOLATION.clear_all_histories()
                                    # Set history only for the first agent
                                    PARALLEL_ISOLATION.replace_isolated_history(agent_ids[0], current_history.copy())
                                    # Initialize empty histories for other agents
                                    for agent_id in agent_ids[1:]:
                                        PARALLEL_ISOLATION.replace_isolated_history(agent_id, [])
                                else:
                                    # This creates isolated copies for each parallel agent
                                    agent_ids = [config.id for config in PARALLEL_CONFIGS]
                                    PARALLEL_ISOLATION.transfer_to_parallel(current_history, len(PARALLEL_CONFIGS), agent_ids)
                        
                            # Sync to environment to enable parallel mode
                            if len(PARALLEL_CONFIGS) >= 2:
                                os.environ["CAI_PARALLEL"] = str(len(PARALLEL_CONFIGS))
                                agent_names = [config.agent_name for config in PARALLEL_CONFIGS]
                                os.environ["CAI_PARALLEL_AGENTS"] = ",".join(agent_names)
                            
                            # Set pattern description in environment for cli.py to check
                            os.environ["CAI_PATTERN_DESCRIPTION"] = pattern.description or ""
                            
                            console.print(f"[green]Loaded parallel pattern: {pattern.description}[/green]")
                            console.print(f"[cyan]{len(PARALLEL_CONFIGS)} agents configured in parallel mode[/cyan]")
                            
                            # Show configured agents
                            for idx, config in enumerate(PARALLEL_CONFIGS, 1):
                                model_info = f" [{config.model}]" if config.model else " [default]"
                                console.print(f"  {idx}. {config.agent_name}{model_info}")
                            
                            return True
                        except (TypeError, AttributeError) as e:
                            # Pattern configs is not iterable or has issues
                            console.print(f"[red]Error loading parallel pattern: {str(e)}[/red]")
                            import traceback
                            console.print(f"[dim]{traceback.format_exc()}[/dim]")
                            return False
                
                elif pattern_type_str == "swarm":
                    # Handle swarm patterns
                    if hasattr(pattern, "entry_agent") and pattern.entry_agent:
                        # Set the entry agent as the current agent
                        entry_agent = pattern.entry_agent
                        
                        # For swarm patterns, we need to set the agent key
                        # First find the key for this agent
                        agent_key = None
                        for key, ag in agents_to_display.items():
                            if ag == entry_agent:
                                agent_key = key
                                break
                        
                        if not agent_key:
                            # Try to find by agent name
                            entry_agent_name = getattr(entry_agent, "name", "")
                            for key, ag in agents_to_display.items():
                                if getattr(ag, "name", "") == entry_agent_name:
                                    agent_key = key
                                    break
                        
                        if agent_key:
                            os.environ["CAI_AGENT_TYPE"] = agent_key
                            console.print(f"[green]Loaded swarm pattern: {pattern.name}[/green]")
                            console.print(f"[cyan]Entry agent: {getattr(entry_agent, 'name', agent_key)}[/cyan]")
                            
                            # Show agents in the swarm
                            if hasattr(pattern, "agents") and pattern.agents:
                                console.print("\n[bold]Agents in swarm:[/bold]")
                                for ag in pattern.agents:
                                    ag_name = getattr(ag, "name", str(ag))
                                    console.print(f"  • {ag_name}")
                            
                            # Delegate to normal agent selection for the entry agent
                            selected_agent_key = agent_key
                            agent_name = getattr(entry_agent, "name", agent_key)
                            agent = entry_agent
                        else:
                            console.print(f"[red]Error: Could not find entry agent for swarm pattern[/red]")
                            return False
                    else:
                        console.print(f"[red]Error: Swarm pattern has no entry agent defined[/red]")
                        return False
                        
                else:
                    # Other pattern types not yet supported for direct loading
                    console.print(f"[yellow]Pattern type '{pattern_type_str}' is not yet supported for direct loading[/yellow]")
                    console.print(f"[dim]Pattern: {pattern.name} - {pattern.description}[/dim]")
                    return False
        else:
            # This is a regular agent, not a pattern
            # selected_agent_key was already set above in the agent selection logic
            pass

        # IMPORTANT: Don't set CAI_AGENT_TYPE yet - we need to set up history transfer first
        # Store the selected agent key for later use
        agent_type_to_set = None
        if 'selected_agent_key' in locals() and not (hasattr(agent, "_pattern") and 
                                                      hasattr(agent._pattern, "type") and 
                                                      str(getattr(agent._pattern.type, 'value', agent._pattern.type)) == "parallel"):
            agent_type_to_set = selected_agent_key
            
            # IMPORTANT: Ensure agent_name is correctly set for the selected agent
            # This fixes the issue where swarm pattern's agent name lingers
            if 'agent' not in locals() or 'agent_name' not in locals():
                # Re-fetch the agent and its name to ensure consistency
                selected_agent = agents_to_display.get(selected_agent_key)
                if selected_agent:
                    agent = selected_agent
                    agent_name = getattr(selected_agent, "name", selected_agent_key)
                else:
                    console.print(f"[red]Error: Could not find agent for key: {selected_agent_key}[/red]")
                    return False
        else:
            # This shouldn't happen, but let's be safe
            console.print(f"[red]Error: Could not determine agent key[/red]")
            return False
        
        # Check if this was a parallel pattern - if so, we're done
        if hasattr(agent, "_pattern") and hasattr(agent._pattern, "type"):
            pattern_type = str(getattr(agent._pattern.type, 'value', agent._pattern.type))
            if pattern_type == "parallel":
                # Parallel pattern was already handled above with its own return
                # This should not be reached, but just in case
                return True
        
        # IMPORTANT: Clear parallel configuration when switching to a regular agent
        # This prevents parallel mode from staying active when switching agents
        from cai.repl.commands.parallel import PARALLEL_CONFIGS, PARALLEL_AGENT_INSTANCES
        from cai.sdk.agents.simple_agent_manager import AGENT_MANAGER
        
        # Get current history before clearing
        current_history = []
        if PARALLEL_CONFIGS:
            # We're switching from parallel to single agent
            from cai.sdk.agents.parallel_isolation import PARALLEL_ISOLATION
            
            # Get isolated histories from parallel agents
            agent_histories = {}
            for idx, config in enumerate(PARALLEL_CONFIGS, 1):
                agent_id = config.id or f"P{idx}"
                isolated_hist = PARALLEL_ISOLATION.get_isolated_history(agent_id)
                if isolated_hist:
                    agent_histories[agent_id] = isolated_hist
            
            # Transfer from parallel - selects the best history
            if agent_histories:
                current_history = PARALLEL_ISOLATION.transfer_from_parallel(agent_histories)
            
            # If no isolated histories, check ALL message histories in AGENT_MANAGER
            # This includes histories from before switching to parallel mode
            if not current_history:
                # Check ALL message histories, not just get_all_histories which filters
                for agent_name, hist in AGENT_MANAGER._message_history.items():
                    if hist:
                        current_history = hist
                        break
        else:
            # We're switching from single agent to another single agent (or from swarm pattern)
            
            # First check if there's a pending history transfer
            if hasattr(AGENT_MANAGER, '_pending_history_transfer') and AGENT_MANAGER._pending_history_transfer:
                current_history = AGENT_MANAGER._pending_history_transfer
                AGENT_MANAGER._pending_history_transfer = None
            else:
                # Get history from all registered agents (not just active ones)
                all_histories = AGENT_MANAGER.get_all_histories()
                
                # Try active agents first
                active_agents = AGENT_MANAGER.get_active_agents()
                if active_agents:
                    for agent_name in active_agents:
                        hist = AGENT_MANAGER.get_message_history(agent_name)
                        if hist:
                            current_history = hist
                            break
                
                # If no active agent has history, check all registered agents
                if not current_history:
                    for display_name, hist in all_histories.items():
                        if hist:
                            current_history = hist
                            break
                
                # Special handling for swarm patterns - get history from the entry agent
                # Check if we're coming from a swarm pattern by checking environment
                prev_agent_type = os.getenv("CAI_AGENT_TYPE", "")
                if prev_agent_type and not current_history:
                    # Try to get history from the swarm pattern's entry agent
                    prev_agent = agents_to_display.get(prev_agent_type)
                    if prev_agent and hasattr(prev_agent, "_pattern"):
                        pattern = prev_agent._pattern
                        if hasattr(pattern, "type") and str(getattr(pattern.type, 'value', pattern.type)) == "swarm":
                            if hasattr(pattern, "entry_agent") and pattern.entry_agent:
                                entry_agent_name = getattr(pattern.entry_agent, "name", "")
                                if entry_agent_name:
                                    hist = AGENT_MANAGER.get_message_history(entry_agent_name)
                                    if hist:
                                        current_history = hist
        
        PARALLEL_CONFIGS.clear()
        PARALLEL_AGENT_INSTANCES.clear()
        
        # Reset parallel mode to single agent
        os.environ["CAI_PARALLEL"] = "1"
        os.environ["CAI_PARALLEL_AGENTS"] = ""
        
        # Transfer history to the new single agent BEFORE clearing
        if current_history:
            # Store temporarily so CLI can pick it up
            AGENT_MANAGER._pending_history_transfer = current_history
        
        # IMPORTANT: Clear ALL agents to ensure no lingering agents from parallel mode
        # This method preserves the pending history transfer
        AGENT_MANAGER.clear_all_agents_except_pending_history()
        
        # Register the new agent immediately so /history works
        # This mimics what the CLI does when it detects the agent change
        if 'selected_agent_key' in locals() and selected_agent_key:
            from cai.agents import get_agent_by_name
            new_agent = get_agent_by_name(selected_agent_key, agent_id="P1")
            new_agent_name = getattr(new_agent, "name", selected_agent_key)
            AGENT_MANAGER.switch_to_single_agent(new_agent, new_agent_name)
            
            # IMPORTANT: Store a strong reference to prevent garbage collection
            # The CLI will pick this up and use it
            AGENT_MANAGER._current_agent_strong_ref = new_agent
            
            # Check if history was transferred
            transferred_history = AGENT_MANAGER.get_message_history(new_agent_name)

        # NOW set the environment variable AFTER history transfer is complete
        if agent_type_to_set:
            os.environ["CAI_AGENT_TYPE"] = agent_type_to_set
            # Set a flag to tell CLI not to switch again
            os.environ["CAI_AGENT_SWITCH_HANDLED"] = "1"
        
        # Double-check agent_name is correct before displaying
        # This ensures we show the correct agent name even after switching from patterns
        final_agent_name = agent_name
        if hasattr(agent, 'name'):
            final_agent_name = agent.name
        elif 'selected_agent_key' in locals() and selected_agent_key in agents_to_display:
            final_agent_name = getattr(agents_to_display[selected_agent_key], 'name', selected_agent_key)
        
        console.print(f"[green]Switched to agent: {final_agent_name}[/green]", end="")
        console.print(" [yellow](Parallel mode disabled)[/yellow]" if len(PARALLEL_CONFIGS) == 0 else "")
        
        visualize_agent_graph(agent)

        # Display the system prompt
        console.print("\n[bold yellow]System Prompt:[/bold yellow]")
        instructions = agent.instructions
        if callable(instructions):
            instructions = instructions()

        # Truncate very long instructions
        if len(instructions) > 500:
            console.print(f"[dim]{instructions[:500]}...[/dim]")
            console.print(
                "[dim italic](Truncated for display - full prompt used by agent)[/dim italic]"
            )
        else:
            console.print(f"[dim]{instructions}[/dim]")

        return True

    def handle_info(self, args: Optional[List[str]] = None) -> bool:
        """Handle /agent info command.

        Args:
            args: Optional list of command arguments

        Returns:
            True if the command was handled successfully, False otherwise
        """
        if not args:
            console.print("[red]Error: No agent specified[/red]")
            console.print("Usage: /agent info <agent_key|number>")
            return False

        agent_id = args[0]

        # Get available agents
        agents_to_display = get_available_agents()

        # Resolve agent_id to an agent key (by index or name)
        if agent_id.isdigit():
            idx = int(agent_id)
            if not (1 <= idx <= len(agents_to_display)):
                console.print(f"[red]Error: Invalid agent number: {agent_id}[/red]")
                return False
            agent_key = list(agents_to_display.keys())[idx - 1]
        else:
            agent_key = None
            for key, ag in agents_to_display.items():
                if key == agent_id or getattr(ag, "name", "").lower() == agent_id.lower():
                    agent_key = key
                    break
            if agent_key is None:
                console.print(f"[red]Error: Unknown agent key: {agent_id}[/red]")
                return False

        agent = agents_to_display[agent_key]

        # Display agent information
        instructions = agent.instructions
        if callable(instructions):
            instructions = instructions()
        # Prepare agent properties
        name = agent.name or agent_key
        description = getattr(agent, "description", None) or "N/A"
        # Keep full description in info view (no truncation)
        clean_description = " ".join(line.strip() for line in description.splitlines())
        functions = getattr(agent, "functions", [])
        parallel = getattr(agent, "parallel_tool_calls", False)
        handoff_desc = getattr(agent, "handoff_description", None) or "N/A"
        handoffs = getattr(agent, "handoffs", [])
        tools = getattr(agent, "tools", [])
        guardrails_in = getattr(agent, "input_guardrails", [])
        guardrails_out = getattr(agent, "output_guardrails", [])
        output_type = getattr(agent, "output_type", None) or "N/A"
        hooks = getattr(agent, "hooks", []) or []

        # Build markdown content for agent info
        markdown_content = f"""
# Agent Info: {name}

| Property               | Value                         |
|------------------------|-------------------------------|
| Key                    | {agent_key}                   |
| Name                   | {name}                        |
| Description            | {clean_description}           |
| Functions              | {len(functions)}              |
| Parallel Tool Calls    | {"Yes" if parallel else "No"} |
| Handoff Description    | {handoff_desc}                |
| Handoffs               | {len(handoffs)}               |
| Tools                  | {len(tools)}                  |
| Input Guardrails       | {len(guardrails_in)}          |
| Output Guardrails      | {len(guardrails_out)}         |
| Output Type            | {output_type}                 |
| Hooks                  | {len(hooks)}                  |

## Instructions
{instructions}

"""
        console.print(Markdown(markdown_content))
        return True

    def handle_current(self, args: Optional[List[str]] = None) -> bool:
        """Handle /agent current command - show current agent configuration.

        Args:
            args: Optional list of command arguments (not used)

        Returns:
            True if the command was handled successfully
        """
        from rich.panel import Panel

        # Check for parallel mode first
        parallel_count = int(os.getenv("CAI_PARALLEL", "1"))
        parallel_enabled = parallel_count >= 2

        # Check PARALLEL_CONFIGS if available
        try:
            from cai.repl.commands.parallel import PARALLEL_CONFIGS
            has_parallel_configs = len(PARALLEL_CONFIGS) > 0
        except ImportError:
            has_parallel_configs = False
            PARALLEL_CONFIGS = []

        # Get available agents
        agents_to_display = get_available_agents()

        # If parallel mode is enabled, show only the parallel configuration
        if parallel_enabled and has_parallel_configs:
            # Find the active pattern name
            pattern_name = "Parallel Configuration"
            
            # Check if this configuration came from a named pattern
            for key, agent in agents_to_display.items():
                if hasattr(agent, "_pattern"):
                    pattern = agent._pattern
                    try:
                        # Check if pattern has configs and they are iterable
                        if hasattr(pattern, "configs") and pattern.configs is not None:
                            # Try to get length - will fail for Mock objects without proper setup
                            pattern_configs_len = len(pattern.configs)
                            if pattern_configs_len == len(PARALLEL_CONFIGS):
                                # Compare configs to see if they match
                                configs_match = True
                                for i, config in enumerate(pattern.configs):
                                    if i < len(PARALLEL_CONFIGS):
                                        pc = PARALLEL_CONFIGS[i]
                                        if config.agent_name != pc.agent_name:
                                            configs_match = False
                                            break
                                if configs_match:
                                    pattern_name = pattern.description or key
                                    break
                    except (TypeError, AttributeError):
                        # Handle cases where pattern.configs is not properly set up (e.g., Mock objects)
                        continue

            # Build parallel content
            parallel_content = []
            parallel_content.append(f"[bold cyan]Active Pattern:[/bold cyan] {pattern_name}")
            parallel_content.append(f"[bold]Mode:[/bold] Parallel Execution")
            parallel_content.append(f"[bold]Agent Count:[/bold] {len(PARALLEL_CONFIGS)}")
            parallel_content.append("")
            parallel_content.append("[bold]Configured Agents:[/bold]")

            # Count instances of each agent type
            agent_counts = {}
            for config in PARALLEL_CONFIGS:
                agent_counts[config.agent_name] = agent_counts.get(config.agent_name, 0) + 1

            # Track current instance for numbering
            agent_instances = {}

            # Process each config
            for idx, config in enumerate(PARALLEL_CONFIGS):
                key = config.agent_name
                # Get agent from agents_to_display
                agent = agents_to_display.get(key, None)
                if agent:
                    name = getattr(agent, "name", key)
                else:
                    # If agent not found, use the key as name
                    name = key

                # Add instance number if there are duplicates
                if agent_counts[key] > 1:
                    if key not in agent_instances:
                        agent_instances[key] = 0
                    agent_instances[key] += 1
                    name = f"{name} #{agent_instances[key]}"

                # Check if this agent has special config
                config_info = ""
                if config.model:
                    config_info = f" [{config.model}]"

                # Add ID (P1, P2, etc)
                agent_id = config.id if hasattr(config, 'id') else f"P{idx + 1}"
                parallel_content.append(f"  {idx+1}. {name} ({key}) [{agent_id}]{config_info}")

            parallel_panel = Panel(
                "\n".join(parallel_content),
                title="Current Configuration",
                border_style="yellow",
                expand=False,
            )
            console.print(parallel_panel)

        else:
            # Show single agent configuration
            current_agent_key = os.getenv("CAI_AGENT_TYPE", "one_tool_agent")

            if current_agent_key not in agents_to_display:
                console.print(f"[red]Error: Current agent '{current_agent_key}' not found[/red]")
                console.print(
                    f"[yellow]Available agents: {', '.join(agents_to_display.keys())}[/yellow]"
                )
                return False

            current_agent = agents_to_display[current_agent_key]
            agent_name = getattr(current_agent, "name", current_agent_key)

            # Create main agent info panel
            main_content = []
            main_content.append(f"[bold cyan]Active Agent:[/bold cyan] {agent_name}")
            main_content.append(f"[bold]Agent Key:[/bold] {current_agent_key}")

            # Model information - get the actual model name
            if hasattr(current_agent, "model") and hasattr(current_agent.model, "model"):
                model_display = current_agent.model.model
            else:
                model_display = self._get_model_display_for_info(current_agent_key, current_agent)
            main_content.append(f"[bold]Model:[/bold] {model_display}")

            # Tools count
            tools = getattr(current_agent, "tools", [])
            main_content.append(f"[bold]Tools:[/bold] {len(tools)}")

            # Handoffs
            handoffs = getattr(current_agent, "handoffs", [])
            main_content.append(f"[bold]Handoffs:[/bold] {len(handoffs)}")

            main_panel = Panel(
                "\n".join(main_content),
                title="Current Configuration",
                border_style="green",
                expand=False,
            )
            console.print(main_panel)

        # Show quick commands
        console.print("\n[bold]Quick Commands:[/bold]")
        console.print("• /agent list - Show all available agents and patterns")
        console.print("• /agent select <name> - Switch to a different agent or pattern")
        console.print("• /agent info <name> - Show detailed agent information")
        if parallel_enabled:
            console.print("• /parallel - Manage parallel agent configuration")
        else:
            console.print("• /parallel add - Configure parallel agents")

        return True


# Register the command
register_command(AgentCommand())
