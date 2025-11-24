"""
Parallel command for CAI CLI abstraction.

Provides commands for managing parallel agent configurations.
Different agents can be configured with specific models and prompts,
which will then be executed in parallel through the CLI.
"""

# Standard library imports
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Third-party imports
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cai.agents import get_available_agents

# Local imports
from cai.repl.commands.base import Command, register_command
from cai.sdk.agents.models.openai_chatcompletions import (
    OpenAIChatCompletionsModel,
    get_all_agent_histories,
    clear_agent_history,
)
from cai.sdk.agents.parallel_isolation import PARALLEL_ISOLATION
from cai.sdk.agents.simple_agent_manager import AGENT_MANAGER

console = Console()

# Store configured parallel runs (made global so CLI can access it)
PARALLEL_CONFIGS = []

# Store strong references to parallel agent instances to prevent garbage collection
# This ensures agent histories persist even when not actively selected
# Key: (agent_name, instance_number), Value: agent instance
PARALLEL_AGENT_INSTANCES = {}


class ParallelConfig:
    """Configuration for a parallel agent run."""

    def __init__(self, agent_name, model=None, prompt=None, unified_context=False):
        """Initialize a parallel agent configuration.

        Args:
            agent_name: Name of the agent to use
            model: Optional model to use (overrides default)
            prompt: Optional specific prompt to use
            unified_context: If True, agent shares message history with other unified agents
        """
        self.agent_name = agent_name
        self.model = model
        self.prompt = prompt
        self.unified_context = unified_context
        self.id = None  # Will be set when added to PARALLEL_CONFIGS

    def __str__(self):
        """String representation of the configuration."""
        model_str = f", model: {self.model}" if self.model else ""
        prompt_str = (
            f", prompt: '{self.prompt[:20]}...'"
            if self.prompt and len(self.prompt) > 20
            else f", prompt: '{self.prompt}'"
            if self.prompt
            else ""
        )
        unified_str = ", unified_context: True" if self.unified_context else ""
        return f"Agent: {self.agent_name}{model_str}{prompt_str}{unified_str}"


