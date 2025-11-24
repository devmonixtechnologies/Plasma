"""
Shell command for CAI REPL.
This module provides commands for executing shell commands.
"""
import os
import signal
import subprocess  # nosec B404
from typing import (
    List,
    Optional
)
from rich.console import Console  # pylint: disable=import-error

from cai.repl.commands.base import Command, register_command
from cai.tools.common import _get_workspace_dir, _get_container_workspace_path

console = Console()


class ShellCommand(Command):
    """Command for executing shell commands."""

    def __init__(self):
        """Initialize the shell command."""
        super().__init__(
            name="/shell",
            description="Execute shell commands in the current environment",
            aliases=["/s", "$"]
        )

    def handle(self, args: Optional[List[str]] = None) -> bool:
        """Handle the shell command.

        Args:
            args: Optional list of command arguments

        Returns:
            True if the command was handled successfully, False otherwise
        """
        if not args:
            console.print("[red]Error: No command specified[/red]")
            return False

        return self.handle_shell_command(args)

    def handle_shell_command(self, command_args: List[str]) -> bool:
        if not command_args:
            console.print("[red]Error: No command specified[/red]")
            return False

        original_command = " ".join(command_args)
        active_container = os.getenv("CAI_ACTIVE_CONTAINER", "")

        # List of known async-style commands
        is_async = any(cmd in original_command for cmd in ['nc', 'netcat', 'ncat', 'telnet', 'ssh', 'python -m http.server'])

        def run_command(command, cwd=None):
            """Execute the given command, optionally in a different working directory (cwd).
            Handles output, async vs sync execution, and user interrupts (Ctrl+C).
            """
            try:
                # Temporary SIGINT handler to allow Ctrl+C to interrupt only this process
                signal.signal(signal.SIGINT, lambda s, f: (_ for _ in ()).throw(KeyboardInterrupt()))

                if is_async:
                    console.print("[yellow]Running in async mode (Ctrl+C to return to REPL)[/yellow]")
                    os.system(command)
                    console.print("[green]Async command completed or detached[/green]")
                    return True

                # Run synchronously and stream output
                process = subprocess.Popen(
                    command, shell=True, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, universal_newlines=True,
                    bufsize=1, cwd=cwd
                )
                for line in iter(process.stdout.readline, ''):
                    print(line, end='')

                process.wait()

                if process.returncode == 0:
                    console.print("[green]Command completed successfully[/green]")
                else:
                    console.print(f"[yellow]Command exited with code {process.returncode}[/yellow]")
                return True

            except KeyboardInterrupt:
                # Terminate process on user interrupt
                if not is_async:
                    process.terminate()
                console.print("\n[yellow]Command interrupted by user[/yellow]")
                return True
            except Exception as e:
                # Handle general execution errors
                console.print(f"[red]Execution error: {e}[/red]")
                return False
            finally:
                # Restore original SIGINT behavior
                signal.signal(signal.SIGINT, signal.getsignal(signal.SIGINT))

        if active_container:
            # If running in a Docker container
            container_workspace = _get_container_workspace_path()
            console.print(f"[dim]Running in container: {active_container[:12]}...[/dim]")
            docker_cmd = f"docker exec -w '{container_workspace}' {active_container} sh -c {original_command!r}"
            console.print(f"[blue]Executing in container workspace '{container_workspace}':[/blue] {original_command}")

            success = run_command(docker_cmd)

            # Retry on host if container execution fails
            if not success and "Error response from daemon" in original_command:
                console.print("[yellow]Container error. Executing on local host.[/yellow]")
                os.environ.pop("CAI_ACTIVE_CONTAINER", None)
                return self.handle_shell_command(command_args)

            return success

        # If no container, run command in local workspace
        host_workspace = _get_workspace_dir()
        console.print(f"[dim]Running in workspace: {host_workspace}[/dim]")

        return run_command(original_command, cwd=host_workspace)


# Register the command
register_command(ShellCommand())
