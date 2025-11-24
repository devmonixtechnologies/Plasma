"""
Quickstart command for CAI REPL.
Provides essential setup information and guidance for new users.
Automatically runs on first launch if ~/.cai doesn't exist.
"""

import os
import subprocess
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from cai.repl.commands.base import Command, register_command

console = Console()


class QuickstartCommand(Command):
    """Command for displaying quickstart guide and setup information."""

    def __init__(self):
        """Initialize the quickstart command."""
        super().__init__(
            name="/quickstart",
            description="Display quickstart guide and setup information",
            aliases=["/qs", "/quick"],
        )

    def handle_no_args(self) -> bool:
        """Handle the command when no arguments are provided."""
        return self.show_quickstart()

    def check_local_endpoint(self, url: str) -> tuple[bool, str]:
        """Check if a local endpoint is accessible.
        
        Args:
            url: The endpoint URL to check
            
        Returns:
            Tuple of (is_accessible, message)
        """
        try:
            # Try using httpx which is already imported by the project
            import httpx
            with httpx.Client(timeout=2.0) as client:
                response = client.get(url)
                if response.status_code == 200:
                    return True, "✅ Accessible"
                else:
                    return False, f"❌ Error: HTTP {response.status_code}"
        except httpx.ConnectError:
            return False, "❌ Connection refused"
        except httpx.TimeoutException:
            return False, "❌ Timeout"
        except ImportError:
            # Fallback if httpx not available
            try:
                import urllib.request
                import urllib.error
                with urllib.request.urlopen(url, timeout=2) as response:
                    if response.status == 200:
                        return True, "✅ Accessible"
                    else:
                        return False, f"❌ Error: HTTP {response.status}"
            except urllib.error.URLError:
                return False, "❌ Connection refused"
            except Exception:
                return False, "❌ Error checking endpoint"
        except Exception as e:
            return False, f"❌ Error: {str(e)}"

    def check_ollama_models(self) -> List[str]:
        """Check available Ollama models."""
        try:
            import httpx
            with httpx.Client(timeout=2.0) as client:
                response = client.get("http://localhost:11434/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return [model['name'] for model in data.get('models', [])]
        except ImportError:
            # Fallback if httpx not available
            try:
                import urllib.request
                import json
                with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as response:
                    if response.status == 200:
                        data = json.loads(response.read())
                        return [model['name'] for model in data.get('models', [])]
            except:
                pass
        except:
            pass
        return []

    def get_provider_name(self, api_key: str) -> str:
        """Get a formatted provider name from API key name.
        
        Args:
            api_key: Environment variable name (e.g., OPENAI_API_KEY)
            
        Returns:
            Formatted provider name
        """
        # Remove _API_KEY suffix to get provider name
        provider_part = api_key.replace("_API_KEY", "")
        
        # Convert SOME_PROVIDER to Some Provider
        # Handle special cases for better formatting
        if provider_part == "OPENAI":
            return "OpenAI"
        elif provider_part == "XAI":
            return "xAI"
        elif provider_part == "HUGGINGFACE":
            return "HuggingFace"
        elif provider_part == "OPENROUTER":
            return "OpenRouter"
        elif provider_part == "DEEPSEEK":
            return "DeepSeek"
        else:
            # General case: convert SOME_PROVIDER to Some Provider
            return provider_part.replace("_", " ").title()
    
    def check_api_keys(self) -> dict[str, bool]:
        """Check which API keys are configured dynamically."""
        keys = {}
        
        # Scan all environment variables for *_API_KEY pattern
        for env_var in os.environ:
            if env_var.endswith("_API_KEY"):
                # Check if the value is set and not empty
                keys[env_var] = bool(os.getenv(env_var))
        
        # Also check .env file for any API keys not in current environment
        try:
            from pathlib import Path
            env_file = Path.home() / "cai" / ".env"
            if not env_file.exists():
                # Try current directory
                env_file = Path(".env")
            
            if env_file.exists():
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if '=' in line and not line.startswith('#'):
                            key, _ = line.split('=', 1)
                            key = key.strip()
                            if key.endswith("_API_KEY") and key not in keys:
                                # Check if it's in environment (might be loaded)
                                keys[key] = bool(os.getenv(key))
        except:
            pass
        
        # Sort keys alphabetically for consistent display
        return dict(sorted(keys.items()))

    def show_quickstart(self) -> bool:
        """Display the quickstart guide."""
        # Welcome banner
        console.print(
            Panel(
                Text.from_markup(
                    "[bold cyan]Welcome to CAI (Cybersecurity AI)![/bold cyan]\n\n"
                    "[yellow]AI-powered security framework for penetration testing, "
                    "bug bounty hunting, and CTF challenges.[/yellow]\n\n"
                    "This quickstart guide will help you get started with CAI."
                ),
                title="🚀 CAI Quickstart",
                border_style="cyan",
                box=box.DOUBLE,
            )
        )

        # Step 1: API Requirements
        console.print("\n[bold yellow]📋 Step 1: API Requirements[/bold yellow]\n")
        console.print("CAI requires at least one AI provider API key to function:")
        
        api_keys = self.check_api_keys()
        
        # Create API status table
        api_table = Table(show_header=True, header_style="bold")
        api_table.add_column("Provider", style="cyan")
        api_table.add_column("Environment Variable", style="yellow")
        api_table.add_column("Status", style="green")
        
        # Dynamically build provider list from detected API keys
        for env_var, is_set in api_keys.items():
            provider_name = self.get_provider_name(env_var)
            status = "✅ Set" if is_set else "❌ Not set"
            api_table.add_row(provider_name, env_var, status)
        
        console.print(api_table)
        
        if not any(api_keys.values()):
            console.print(
                Panel(
                    "[red]⚠️  No API keys detected![/red]\n\n"
                    "You need at least one API key to use CAI.\n"
                    "Set it in your shell or .env file:\n\n"
                    "[yellow]export PROVIDER_API_KEY='your-key-here'[/yellow]\n\n"
                    "Replace PROVIDER with your model provider name\n",
                    border_style="red",
                )
            )

        # Step 2: Local Models (Ollama)
        console.print("\n[bold yellow]🖥️  Step 2: Local Models (Optional)[/bold yellow]\n")
        console.print("For local model support, CAI can use Ollama:")
        
        # Check Ollama endpoints
        ollama_table = Table(show_header=True, header_style="bold")
        ollama_table.add_column("Endpoint", style="cyan")
        ollama_table.add_column("Status", style="green")
        ollama_table.add_column("Models", style="yellow")
        
        # Check standard Ollama port
        is_accessible, status = self.check_local_endpoint("http://localhost:11434")
        models = self.check_ollama_models() if is_accessible else []
        model_str = f"{len(models)} models" if models else "N/A"
        ollama_table.add_row("http://localhost:11434", status, model_str)
        
        # Check Docker internal
        is_docker_accessible, docker_status = self.check_local_endpoint("http://host.docker.internal:11434")
        ollama_table.add_row("http://host.docker.internal:11434", docker_status, "Docker access")
        
        console.print(ollama_table)
        
        if is_accessible and models:
            console.print(f"\n[green]Available Ollama models:[/green] {', '.join(models[:5])}")
            if len(models) > 5:
                console.print(f"[dim]... and {len(models) - 5} more[/dim]")
        
        console.print(
            Panel(
                "[cyan]To use Ollama:[/cyan]\n"
                "1. Install: [yellow]curl -fsSL https://ollama.com/install.sh | sh[/yellow]\n"
                "2. Pull a model: [yellow]ollama pull llama3.1[/yellow]\n"
                "3. Set in .env: "
                "[yellow]OLLAMA_API_BASE='http://127.0.0.1:11434/v1'[/yellow]\n"
                "4. Use in CAI: [yellow]/model llama3.1[/yellow]",
                border_style="cyan",
            )
        )

        # Step 3: Choose Your Model
        console.print("\n[bold yellow]🤖 Step 3: Choose Your Model[/bold yellow]\n")
        
        # Check which API keys are available
        has_api_keys = any(api_keys.values())
        
        if has_api_keys:
            console.print("Great! You have API keys configured. Now you need to select a model.")
            console.print("\n[cyan]To see which models are available for your API keys:[/cyan]")
            console.print("  [yellow]1.[/yellow] Run: [bold green]/model-show[/bold green] to see all available models")
            console.print("  [yellow]2.[/yellow] Run: [bold green]/model-show supported[/bold green] to see only models with function calling support")
            console.print("  [yellow]3.[/yellow] Select a model: [bold green]/model <model-name>[/bold green]")
            console.print("\n[dim]Note: The default model 'alias0' requires configuration. Please select a specific model.[/dim]")
        else:
            console.print(
                Panel(
                    "[red]⚠️  No API keys detected![/red]\n\n"
                    "You need to set up at least one API key before choosing a model.\n"
                    "Once you have an API key configured:\n\n"
                    "1. Run [yellow]/model-show[/yellow] to see available models\n"
                    "2. Select a model with [yellow]/model <model-name>[/yellow]",
                    border_style="red",
                )
            )
        
        # Step 4: Core Commands
        console.print("\n[bold yellow]🎯 Step 4: Essential Commands[/bold yellow]\n")
        
        commands_table = Table(show_header=True, header_style="bold", box=box.SIMPLE)
        commands_table.add_column("Command", style="cyan")
        commands_table.add_column("Description", style="white")
        commands_table.add_column("Example", style="green")
        
        essential_commands = [
            ("/agent list", "View available agents", "/agent list"),
            ("/agent select <name>", "Switch to specific agent", "/agent select red_teamer"),
            ("/model", "View current model", "/model"),
            ("/model-show", "List all available models", "/model-show"),
            ("/model <name>", "Change AI model", "/model gpt-4o"),
            ("/config", "View all settings", "/config"),
            ("/help", "Get detailed help", "/help agent"),
            ("/shell <cmd>", "Run shell command", "/shell ls -la"),
            ("$ <cmd>", "Quick shell command", "$ whoami"),
        ]
        
        for cmd, desc, example in essential_commands:
            commands_table.add_row(cmd, desc, example)
        
        console.print(commands_table)

        # Step 5: Quick Examples
        console.print("\n[bold yellow]💡 Step 5: Quick Examples[/bold yellow]\n")
        
        examples = [
            ("[bold]Basic CTF Challenge:[/bold]", [
                "# Select the CTF agent",
                "/agent select one_tool_agent",
                "# Describe your challenge",
                "I have a binary at /tmp/challenge that asks for a password",
            ]),
            ("[bold]Web Security Testing:[/bold]", [
                "# Switch to bug bounty agent",
                "/agent select bug_bounter",
                "# Test a website",
                "Test https://example.com for common vulnerabilities",
            ]),
            ("[bold]Network Reconnaissance:[/bold]", [
                "# Use the red team agent",
                "/agent select red_teamer",
                "# Scan network",
                "Scan the network 192.168.1.0/24 for open ports",
            ]),
        ]
        
        for title, commands in examples:
            console.print(f"{title}")
            for cmd in commands:
                if cmd.startswith("#"):
                    console.print(f"  [dim]{cmd}[/dim]")
                else:
                    console.print(f"  [green]→[/green] [yellow]{cmd}[/yellow]")
            console.print()

        # Step 6: Features Overview
        console.print("\n[bold yellow]🛠️  Step 6: Key Features[/bold yellow]\n")
        
        features_table = Table(show_header=False, box=None)
        features_table.add_column(style="cyan", width=25)
        features_table.add_column(style="white")
        
        features = [
            ("Multiple Agents", "Specialized AI agents for different security tasks"),
            ("Tool Integration", "Execute commands, analyze code, search web"),
            ("Parallel Execution", "Run multiple agents simultaneously"),
            ("Memory System", "Persistent context across sessions"),
            ("MCP Support", "Extend with external tool servers"),
            ("Docker Integration", "Run tools in isolated containers"),
        ]
        
        for feature, desc in features:
            features_table.add_row(f"  • {feature}", desc)
        
        console.print(features_table)

        # Configuration directory info
        cai_dir = Path.home() / ".cai"
        console.print("\n[bold yellow]📁 Configuration Directory[/bold yellow]\n")
        console.print(f"CAI stores configuration and logs in: [cyan]{cai_dir}[/cyan]")
        
        if not cai_dir.exists():
            console.print("[yellow]→ This directory will be created on first run[/yellow]")
        else:
            console.print("[green]✓ Directory exists[/green]")

        # Next steps
        console.print(
            Panel(
                "[bold]🎉 You're ready to start![/bold]\n\n"
                "[cyan]Next steps:[/cyan]\n"
                "1. Set up at least one API key (see table above)\n"
                "2. Try the examples to get familiar with CAI\n"
                "3. Use [yellow]/help[/yellow] for detailed command information\n"
                "4. Join our community for support and updates\n\n"
                "[dim]This guide: /quickstart | Hide on startup: Create ~/.cai directory[/dim]",
                title="Ready to Go!",
                border_style="green",
            )
        )

        return True


# Register the command
register_command(QuickstartCommand())