class ParallelCommand(Command):
    """Command for managing parallel agent configurations."""

    def __init__(self):
        """Initialize the parallel command."""
        super().__init__(
            name="/parallel",
            description="Configure multiple agents to run in parallel with different settings",
            aliases=["/par", "/p"],
        )

        # Add subcommands for configuration management
        self.add_subcommand("add", "Add a new agent to the parallel config", self.handle_add)
        self.add_subcommand("list", "List configured parallel agents", self.handle_list)
        self.add_subcommand("clear", "Clear all configured parallel agents", self.handle_clear)
        self.add_subcommand(
            "remove", "Remove a specific parallel agent by index", self.handle_remove
        )
        self.add_subcommand(
            "override-models",
            "Override all parallel agent models to use global model",
            self.handle_override_models,
        )
        self.add_subcommand(
            "merge", "Merge message histories from multiple agents", self.handle_merge
        )
        self.add_subcommand(
            "prompt", "Set a custom prompt for a specific parallel agent", self.handle_prompt
        )

        # Auto-load configuration on init
        self._auto_load_config()

    def _auto_load_config(self):
        """Auto-load configuration from agents.yml if it exists."""
        # Try multiple locations for agents.yml
        config_paths = [
            Path("agents.yml"),  # Current directory (backward compatibility)
            Path(__file__).parent.parent.parent / "agents" / "patterns" / "configs" / "agents.yml",  # New location
        ]
        
        config_path = None
        for path in config_paths:
            if path.exists():
                config_path = path
                break
        
        if config_path:
            try:
                with open(config_path) as f:
                    data = yaml.safe_load(f)
                    if data and isinstance(data, dict) and "parallel_agents" in data:
                        PARALLEL_CONFIGS.clear()
                        for idx, agent_config in enumerate(data["parallel_agents"], 1):
                            config = ParallelConfig(
                                agent_config["name"],
                                agent_config.get("model"),
                                agent_config.get("prompt"),
                                agent_config.get("unified_context", False)
                            )
                            # Assign ID based on position
                            config.id = f"P{idx}"
                            PARALLEL_CONFIGS.append(config)
                        self._sync_to_env()
                        console.print(
                            f"[green]Loaded {len(PARALLEL_CONFIGS)} agents from agents.yml[/green]"
                        )
            except Exception as e:
                console.print(f"[yellow]Failed to load agents.yml: {e}[/yellow]")

    def _sync_to_env(self):
        """Sync PARALLEL_CONFIGS to environment variables and manage history isolation."""
        if len(PARALLEL_CONFIGS) >= 2:
            # Auto-enable parallel mode - set the count, not "true"
            os.environ["CAI_PARALLEL"] = str(len(PARALLEL_CONFIGS))
            # Set agent names
            agent_names = [config.agent_name for config in PARALLEL_CONFIGS]
            os.environ["CAI_PARALLEL_AGENTS"] = ",".join(agent_names)
            
            # Set up history isolation for parallel mode
            if not PARALLEL_ISOLATION.is_parallel_mode():
                # Get current active agent's history as base
                active_agents = AGENT_MANAGER.get_active_agents()
                base_history = []
                if active_agents:
                    # Get the first active agent's history
                    for agent_name in active_agents:
                        base_history = AGENT_MANAGER.get_message_history(agent_name)
                        break
                
                # Create isolated histories for each parallel agent
                agent_ids = [config.id for config in PARALLEL_CONFIGS]
                PARALLEL_ISOLATION.transfer_to_parallel(base_history, len(PARALLEL_CONFIGS), agent_ids)
        else:
            # Disable parallel mode if less than 2 agents
            os.environ["CAI_PARALLEL"] = "1"
            os.environ["CAI_PARALLEL_AGENTS"] = ""
            # Don't clear configs - we want to keep single agent configurations
            
            # Clear parallel isolation if it was active
            if PARALLEL_ISOLATION.is_parallel_mode():
                # Transfer back to single agent mode
                all_histories = {}
                for config in PARALLEL_CONFIGS:
                    if config.id:
                        history = PARALLEL_ISOLATION.get_isolated_history(config.id)
                        if history:
                            all_histories[config.id] = history
                
                if all_histories:
                    # Select one history to keep
                    selected_history = PARALLEL_ISOLATION.transfer_from_parallel(all_histories)
                    # Store it for the next single agent
                    AGENT_MANAGER._pending_history_transfer = selected_history
                
                PARALLEL_ISOLATION.clear_all_histories()

    def handle_no_args(self) -> bool:
        """Handle command with no arguments - show current status."""
        from rich.panel import Panel

        # Show configured runs
        if PARALLEL_CONFIGS:
            # Check if parallel mode is actually enabled
            parallel_count = int(os.getenv("CAI_PARALLEL", "1"))
            parallel_enabled = parallel_count >= 2

            if parallel_enabled:
                status_text = "[bold green]Parallel Mode: ENABLED[/bold green]\n"
                status_text += f"[cyan]{len(PARALLEL_CONFIGS)} agents configured[/cyan]\n\n"
            else:
                status_text = "[bold yellow]Parallel Mode: DISABLED[/bold yellow]\n"
                status_text += (
                    f"[dim]{len(PARALLEL_CONFIGS)} agent(s) configured - "
                    "add more to auto-enable[/dim]\n\n"
                )

            status_text += "[bold]Configured Agents:[/bold]\n"

            # Count instances of each agent type
            agent_counts = {}
            for config in PARALLEL_CONFIGS:
                agent_counts[config.agent_name] = agent_counts.get(config.agent_name, 0) + 1

            # Track current instance number for each agent type
            agent_instances = {}

            for idx, config in enumerate(PARALLEL_CONFIGS, 1):
                agent_display_name = self._get_agent_display_name(config.agent_name)

                # Add instance number if there are duplicates
                if agent_counts[config.agent_name] > 1:
                    if config.agent_name not in agent_instances:
                        agent_instances[config.agent_name] = 0
                    agent_instances[config.agent_name] += 1
                    agent_display_name = (
                        f"{agent_display_name} #{agent_instances[config.agent_name]}"
                    )

                model_info = f" [{config.model}]" if config.model else " [default]"
                unified_info = " [unified]" if config.unified_context else ""
                prompt_info = (
                    f"\n    └─ Prompt: {config.prompt[:50]}..."
                    if config.prompt and len(config.prompt) > 50
                    else f"\n    └─ Prompt: {config.prompt}"
                    if config.prompt
                    else ""
                )
                # Display with ID
                id_info = f" [{config.id}]" if config.id else ""
                status_text += (
                    f"  {idx}. {agent_display_name} ({config.agent_name}){id_info}"
                    f"{model_info}{unified_info}{prompt_info}\n"
                )

            console.print(
                Panel(
                    status_text,
                    title="Parallel Configuration",
                    border_style="green" if parallel_enabled else "yellow",
                )
            )

            console.print("\n[bold]Quick Commands:[/bold]")
            console.print("• /parallel add <agent> - Add another agent")
            console.print("• /parallel list - Show detailed configuration")
            console.print("• /parallel clear - Clear all agents")
            console.print("• /parallel remove <index/ID> - Remove specific agent (e.g., /parallel remove P2)")
            console.print("• /parallel prompt <ID> <prompt> - Set custom prompt for agent")
            console.print("• /parallel override-models - Make all agents use global model")
            console.print("• /parallel merge <agents/IDs...> - Merge message histories")
            console.print(
                "\n[dim]Note: You can use agent IDs (P1, P2, etc.) in commands "
                "instead of long agent names[/dim]"
            )

            if Path("agents.yml").exists():
                console.print("\n[dim]Configuration loaded from agents.yml[/dim]")
        else:
            status_text = "[bold red]No Parallel Configuration[/bold red]\n\n"
            status_text += "Add agents to enable parallel execution:\n"
            status_text += "• /parallel add <agent_name> [--model MODEL] [--prompt PROMPT]\n\n"
            status_text += "Example: /parallel add red_teamer --model claude-3-opus\n\n"
            status_text += "[dim]Or create an agents.yml file with configuration[/dim]"

            console.print(Panel(status_text, title="Parallel Configuration", border_style="red"))

        return True

    def _get_agent_display_name(self, agent_key: str) -> str:
        """Get the display name for an agent."""
        available_agents = get_available_agents()
        if agent_key in available_agents:
            agent = available_agents[agent_key]
            return getattr(agent, "name", agent_key)
        return agent_key

    def handle_add(self, args: Optional[list[str]] = None) -> bool:
        """Handle the add subcommand.

        Args:
            args: Command arguments [agent_name] [--model MODEL] [--prompt PROMPT] [--unified]

        Returns:
            True if successful
        """
        if not args:
            console.print("[red]Error: Agent name required[/red]")
            console.print("Usage: /parallel add <agent_name> [--model MODEL] [--prompt PROMPT] [--unified]")
            return False

        agent_name = args[0]

        # Check if agent exists
        available_agents = get_available_agents()
        if agent_name not in available_agents:
            console.print(f"[red]Error: Unknown agent '{agent_name}'[/red]")
            console.print("Available agents:")
            for idx, name in enumerate(available_agents.keys(), 1):
                console.print(f"  {idx}. {name}")
            return False

        # Parse optional arguments
        model = None
        prompt = None
        unified_context = False
        i = 1
        while i < len(args):
            if args[i] == "--model" and i + 1 < len(args):
                model = args[i + 1]
                i += 2
            elif args[i] == "--unified":
                unified_context = True
                i += 1
            elif args[i] == "--prompt" and i + 1 < len(args):
                # Capture all remaining arguments as the prompt
                prompt = " ".join(args[i + 1 :])
                break  # Stop parsing after --prompt since we take everything after it
            else:
                i += 1

        # Add configuration with ID
        config = ParallelConfig(agent_name, model, prompt, unified_context)
        # Assign ID based on position (P1, P2, P3...)
        config.id = f"P{len(PARALLEL_CONFIGS) + 1}"
        PARALLEL_CONFIGS.append(config)

        # Sync to environment
        self._sync_to_env()

        # Get display name
        agent = available_agents[agent_name]
        display_name = getattr(agent, "name", agent_name)

        # Count instances of this agent type
        instance_count = sum(1 for c in PARALLEL_CONFIGS if c.agent_name == agent_name)

        # Show status with instance numbers for duplicates
        if instance_count > 1:
            console.print(
                f"[green]Added {display_name} #{instance_count} to parallel configuration[/green]"
            )
        else:
            console.print(f"[green]Added {display_name} to parallel configuration[/green]")

        if len(PARALLEL_CONFIGS) >= 2:
            console.print(
                f"[bold green]Parallel mode AUTO-ENABLED with "
                f"{len(PARALLEL_CONFIGS)} agents[/bold green]"
            )
        else:
            console.print("[yellow]Add one more agent to enable parallel execution[/yellow]")

        return True

    def handle_list(self, args: Optional[list[str]] = None) -> bool:
        """Handle the list subcommand.

        Args:
            args: Command arguments (unused)

        Returns:
            True if successful
        """
        if not PARALLEL_CONFIGS:
            console.print("[yellow]No parallel configurations defined[/yellow]")
            console.print("Use '/parallel add <agent_name>' to add a configuration")
            return True

        # Check parallel status
        parallel_count = int(os.getenv("CAI_PARALLEL", "1"))
        parallel_enabled = parallel_count >= 2

        table = Table(
            title=f"Configured Parallel Agents ({'ENABLED' if parallel_enabled else 'DISABLED'})"
        )
        table.add_column("#", style="dim", width=3)
        table.add_column("ID", style="magenta", width=4)
        table.add_column("Agent", style="cyan")
        table.add_column("Display Name", style="white")
        table.add_column("Model", style="green")
        table.add_column("Context", style="magenta")
        table.add_column("Custom Prompt", style="yellow", max_width=40)

        # Count instances of each agent type
        agent_counts = {}
        for config in PARALLEL_CONFIGS:
            agent_counts[config.agent_name] = agent_counts.get(config.agent_name, 0) + 1

        # Track current instance number for each agent type
        agent_instances = {}

        for idx, config in enumerate(PARALLEL_CONFIGS, 1):
            agent_display_name = self._get_agent_display_name(config.agent_name)

            # Add instance number if there are duplicates
            if agent_counts[config.agent_name] > 1:
                if config.agent_name not in agent_instances:
                    agent_instances[config.agent_name] = 0
                agent_instances[config.agent_name] += 1
                agent_display_name = f"{agent_display_name} #{agent_instances[config.agent_name]}"

            prompt_display = (
                (config.prompt[:37] + "...")
                if config.prompt and len(config.prompt) > 40
                else config.prompt or "-"
            )
            table.add_row(
                str(idx),
                config.id or "-",
                config.agent_name,
                str(agent_display_name),  # Ensure it's converted to string
                config.model or "default",
                "unified" if config.unified_context else "isolated",
                prompt_display,
            )

        console.print(table)

        if parallel_enabled:
            console.print("\n[bold green]Parallel execution is ACTIVE[/bold green]")
            console.print("[cyan]Your next prompt will show an agent selection menu[/cyan]")
        else:
            console.print("\n[bold yellow]Parallel execution is INACTIVE[/bold yellow]")
            console.print("[dim]Add one more agent to auto-enable parallel mode[/dim]")
        return True

    def handle_clear(self, args: Optional[list[str]] = None) -> bool:
        """Handle the clear subcommand.

        Args:
            args: Command arguments (unused)

        Returns:
            True if successful
        """
        count = len(PARALLEL_CONFIGS)
        PARALLEL_CONFIGS.clear()

        # Also clear stored agent instances
        PARALLEL_AGENT_INSTANCES.clear()
        
        # Clear history isolation
        PARALLEL_ISOLATION.clear_all_histories()

        # Sync to environment (will disable parallel mode)
        self._sync_to_env()

        console.print(f"[green]Cleared {count} parallel configurations[/green]")
        console.print("[yellow]Parallel mode DISABLED[/yellow]")
        return True

    def handle_remove(self, args: Optional[list[str]] = None) -> bool:
        """Handle the remove subcommand.

        Args:
            args: Command arguments [index or ID]

        Returns:
            True if successful
        """
        if not args:
            console.print("[red]Error: Index or ID required[/red]")
            console.print("Usage: /parallel remove <index>")
            console.print("       /parallel remove <ID>")
            return False

        identifier = args[0]
        removed = None
        removed_idx = -1

        # Try to remove by ID first (if it starts with P)
        if identifier.upper().startswith("P"):
            for idx, config in enumerate(PARALLEL_CONFIGS):
                if config.id and config.id.upper() == identifier.upper():
                    removed = PARALLEL_CONFIGS.pop(idx)
                    removed_idx = idx + 1
                    break
            if not removed:
                console.print(f"[red]Error: No agent found with ID '{identifier}'[/red]")
                return False
        else:
            # Try to remove by index
            try:
                idx = int(identifier)
                if idx < 1 or idx > len(PARALLEL_CONFIGS):
                    raise ValueError("Index out of range")

                removed = PARALLEL_CONFIGS.pop(idx - 1)
                removed_idx = idx
            except ValueError:
                console.print(f"[red]Error: Invalid index or ID '{identifier}'[/red]")
                return False

        # Also remove the stored instance if it exists
        if removed:
            instance_key = (removed.agent_name, removed_idx)
            if instance_key in PARALLEL_AGENT_INSTANCES:
                del PARALLEL_AGENT_INSTANCES[instance_key]

            console.print(
                f"[green]Removed {self._get_agent_display_name(removed.agent_name)} "
                f"(ID: {removed.id}) from configuration[/green]"
            )

            # Re-assign IDs after removal to keep them sequential
            for idx, config in enumerate(PARALLEL_CONFIGS, 1):
                config.id = f"P{idx}"
            
            # Sync to environment
            self._sync_to_env()

            # Show status
            if len(PARALLEL_CONFIGS) >= 2:
                console.print(
                    f"[green]Parallel mode still ENABLED with "
                    f"{len(PARALLEL_CONFIGS)} agents[/green]"
                )
            elif len(PARALLEL_CONFIGS) == 1:
                console.print(
                    "[yellow]Parallel mode DISABLED - only 1 agent configured[/yellow]"
                )
            else:
                console.print(
                    "[yellow]Parallel mode DISABLED - no agents configured[/yellow]"
                )

            return True

    def handle_load(self, args: Optional[list[str]] = None) -> bool:
        """Load configuration from YAML file.

        Args:
            args: Optional filename (defaults to agents.yml)

        Returns:
            True if successful
        """
        filename = args[0] if args else "agents.yml"
        config_path = Path(filename)

        if not config_path.exists():
            console.print(f"[red]Error: File '{filename}' not found[/red]")
            return False

        try:
            with open(config_path) as f:
                data = yaml.safe_load(f)
                if not data or not isinstance(data, dict) or "parallel_agents" not in data:
                    console.print(f"[red]Error: Invalid configuration format in '{filename}'[/red]")
                    console.print("[dim]Expected 'parallel_agents' key with list of agents[/dim]")
                    return False

                PARALLEL_CONFIGS.clear()
                config_idx = 1
                for agent_config in data["parallel_agents"]:
                    if "name" not in agent_config:
                        console.print(
                            "[yellow]Warning: Skipping agent without 'name' field[/yellow]"
                        )
                        continue

                    config = ParallelConfig(
                        agent_config["name"], 
                        agent_config.get("model"), 
                        agent_config.get("prompt"),
                        agent_config.get("unified_context", False)
                    )
                    # Assign ID based on position
                    config.id = f"P{config_idx}"
                    PARALLEL_CONFIGS.append(config)
                    config_idx += 1

                self._sync_to_env()
                console.print(
                    f"[green]Loaded {len(PARALLEL_CONFIGS)} agents from {filename}[/green]"
                )

                if len(PARALLEL_CONFIGS) >= 2:
                    console.print("[bold green]Parallel mode AUTO-ENABLED[/bold green]")

        except Exception as e:
            console.print(f"[red]Error loading '{filename}': {e}[/red]")
            return False

        return True

    def handle_save(self, args: Optional[list[str]] = None) -> bool:
        """Save current configuration to YAML file.

        Args:
            args: Optional filename (defaults to agents.yml)

        Returns:
            True if successful
        """
        if not PARALLEL_CONFIGS:
            console.print("[red]Error: No configurations to save[/red]")
            return False

        filename = args[0] if args else "agents.yml"

        # Build YAML structure
        data = {"parallel_agents": []}

        for config in PARALLEL_CONFIGS:
            agent_data = {"name": config.agent_name}
            if config.model:
                agent_data["model"] = config.model
            if config.prompt:
                agent_data["prompt"] = config.prompt
            data["parallel_agents"].append(agent_data)

        try:
            with open(filename, "w") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            console.print(f"[green]Saved {len(PARALLEL_CONFIGS)} agents to {filename}[/green]")
        except Exception as e:
            console.print(f"[red]Error saving to '{filename}': {e}[/red]")
            return False

        return True

    def handle_override_models(self, args: Optional[list[str]] = None) -> bool:
        """Override all parallel agent models to use the global model.

        Args:
            args: Command arguments (unused)

        Returns:
            True if successful
        """
        if not PARALLEL_CONFIGS:
            console.print("[yellow]No parallel configurations to override[/yellow]")
            return False

        global_model = os.getenv("CAI_MODEL", "alias0")
        count = 0

        for config in PARALLEL_CONFIGS:
            if config.model is not None:  # Only override if a specific model was set
                config.model = None  # Set to None to use global model
                count += 1

        if count > 0:
            console.print(
                f"[green]Override {count} agent(s) to use global model: {global_model}[/green]"
            )
            console.print("[dim]Agent models will now follow the global /model setting[/dim]")
        else:
            console.print("[yellow]All agents already using global model[/yellow]")

        return True

    def handle_merge(self, args: Optional[list[str]] = None) -> bool:
        """Handle the merge subcommand to merge message histories from multiple agents.

        Args:
            args: Command arguments [agent_names...] [--strategy STRATEGY] [--target TARGET] [--remove-sources]
                  agent_names: List of agent names or "all" to merge all available
                  --strategy: Merge strategy (chronological, by-agent, interleaved)
                  --target: Target agent name to save merged history to (default: "merged")
                  --remove-sources: Remove source agents after merging

        Returns:
            True if successful
        """
        if not args:
            # Default to merging all agents when no arguments provided
            args = ["all"]

        # Import PARALLEL_ISOLATION here
        from cai.sdk.agents.parallel_isolation import PARALLEL_ISOLATION
        
        # Get all available agent histories to help with name matching
        all_histories = {}

        # Parse arguments - first extract flags
        strategy = "chronological"
        target_agent = None
        remove_sources = False
        remaining_args = []

        i = 0
        while i < len(args):
            if args[i] == "--strategy" and i + 1 < len(args):
                strategy = args[i + 1]
                i += 2
            elif args[i] == "--target" and i + 1 < len(args):
                # Join remaining args until next flag for target agent name
                j = i + 2
                target_parts = [args[i + 1]]
                while j < len(args) and not args[j].startswith("--"):
                    target_parts.append(args[j])
                    j += 1
                target_agent = " ".join(target_parts)
                i = j
            elif args[i] == "--remove-sources":
                remove_sources = True
                i += 1
            else:
                remaining_args.append(args[i])
                i += 1

        # If no target specified, use special value to indicate merging to all source agents
        merge_to_all_sources = False
        if not target_agent:
            merge_to_all_sources = True
            target_agent = "all_sources"  # Special marker

        # Now parse agent names from remaining args
        agent_names = []

        # Special case for "all"
        if "all" in remaining_args:
            agent_names = ["all"]
        else:
            # Try to match agent names, accounting for spaces
            agent_names = self._parse_agent_names(remaining_args, all_histories)

        if not agent_names:
            console.print("[red]Error: No valid agent names provided[/red]")
            console.print(f"Available agents with histories: {', '.join(all_histories.keys())}")
            return False

        # Validate strategy
        valid_strategies = ["chronological", "by-agent", "interleaved"]
        if strategy not in valid_strategies:
            console.print(
                f"[red]Error: Invalid strategy '{strategy}'. "
                f"Must be one of: {', '.join(valid_strategies)}[/red]"
            )
            return False

        # Check if we're in parallel mode and need to get histories from PARALLEL_ISOLATION
        if PARALLEL_CONFIGS and (PARALLEL_ISOLATION.is_parallel_mode() or PARALLEL_ISOLATION.has_isolated_histories()):
            console.print("[dim]Getting histories from parallel agents...[/dim]")
            
            # Build all_histories from both PARALLEL_ISOLATION and AGENT_MANAGER
            from cai.agents import get_available_agents
            available_agents = get_available_agents()
            
            # First, get any histories from AGENT_MANAGER
            all_histories = get_all_agent_histories()
            
            # Then, add histories from PARALLEL_ISOLATION for each configured agent
            for idx, config in enumerate(PARALLEL_CONFIGS, 1):
                agent_id = config.id or f"P{idx}"
                isolated_history = PARALLEL_ISOLATION.get_isolated_history(agent_id)
                
                if isolated_history:
                    # Get the display name for this agent
                    if config.agent_name in available_agents:
                        agent = available_agents[config.agent_name]
                        agent_display_name = getattr(agent, "name", config.agent_name)
                        
                        # Add instance number if needed
                        total_count = sum(1 for c in PARALLEL_CONFIGS if c.agent_name == config.agent_name)
                        if total_count > 1:
                            instance_num = 0
                            for c in PARALLEL_CONFIGS:
                                if c.agent_name == config.agent_name:
                                    instance_num += 1
                                    if c.id == config.id:
                                        break
                            agent_display_name = f"{agent_display_name} #{instance_num}"
                        
                        # Add to all_histories with the agent ID
                        history_key = f"{agent_display_name} [{agent_id}]"
                        all_histories[history_key] = isolated_history
                        console.print(f"[dim]  Found {len(isolated_history)} messages for {history_key}[/dim]")
        
        # If still no histories, check AGENT_MANAGER directly
        if not all_histories:
            from cai.sdk.agents.simple_agent_manager import AGENT_MANAGER
            # Try to get histories from AGENT_MANAGER
            for agent_name, history in AGENT_MANAGER._message_history.items():
                if history:  # Only include agents with actual history
                    # Check if this agent already has an ID suffix
                    if "[" in agent_name and agent_name.endswith("]"):
                        all_histories[agent_name] = history
                    else:
                        # Add with P1 suffix for single agent mode
                        all_histories[f"{agent_name} [P1]"] = history
        
        # all_histories already fetched above
        if not all_histories:
            console.print("[yellow]No agent histories found[/yellow]")
            console.print("[dim]Make sure agents have been loaded with history first[/dim]")
            return False

        # Determine which agents to merge
        if "all" in agent_names:
            agents_to_merge = list(all_histories.keys())
        else:
            # Validate that all requested agents exist
            agents_to_merge = []
            missing_agents = []
            for agent in agent_names:
                if agent in all_histories:
                    agents_to_merge.append(agent)
                else:
                    missing_agents.append(agent)
            
            if missing_agents:
                console.print(f"[red]Error: The following agents were not found: {', '.join(missing_agents)}[/red]")
                console.print("[yellow]Available agents with histories:[/yellow]")
                for agent_name in sorted(all_histories.keys()):
                    console.print(f"  - {agent_name}")
                return False
        
        # Remove duplicates while preserving order
        seen = set()
        unique_agents_to_merge = []
        for agent in agents_to_merge:
            if agent not in seen:
                seen.add(agent)
                unique_agents_to_merge.append(agent)
        agents_to_merge = unique_agents_to_merge

        if len(agents_to_merge) < 2:
            console.print("[red]Error: Need at least 2 agents to merge[/red]")
            if len(agents_to_merge) == 1:
                console.print(f"[yellow]Only found 1 agent: {agents_to_merge[0]}[/yellow]")
            console.print(f"[yellow]Available agents with histories:[/yellow]")
            for agent_name in sorted(all_histories.keys()):
                console.print(f"  - {agent_name}")
            console.print("\n[dim]Tip: Make sure you have multiple agents with history to merge.[/dim]")
            console.print("[dim]You can load histories with '/load parallel' or run agents in parallel mode.[/dim]")
            return False

        # Get agent IDs for display
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
        
        # Format agents for display
        agents_display = []
        for agent in agents_to_merge:
            if agent in agent_ids:
                agents_display.append(f"{agent} [{agent_ids[agent]}]")
            else:
                agents_display.append(agent)
        
        console.print(f"[cyan]Merging histories from: {', '.join(agents_display)}[/cyan]")
        console.print(f"[cyan]Using strategy: {strategy}[/cyan]")
        console.print(f"[cyan]Target agent: {target_agent}[/cyan]")
        
        # Debug: Show message counts for each agent
        total_unique_messages = 0
        all_signatures = set()
        for agent in agents_to_merge:
            if agent in all_histories:
                agent_history = all_histories[agent]
                agent_signatures = set()
                for msg in agent_history:
                    sig = self._get_message_signature(msg)
                    if sig:
                        agent_signatures.add(sig)
                        if sig not in all_signatures:
                            total_unique_messages += 1
                        all_signatures.add(sig)
                console.print(f"[dim]  - {agent}: {len(agent_history)} messages ({len(agent_signatures)} unique signatures)[/dim]")
            else:
                console.print(f"[yellow]  - {agent}: Not found in histories[/yellow]")
        
        console.print(f"[dim]Total unique messages across all agents: {total_unique_messages}[/dim]")

        # Perform the merge based on strategy
        merged_history = []

        if strategy == "chronological":
            merged_history = self._merge_chronological(all_histories, agents_to_merge)
        elif strategy == "by-agent":
            merged_history = self._merge_by_agent(all_histories, agents_to_merge)
        elif strategy == "interleaved":
            merged_history = self._merge_interleaved(all_histories, agents_to_merge)

        if not merged_history:
            console.print("[yellow]No messages found to merge[/yellow]")
            return False

        # Create or update the target agent(s) with merged history
        if merge_to_all_sources:
            # Default behavior: add merged history to all source agents
            self._save_merged_history_to_sources(agents_to_merge, merged_history, all_histories)
        else:
            # Explicit target specified: create/update single target agent
            self._save_merged_history(target_agent, merged_history, remove_sources=remove_sources, source_agents=agents_to_merge)

        # Display summary
        message_count = len(merged_history)
        user_messages = sum(1 for msg in merged_history if msg.get("role") == "user")
        assistant_messages = sum(1 for msg in merged_history if msg.get("role") == "assistant")
        tool_messages = sum(1 for msg in merged_history if msg.get("role") == "tool")

        summary = f"[bold green]Successfully merged {len(agents_to_merge)} agents[/bold green]\n\n"
        summary += "[bold]Merge Summary:[/bold]\n"
        summary += f"  Total messages: {message_count}\n"
        summary += f"  User messages: {user_messages}\n"
        summary += f"  Agent messages: {assistant_messages}\n"
        summary += f"  Tool messages: {tool_messages}\n"
        
        if merge_to_all_sources:
            summary += f"  Updated agents: {', '.join(agents_to_merge)}\n\n"
            summary += f"[dim]All source agents now have the complete merged history[/dim]"
        else:
            summary += f"  Target agent: {target_agent}\n\n"
            summary += f"[dim]Use '/history {target_agent}' to view the merged history[/dim]"

        console.print(Panel(summary, title="Merge Complete", border_style="green"))

        return True

    def _merge_chronological(
        self, all_histories: dict[str, list], agents_to_merge: list[str]
    ) -> list[dict[str, Any]]:
        """Merge histories chronologically by interleaving messages based on conversation flow."""
        # Collect all messages with agent source and their indices
        agent_messages = {}
        for agent_name in agents_to_merge:
            history = all_histories.get(agent_name, [])
            agent_messages[agent_name] = []
            for idx, msg in enumerate(history):
                msg_copy = msg.copy()
                msg_copy["_source_agent"] = agent_name
                msg_copy["_original_index"] = idx
                agent_messages[agent_name].append(msg_copy)

        # Create indices to track position in each agent's history
        indices = {agent: 0 for agent in agents_to_merge}
        
        # Process messages in an intelligent interleaved fashion
        all_messages = []
        
        while any(indices[agent] < len(agent_messages[agent]) for agent in agents_to_merge):
            # Look for the next user message across all agents
            next_user_msgs = []
            for agent in agents_to_merge:
                if indices[agent] < len(agent_messages[agent]):
                    msg = agent_messages[agent][indices[agent]]
                    if msg.get("role") == "user":
                        next_user_msgs.append((agent, msg))
            
            if next_user_msgs:
                # Process the first user message found (they should be similar across agents)
                chosen_agent, user_msg = next_user_msgs[0]
                all_messages.append(user_msg)
                indices[chosen_agent] += 1
                
                # Skip duplicate user messages from other agents
                for agent, msg in next_user_msgs[1:]:
                    if msg.get("content") == user_msg.get("content"):
                        indices[agent] += 1
                
                # Now collect all responses to this user message from all agents
                responses_collected = True
                while responses_collected:
                    responses_collected = False
                    
                    for agent in agents_to_merge:
                        if indices[agent] < len(agent_messages[agent]):
                            msg = agent_messages[agent][indices[agent]]
                            
                            # Collect assistant responses and tool interactions until next user message
                            if msg.get("role") in ["assistant", "tool", "system"]:
                                all_messages.append(msg)
                                indices[agent] += 1
                                responses_collected = True
                                
                                # If this is a tool call, look for the corresponding tool response
                                if msg.get("role") == "assistant" and msg.get("tool_calls"):
                                    tool_call_ids = [tc.get("id") for tc in msg.get("tool_calls", [])]
                                    
                                    # Look ahead for tool responses
                                    temp_idx = indices[agent]
                                    while temp_idx < len(agent_messages[agent]):
                                        next_msg = agent_messages[agent][temp_idx]
                                        if next_msg.get("role") == "tool" and next_msg.get("tool_call_id") in tool_call_ids:
                                            all_messages.append(next_msg)
                                            indices[agent] = temp_idx + 1
                                            break
                                        elif next_msg.get("role") == "user":
                                            # Stop if we hit another user message
                                            break
                                        temp_idx += 1
                            elif msg.get("role") == "user":
                                # Don't process user messages here - they'll be handled in the next iteration
                                break
            else:
                # No more user messages, collect any remaining messages
                for agent in agents_to_merge:
                    if indices[agent] < len(agent_messages[agent]):
                        msg = agent_messages[agent][indices[agent]]
                        all_messages.append(msg)
                        indices[agent] += 1
                        break  # Process one at a time to maintain some order

        # Process messages to create the merged history
        merged = []
        seen_tool_calls = {}  # Track tool calls by ID to avoid duplicates
        seen_messages = set()  # Track message signatures to avoid duplicates
        
        # Debug: show total messages collected
        console.print(f"[dim]Total messages collected from all agents: {len(all_messages)}[/dim]")
        
        # Debug: Show how many unique messages there are
        unique_sigs = set()
        for msg in all_messages:
            sig = self._get_message_signature(msg)
            if sig:
                unique_sigs.add(sig)
        console.print(f"[dim]Unique message signatures in collected messages: {len(unique_sigs)}[/dim]")

        for msg in all_messages:
            should_add = True
            msg_sig = self._get_message_signature(msg)

            # Check if we've already seen this exact message
            if msg_sig and msg_sig in seen_messages:
                should_add = False
            
            # Additional checks for specific message types
            if should_add and msg.get("role") == "user":
                # For user messages, check if the same content was just added
                if (
                    merged
                    and merged[-1].get("role") == "user"
                    and merged[-1].get("content") == msg.get("content")
                ):
                    should_add = False
            elif should_add and msg.get("role") == "assistant" and msg.get("tool_calls"):
                # For tool calls, track by tool call ID
                for tool_call in msg.get("tool_calls", []):
                    tool_id = tool_call.get("id")
                    if tool_id:
                        if tool_id in seen_tool_calls:
                            should_add = False
                            break
                        seen_tool_calls[tool_id] = msg.get("_source_agent")
            elif should_add and msg.get("role") == "tool":
                # Tool responses should match their tool calls
                tool_call_id = msg.get("tool_call_id")
                if tool_call_id and tool_call_id in seen_tool_calls:
                    # Only add if from the same agent that made the tool call
                    if seen_tool_calls.get(tool_call_id) != msg.get("_source_agent"):
                        should_add = False

            if should_add:
                # Clean up internal metadata before adding
                clean_msg = {k: v for k, v in msg.items() if not k.startswith("_")}
                merged.append(clean_msg)
                if msg_sig:
                    seen_messages.add(msg_sig)

        return merged

    def _merge_by_agent(
        self, all_histories: dict[str, list], agents_to_merge: list[str]
    ) -> list[dict[str, Any]]:
        """Merge histories by grouping messages from each agent."""
        merged = []

        # Add a system message indicating merged history
        merged.append(
            {
                "role": "system",
                "content": (
                    f"This is a merged conversation history from agents: "
                    f"{', '.join(agents_to_merge)}"
                ),
            }
        )

        # Process each agent's history in sequence
        for agent_name in agents_to_merge:
            history = all_histories[agent_name]
            if history:
                # Add agent separator
                merged.append({"role": "system", "content": f"--- Messages from {agent_name} ---"})

                # Add all messages from this agent
                for msg in history:
                    # Skip system messages that might be duplicates
                    if msg.get("role") == "system" and any(
                        existing.get("role") == "system"
                        and existing.get("content") == msg.get("content")
                        for existing in merged[:5]  # Only check first few messages
                    ):
                        continue
                    merged.append(msg.copy())

        return merged

    def _merge_interleaved(
        self, all_histories: dict[str, list], agents_to_merge: list[str]
    ) -> list[dict[str, Any]]:
        """Merge histories while preserving conversation flow and tool call/response pairs."""
        merged = []
        seen_tool_calls = set()

        # Create indices for each agent's history
        indices = {agent: 0 for agent in agents_to_merge}
        histories = {agent: all_histories[agent] for agent in agents_to_merge}

        # Process messages in a round-robin fashion
        while any(indices[agent] < len(histories[agent]) for agent in agents_to_merge):
            # Collect next available message from each agent
            next_messages = []

            for agent in agents_to_merge:
                if indices[agent] < len(histories[agent]):
                    msg = histories[agent][indices[agent]]
                    next_messages.append((agent, indices[agent], msg))

            if not next_messages:
                break

            # Sort by role priority: user > assistant > tool
            role_priority = {"user": 0, "assistant": 1, "tool": 2, "system": 3}
            next_messages.sort(key=lambda x: (role_priority.get(x[2].get("role", ""), 4), x[1]))

            # Process the highest priority message
            agent, idx, msg = next_messages[0]
            indices[agent] += 1

            # Handle tool calls and responses specially
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                tool_call_id = msg["tool_calls"][0].get("id")
                if tool_call_id not in seen_tool_calls:
                    seen_tool_calls.add(tool_call_id)
                    merged.append(msg.copy())

                    # Look for corresponding tool response in any agent's history
                    for search_agent in agents_to_merge:
                        search_idx = indices[search_agent]
                        while search_idx < len(histories[search_agent]):
                            search_msg = histories[search_agent][search_idx]
                            if (
                                search_msg.get("role") == "tool"
                                and search_msg.get("tool_call_id") == tool_call_id
                            ):
                                merged.append(search_msg.copy())
                                indices[search_agent] = search_idx + 1
                                break
                            search_idx += 1

            elif msg.get("role") == "tool":
                # Skip if we already processed this tool response
                if msg.get("tool_call_id") not in seen_tool_calls:
                    merged.append(msg.copy())
            else:
                # For other messages, check for duplicates
                is_duplicate = False
                if msg.get("role") in ["user", "system"]:
                    # Check if this exact message was recently added
                    for recent_msg in reversed(merged[-5:]):  # Check last 5 messages
                        if recent_msg.get("role") == msg.get("role") and recent_msg.get(
                            "content"
                        ) == msg.get("content"):
                            is_duplicate = True
                            break

                if not is_duplicate:
                    merged.append(msg.copy())

        return merged

    def _save_merged_history(self, target_agent: str, merged_history: list[dict[str, Any]], remove_sources: bool = False, source_agents: list[str] = None) -> None:
        """Save the merged history to a target agent.
        
        Args:
            target_agent: Name of the target agent to save merged history to
            merged_history: The merged message history
            remove_sources: Whether to remove source agents after merging
            source_agents: List of source agent names to remove (if remove_sources is True)
        """
        from cai.sdk.agents.models.openai_chatcompletions import (
            ACTIVE_MODEL_INSTANCES, 
            PERSISTENT_MESSAGE_HISTORIES
        )
        from cai.agents import get_agent_by_name, get_available_agents

        # First, check if the target agent already exists in PARALLEL_CONFIGS
        target_config = None
        target_exists_in_configs = False
        target_display_name = target_agent
        
        # Check if target matches any existing config by display name or ID
        available_agents = get_available_agents()
        for config in PARALLEL_CONFIGS:
            # Get the display name for this config
            agent = available_agents.get(config.agent_name)
            if agent and hasattr(agent, 'name'):
                display_name = getattr(agent, 'name', config.agent_name)
                
                # Check if target matches display name, agent name, or ID
                if (display_name.lower() == target_agent.lower() or 
                    config.agent_name.lower() == target_agent.lower() or
                    (config.id and config.id.upper() == target_agent.upper())):
                    target_config = config
                    target_exists_in_configs = True
                    target_display_name = display_name
                    break
        
        # If not in configs, just store the merged history
        if not target_exists_in_configs:
            # Don't create a config for merged agents - they are virtual
            # Just store the merged history in the persistent store
            PERSISTENT_MESSAGE_HISTORIES[target_agent] = merged_history
            console.print(f"[green]Created merged history for '{target_agent}' with {len(merged_history)} messages[/green]")
        else:
            # Target already exists in configs, just update its history
            # First check if there's an active instance
            existing_model = None
            for (agent_name, instance_id), model_ref in ACTIVE_MODEL_INSTANCES.items():
                if agent_name == target_agent:
                    model = model_ref() if callable(model_ref) else model_ref
                    if model:
                        existing_model = model
                        break
            
            if existing_model:
                # Update existing model's history
                existing_model.message_history.clear()
                # Reset context usage since we cleared history
                os.environ['CAI_CONTEXT_USAGE'] = '0.0'
                for msg in merged_history:
                    existing_model.add_to_message_history(msg)
                console.print(f"[green]Updated history for existing agent '{target_agent}'[/green]")
            else:
                # Store in persistent history
                PERSISTENT_MESSAGE_HISTORIES[target_agent] = merged_history
                console.print(f"[green]Updated history for '{target_agent}'[/green]")
        
        # Remove source agents if requested
        if remove_sources and source_agents:
            removed_count = 0
            for source_agent in source_agents:
                # Skip if source is same as target
                if source_agent.lower() == target_agent.lower():
                    continue
                    
                # Clear the source agent's history
                clear_agent_history(source_agent)
                
                # Remove from PARALLEL_CONFIGS if it exists there
                for i in range(len(PARALLEL_CONFIGS) - 1, -1, -1):
                    config = PARALLEL_CONFIGS[i]
                    # Check by display name or ID
                    from cai.agents import get_available_agents
                    available_agents = get_available_agents()
                    if config.agent_name in available_agents:
                        agent = available_agents[config.agent_name]
                        display_name = getattr(agent, 'name', config.agent_name)
                        
                        # Check if this config matches the source agent
                        # Handle instance numbers (e.g., "Test Agent #1" matches "Test Agent")
                        source_base_name = source_agent.split(' #')[0] if ' #' in source_agent else source_agent
                        
                        if (display_name == source_agent or 
                            display_name == source_base_name or
                            (config.id and source_agent.upper().startswith('P') and config.id.upper() == source_agent.upper())):
                            PARALLEL_CONFIGS.pop(i)
                            removed_count += 1
                            # Also remove from PARALLEL_AGENT_INSTANCES
                            instance_key = (config.agent_name, i + 1)
                            if instance_key in PARALLEL_AGENT_INSTANCES:
                                del PARALLEL_AGENT_INSTANCES[instance_key]
                            break
            
            if removed_count > 0:
                # Re-assign IDs after removal
                for idx, config in enumerate(PARALLEL_CONFIGS, 1):
                    config.id = f"P{idx}"
                
                # Sync to environment
                self._sync_to_env()
                
                console.print(f"[yellow]Removed {removed_count} source agent(s) after merging[/yellow]")
        
        console.print(
            f"[dim]Note: The merged agent '{target_agent}' is now available with "
            "the combined history[/dim]"
        )
        
        # Disable parallel mode if no agents remain
        if remove_sources and len(PARALLEL_CONFIGS) < 2:
            if len(PARALLEL_CONFIGS) > 0:
                PARALLEL_CONFIGS.clear()
                PARALLEL_AGENT_INSTANCES.clear()
                self._sync_to_env()
                console.print("[yellow]Parallel mode DISABLED after merging[/yellow]")
    
    def _save_merged_history_to_sources(self, source_agents: list[str], merged_history: list[dict[str, Any]], original_histories: dict[str, list]) -> None:
        """Save the merged history to all source agents, avoiding duplicates.
        
        Args:
            source_agents: List of source agent names to update
            merged_history: The merged message history
            original_histories: Original histories before merge (for duplicate detection)
        """
        from cai.sdk.agents.models.openai_chatcompletions import (
            ACTIVE_MODEL_INSTANCES, 
            PERSISTENT_MESSAGE_HISTORIES
        )
        
        console.print("[dim]Updating all source agents with merged history...[/dim]")
        
        for agent_name in source_agents:
            # Get the original history for this agent
            original_history = original_histories.get(agent_name, [])
            
            # Build a set of message signatures from original history for duplicate detection
            original_signatures = set()
            original_messages_by_sig = {}  # Track actual messages by signature
            for msg in original_history:
                # Create a signature based on role, content, and tool info
                sig = self._get_message_signature(msg)
                if sig:
                    original_signatures.add(sig)
                    original_messages_by_sig[sig] = msg
            
            # Track which messages from merged history are truly new
            new_messages = []
            seen_signatures = set(original_signatures)  # Start with original signatures
            
            for msg in merged_history:
                sig = self._get_message_signature(msg)
                
                # Check if this message is already in the original history
                is_duplicate = False
                if sig in original_signatures:
                    # This message already exists in the original history
                    is_duplicate = True
                else:
                    # Check if we've already added this message in this merge
                    if sig in seen_signatures:
                        is_duplicate = True
                
                if not is_duplicate and sig:
                    new_messages.append(msg)
                    seen_signatures.add(sig)
            
            # The final history should be the merged history (which already contains all messages)
            # We don't want to append to original history as that would duplicate messages
            # The merged history is already the complete history from all agents
            final_history = merged_history.copy()
            
            # Update the agent's history
            # First check if there's an active instance
            existing_model = None
            for (model_agent_name, instance_id), model_ref in ACTIVE_MODEL_INSTANCES.items():
                # Extract base agent name from the format "Agent Name [ID]"
                base_name = agent_name
                if "[" in agent_name and agent_name.endswith("]"):
                    base_name = agent_name.rsplit("[", 1)[0].strip()
                
                if model_agent_name == base_name or model_agent_name == agent_name:
                    model = model_ref() if callable(model_ref) else model_ref
                    if model:
                        existing_model = model
                        break
            
            if existing_model:
                # Update existing model's history
                existing_model.message_history.clear()
                # Reset context usage since we're rebuilding history
                import os
                os.environ['CAI_CONTEXT_USAGE'] = '0.0'
                for msg in final_history:
                    existing_model.add_to_message_history(msg)
                console.print(f"[green]✓ Updated {agent_name} (active instance)[/green]")
            else:
                # Store in persistent history
                PERSISTENT_MESSAGE_HISTORIES[agent_name] = final_history
                console.print(f"[green]✓ Updated {agent_name} (persistent storage)[/green]")
            
            # Also update in AGENT_MANAGER if needed
            from cai.sdk.agents.simple_agent_manager import AGENT_MANAGER
            base_name = agent_name
            if "[" in agent_name and agent_name.endswith("]"):
                base_name = agent_name.rsplit("[", 1)[0].strip()
                # Also extract the ID for PARALLEL_ISOLATION
                agent_id = agent_name.split("[")[1].rstrip("]")
                
                # Update PARALLEL_ISOLATION if it has this agent
                if PARALLEL_ISOLATION.get_isolated_history(agent_id) is not None:
                    PARALLEL_ISOLATION.replace_isolated_history(agent_id, final_history)
            
            # Update AGENT_MANAGER's message history directly
            AGENT_MANAGER._message_history[base_name] = final_history
            
            # Show statistics
            original_count = len(original_history)
            merged_count = len(merged_history)
            new_count = len(new_messages)
            console.print(f"[dim]  Original: {original_count} messages, Merged total: {merged_count} messages, New: {new_count} messages[/dim]")
        
        console.print(
            f"[dim]Note: All {len(source_agents)} source agents now have the combined history[/dim]"
        )
    
    def _get_message_signature(self, msg: dict) -> Optional[str]:
        """Get a unique signature for a message to detect duplicates.
        
        Args:
            msg: The message dictionary
            
        Returns:
            A unique signature string or None if message is invalid
        """
        role = msg.get("role")
        if not role:
            return None
        
        # For user and system messages, use role + content
        if role in ["user", "system"]:
            content = msg.get("content", "")
            # Normalize whitespace for better matching
            normalized_content = " ".join(content.split()) if content else ""
            return f"{role}:{normalized_content}"
        
        # For assistant messages with tool calls
        elif role == "assistant":
            content = msg.get("content", "") or ""
            # Normalize whitespace
            normalized_content = " ".join(content.split()) if content else ""
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                # Create a more detailed signature for tool calls
                tool_sigs = []
                for tc in tool_calls:
                    tool_name = tc.get("function", {}).get("name", "")
                    tool_args = tc.get("function", {}).get("arguments", "")
                    # Create signature with tool name and arguments
                    tool_sigs.append(f"{tool_name}:{tool_args}")
                return f"{role}:{normalized_content}:tools:[{';'.join(sorted(tool_sigs))}]"
            else:
                return f"{role}:{normalized_content}"
        
        # For tool messages
        elif role == "tool":
            tool_call_id = msg.get("tool_call_id", "")
            content = msg.get("content", "")
            # Normalize and use more of the content for better discrimination
            normalized_content = " ".join(content.split()) if content else ""
            # Use first 200 chars instead of 100 for better discrimination
            content_preview = normalized_content[:200] if normalized_content else ""
            return f"{role}:{tool_call_id}:{content_preview}"
        
        return None

    def _parse_agent_names(self, args: list[str], all_histories: dict[str, list]) -> list[str]:
        """Parse agent names from arguments, handling names with spaces and IDs.

        Args:
            args: List of argument strings
            all_histories: Dictionary of available agent histories

        Returns:
            List of matched agent names
        """
        if not args:
            return []

        # Get all available agent names
        available_agents = list(all_histories.keys())
        
        # Create a case-insensitive lookup dictionary
        agent_lookup = {name.lower(): name for name in available_agents}

        # Build a list of possible agent names by progressively joining arguments
        parsed_agents = []
        i = 0

        while i < len(args):
            # Check if this is an ID reference (P1, P2, etc.)
            if args[i].upper().startswith("P"):
                # First, check if any available agent has this ID in brackets
                found_by_id = False
                target_id = args[i].upper()
                
                # Look for agents with [ID] suffix in the available agents
                for agent_name in available_agents:
                    if f"[{target_id}]" in agent_name:
                        parsed_agents.append(agent_name)
                        found_by_id = True
                        i += 1
                        break
                
                if found_by_id:
                    continue
                
                # If not found by bracket ID, try to find by PARALLEL_CONFIGS
                for config in PARALLEL_CONFIGS:
                    if config.id and config.id.upper() == target_id:
                        # Get the actual agent name with instance number
                        agent_counts = {}
                        instance_num = 0
                        
                        # Count how many instances of this agent type exist
                        total_count = sum(1 for c in PARALLEL_CONFIGS if c.agent_name == config.agent_name)
                        
                        # Count instances to find the right one
                        for idx, c in enumerate(PARALLEL_CONFIGS):
                            if c.agent_name == config.agent_name:
                                instance_num += 1
                                if c.id == config.id:
                                    break
                        
                        # Get display name
                        available_agents_dict = get_available_agents()
                        if config.agent_name in available_agents_dict:
                            agent = available_agents_dict[config.agent_name]
                            display_name = getattr(agent, "name", config.agent_name)
                            
                            # Add instance number if there are duplicates
                            if total_count > 1:
                                full_name = f"{display_name} #{instance_num}"
                            else:
                                full_name = display_name
                            
                            # Look for this agent in the available histories
                            # The histories might be stored with [ID] suffix
                            found_match = False
                            for agent_name in available_agents:
                                # Check if this history entry matches our agent
                                if f"[{target_id}]" in agent_name:
                                    parsed_agents.append(agent_name)
                                    found_match = True
                                    break
                                # Also check if the base name matches (without ID)
                                elif agent_name.startswith(full_name):
                                    parsed_agents.append(agent_name)
                                    found_match = True
                                    break
                                # Check case-insensitive match
                                elif agent_name.lower().startswith(full_name.lower()):
                                    parsed_agents.append(agent_name)
                                    found_match = True
                                    break
                            
                            if found_match:
                                found_by_id = True
                                break
                
                if found_by_id:
                    i += 1
                    continue
            
            # Try to match progressively longer combinations (for names with spaces)
            found_match = False

            # Start with the longest possible combination and work backwards
            for j in range(len(args), i, -1):
                potential_name = " ".join(args[i:j])
                potential_name_lower = potential_name.lower()

                # Check for case-insensitive match
                if potential_name_lower in agent_lookup:
                    parsed_agents.append(agent_lookup[potential_name_lower])
                    i = j
                    found_match = True
                    break
                # Also check exact match as fallback
                elif potential_name in available_agents:
                    parsed_agents.append(potential_name)
                    i = j
                    found_match = True
                    break

            # If no match found, skip this argument
            if not found_match:
                # Don't warn if it looks like a flag
                if not args[i].startswith("--"):
                    console.print(
                        f"[yellow]Warning: Agent '{args[i]}' not found in histories[/yellow]"
                    )
                i += 1

        return parsed_agents
    
    def handle_prompt(self, args: Optional[list[str]] = None) -> bool:
        """Handle the prompt subcommand to set custom prompts for agents.
        
        Args:
            args: Command arguments [agent_id/index] [prompt]
            
        Returns:
            True if successful
        """
        if not args or len(args) < 2:
            console.print("[red]Error: Agent ID/index and prompt required[/red]")
            console.print("Usage: /parallel prompt <ID/index> <prompt>")
            console.print("Example: /parallel prompt P1 Focus on SQL injection")
            console.print("Example: /parallel prompt 2 Look for authentication bypasses")
            return False
        
        identifier = args[0]
        prompt = " ".join(args[1:])
        
        # Find the config to update
        config_to_update = None
        index_to_update = -1
        
        # Try by ID first
        if identifier.upper().startswith("P"):
            for idx, config in enumerate(PARALLEL_CONFIGS):
                if config.id and config.id.upper() == identifier.upper():
                    config_to_update = config
                    index_to_update = idx + 1
                    break
        else:
            # Try by index
            try:
                idx = int(identifier)
                if 1 <= idx <= len(PARALLEL_CONFIGS):
                    config_to_update = PARALLEL_CONFIGS[idx - 1]
                    index_to_update = idx
            except ValueError:
                pass
        
        if not config_to_update:
            console.print(f"[red]Error: No agent found with ID/index '{identifier}'[/red]")
            return False
        
        # Update the prompt
        old_prompt = config_to_update.prompt
        config_to_update.prompt = prompt
        
        # Get display name
        from cai.agents import get_available_agents
        available_agents = get_available_agents()
        if config_to_update.agent_name in available_agents:
            agent = available_agents[config_to_update.agent_name]
            display_name = getattr(agent, "name", config_to_update.agent_name)
        else:
            display_name = config_to_update.agent_name
        
        console.print(f"[green]Updated prompt for {display_name} (ID: {config_to_update.id})[/green]")
        if old_prompt:
            console.print(f"[dim]Old prompt: {old_prompt}[/dim]")
        console.print(f"[cyan]New prompt: {prompt}[/cyan]")
        
        return True


# Register the command
register_command(ParallelCommand())
