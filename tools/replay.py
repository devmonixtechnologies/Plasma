#!/usr/bin/env python3
"""
Tool to convert JSONL files to a replay format that simulates the CLI output.
This allows reviewing conversations in a more readable format.

Usage:
    JSONL_FILE_PATH="path/to/file.jsonl" REPLAY_DELAY="0.5" python3 tools/replay.py

    # Or using positional arguments:
    python3 tools/replay.py path/to/file.jsonl 0.5
    cai-replay path/to/file.jsonl 0.5

    # Or using command line arguments:
    python3 tools/replay.py --jsonl-file-path path/to/file.jsonl --replay-delay 0.5

Usage with asciinema rec, generating a .cast file and then converting it to a gif:
    asciinema rec --command="python3 tools/replay.py path/to/file.jsonl 0.5" --overwrite

Or alternatively:
    asciinema rec --command="JSONL_FILE_PATH='caiextensions-memory/caiextensions/memory/it/pentestperf/hackableii/hackableII_autonomo.jsonl' REPLAY_DELAY='0.05' cai-replay"

Then convert the .cast file to a gif:
    agg /tmp/tmp6c4dxoac-ascii.cast demo.gif

Environment Variables:
    JSONL_FILE_PATH: Path to the JSONL file containing conversation history (required)
    REPLAY_DELAY: Time in seconds to wait between actions (default: 0.5)
"""
import re
import json
import os
import sys
import time
import argparse
from typing import Dict, List, Tuple

# Disable session recording for replay tool
os.environ["CAI_DISABLE_SESSION_RECORDING"] = "true"

# Add the parent directory to the path to import cai modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.box import ROUNDED
from rich.text import Text
from rich.console import Group
from rich.columns import Columns
from rich.rule import Rule

from cai.util import (
    cli_print_agent_messages,
    cli_print_tool_output,
    color,
    COST_TRACKER
)
from cai.sdk.agents.run_to_jsonl import get_token_stats, load_history_from_jsonl
from cai.repl.ui.banner import display_banner
from collections import defaultdict

# Initialize console object for rich printing
console = Console()


# Create our own display_execution_time function that uses our local console
def display_execution_time(metrics=None):
    """Display the total execution time with our local console."""
    if metrics is None:
        return

    # Create a panel for the execution time
    content = []
    content.append(f"Session Time: {metrics['session_time']}")
    content.append(f"Active Time: {metrics['active_time']}")
    content.append(f"Idle Time: {metrics['idle_time']}")

    if metrics.get('llm_time') and metrics['llm_time'] != "0.0s":
        content.append(
            f"LLM Processing Time: [bold yellow]{metrics['llm_time']}[/bold yellow] "
            f"[dim]({metrics['llm_percentage']:.1f}% of session)[/dim]"
        )

    time_panel = Panel(
        Group(*[Text(line) for line in content]),
        border_style="blue",
        box=ROUNDED,
        padding=(0, 1),
        title="[bold]Session Statistics[/bold]",
        title_align="left"
    )
    console.print(time_panel)


def load_jsonl(file_path: str) -> List[Dict]:
    """Load a JSONL file and return its contents as a list of dictionaries."""
    data = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    print(f"Warning: Skipping invalid JSON line: {line[:50]}...")
    return data

def detect_parallel_agents(messages: List[Dict]) -> Dict[str, str]:
    """
    Detect parallel agents from messages by analyzing sender field patterns.
    Returns a mapping of agent_id to agent_name.
    """
    agents = {}
    
    # Look for messages with sender field that follows parallel pattern
    for msg in messages:
        sender = msg.get("sender", "")
        # Match patterns like "Bug Bounter [P1]", "Red Team Agent [P2]" etc
        match = re.match(r"(.+?)\s*\[(P\d+)\]$", sender)
        if match:
            agent_name = match.group(1).strip()
            agent_id = match.group(2)
            agents[agent_id] = agent_name
    
    return agents


def replay_conversation(messages: List[Dict], replay_delay: float = 0.5, usage: Tuple = None, jsonl_file_path: str = None, full_data: List[Dict] = None) -> None:
    """
    Replay a conversation from a list of messages, printing in real-time.

    Args:
        messages: List of message dictionaries
        replay_delay: Time in seconds to wait between actions
        usage: Tuple containing (model_name, total_input_tokens, total_output_tokens,
               total_cost, active_time, idle_time)
        jsonl_file_path: Path to the original JSONL file for graph display
        full_data: Full JSONL data for additional metadata lookup
    """
    turn_counter = 0
    interaction_counter = 0
    debug = 0  # Always set debug to 2
    
    # Detect parallel agents
    parallel_agents = detect_parallel_agents(messages)
    is_parallel = len(parallel_agents) > 0
    
    # Store messages for graph display
    agent_messages = defaultdict(list)
    
    # Create a mapping of timestamps to agent names from full_data
    timestamp_to_agent = {}
    if full_data:
        for entry in full_data:
            if entry.get("agent_name") and entry.get("timestamp_iso"):
                timestamp_to_agent[entry["timestamp_iso"]] = entry["agent_name"]

    if not messages:
        print(color("No valid messages found in the JSONL file", fg="yellow"))
        return

    print(color(f"Replaying conversation with {len(messages)} messages...",
                fg="green"))
    
    if is_parallel:
        print(color(f"Detected {len(parallel_agents)} parallel agents:", fg="cyan"))
        for agent_id, agent_name in sorted(parallel_agents.items()):
            print(color(f"  • {agent_name} [{agent_id}]", fg="cyan"))

    # Extract the usage stats from the usage tuple
    # Handle both old format (4 elements) and new format (6 elements with timing)
    file_model = usage[0]
    total_input_tokens = usage[1]
    total_output_tokens = usage[2]
    total_cost = usage[3]

    # Check if timing information is available
    active_time = usage[4] if len(usage) > 4 else 0
    idle_time = usage[5] if len(usage) > 5 else 0

    # Display timing information if available
    if active_time > 0 or idle_time > 0:
        print(color(f"Active time: {active_time:.2f}s", fg="cyan"))
        print(color(f"Idle time: {idle_time:.2f}s", fg="cyan"))

    print(color(f"Total cost: ${total_cost:.6f}", fg="cyan"))
    
    # Initialize COST_TRACKER with the total cost from the JSONL file
    COST_TRACKER.session_total_cost = total_cost

    # First pass: Process all tool outputs
    tool_outputs = {}
    for idx, message in enumerate(messages):
        if message.get("role") == "tool" and message.get("tool_call_id"):
            tool_id = message.get("tool_call_id")
            content = message.get("content", "")
            tool_outputs[tool_id] = content

    # Process assistant messages to match tool calls with outputs
    for message in messages:
        if message.get("role") == "assistant" and message.get("tool_calls"):
            for tool_call in message.get("tool_calls", []):
                call_id = tool_call.get("id", "")
                if call_id in tool_outputs:
                    # Add this output to the tool_outputs of the assistant message
                    if "tool_outputs" not in message:
                        message["tool_outputs"] = {}
                    message["tool_outputs"][call_id] = tool_outputs[call_id]

    # Process all messages, including the last one
    total_messages = len(messages)
    cumulative_cost = 0.0  # Track cumulative cost for progressive updates
    
    for i, message in enumerate(messages):
        try:
            # Add delay between actions
            if i > 0:
                time.sleep(replay_delay)

            role = message.get("role", "")
            content = message.get("content")
            content = str(content).strip() if content is not None else ""
            sender = message.get("sender", role)
            model = message.get("model", file_model)
            
            # Update COST_TRACKER with cumulative cost up to this message
            message_cost = message.get("interaction_cost", 0.0)
            if message_cost > 0:
                cumulative_cost += message_cost
                COST_TRACKER.current_agent_total_cost = cumulative_cost
                COST_TRACKER.session_total_cost = cumulative_cost

            # Skip system messages
            if role == "system":
                continue

            # Store message for graph if parallel agents detected
            if is_parallel:
                # Determine agent for this message
                if role == "assistant":
                    # Extract agent ID from sender if present
                    agent_match = re.match(r"(.+?)\s*\[(P\d+)\]$", sender)
                    if agent_match:
                        agent_id = agent_match.group(2)
                        agent_messages[agent_id].append(message)
                elif role == "user":
                    # User messages go to all agents
                    for agent_id in parallel_agents:
                        agent_messages[agent_id].append(message)
                elif role == "tool":
                    # Tool messages go to the agent that called them
                    # Look back for the assistant message that made this tool call
                    tool_call_id = message.get("tool_call_id")
                    for j in range(i-1, -1, -1):
                        prev_msg = messages[j]
                        if prev_msg.get("role") == "assistant":
                            prev_sender = prev_msg.get("sender", "")
                            agent_match = re.match(r"(.+?)\s*\[(P\d+)\]$", prev_sender)
                            if agent_match:
                                agent_id = agent_match.group(2)
                                agent_messages[agent_id].append(message)
                                break
            
            # Handle user messages
            if role == "user":
                print(color(f"CAI> ", fg="cyan") + f"{content}")
                turn_counter += 1
                # Don't reset interaction_counter to maintain numbering across user prompts
            
            # Handle assistant messages
            elif role == "assistant":
                # Check if there are tool calls
                tool_calls = message.get("tool_calls", [])
                tool_outputs = message.get("tool_outputs", {})
                
                # Extract the actual agent name
                display_sender = sender
                
                # First, check if we have agent_name in the message metadata
                agent_name = message.get("agent_name")
                if agent_name:
                    display_sender = agent_name
                else:
                    # If still not found, try to extract from content patterns
                    if display_sender in ["assistant", role] and content:
                        # Look for patterns like "Agent: Bug Bounter >>" or "[0] Agent: Bug Bounter"
                        agent_match = re.search(r'(?:\[\d+\]\s*)?Agent:\s*([^>]+?)(?:\s*>>|\s*\[|$)', content)
                        if agent_match:
                            display_sender = agent_match.group(1).strip()
                    
                    # If still "assistant", default to a generic name
                    if display_sender == "assistant" or display_sender == role:
                        display_sender = "Assistant"

                if tool_calls:
                    # Print the assistant message with tool calls
                    cli_print_agent_messages(
                        display_sender,
                        content or "",
                        interaction_counter,
                        model,
                        debug,
                        interaction_input_tokens=message.get("input_tokens", 0),
                        interaction_output_tokens=message.get("output_tokens", 0),
                        interaction_reasoning_tokens=message.get("reasoning_tokens", 0),
                        total_input_tokens=total_input_tokens,
                        total_output_tokens=total_output_tokens,
                        total_reasoning_tokens=message.get("total_reasoning_tokens", 0),
                        interaction_cost=message.get("interaction_cost", 0.0),
                        total_cost=total_cost
                    )

                    # Print each tool call with its output
                    for tool_call in tool_calls:
                        function = tool_call.get("function", {})
                        name = function.get("name", "")
                        arguments = function.get("arguments", "{}")
                        call_id = tool_call.get("id", "")

                        # Get the tool output if available
                        tool_output = ""
                        if call_id and call_id in tool_outputs:
                            tool_output = tool_outputs[call_id]

                        # Skip empty tool calls
                        if not name:
                            continue

                        try:
                            # Try to parse arguments as JSON
                            if arguments and isinstance(arguments, str) and arguments.strip().startswith("{"):
                                args_obj = json.loads(arguments)
                            else:
                                args_obj = arguments
                                
                            # Special handling for execute_code to show full code
                            # Don't modify args_obj for execute_code, we'll handle display separately
                        except json.JSONDecodeError:
                            args_obj = arguments

                        # Special handling for execute_code to show the code
                        if name == "execute_code" and isinstance(args_obj, dict) and args_obj.get("code"):
                            # Show execute_code with full code content
                            from rich.panel import Panel
                            from rich.syntax import Syntax
                            
                            code = args_obj.get("code", "")
                            language = args_obj.get("language", "python")
                            filename = args_obj.get("filename", "exploit")
                            
                            # Create syntax highlighted code
                            syntax = Syntax(code, language, theme="monokai", line_numbers=True)
                            
                            # Create the panel with code
                            code_panel = Panel(
                                syntax,
                                title=f"[bold yellow]execute_code({filename}.{language})[/bold yellow]",
                                border_style="yellow",
                                padding=(0, 1)
                            )
                            console.print(code_panel)
                            
                            # If there's output, show it too
                            if tool_output:
                                output_panel = Panel(
                                    tool_output,
                                    title="[bold green]Output[/bold green]",
                                    border_style="green",
                                    padding=(0, 1)
                                )
                                console.print(output_panel)
                            
                            console.print()  # Add spacing
                        else:
                            # Print other tool calls normally
                            cli_print_tool_output(
                                tool_name=name,
                                args=args_obj,
                                output=tool_output,  # Use the matched tool output
                                call_id=call_id,
                                token_info={
                                    "interaction_input_tokens": message.get("input_tokens", 0),
                                    "interaction_output_tokens": message.get("output_tokens", 0),
                                    "interaction_reasoning_tokens": message.get("reasoning_tokens", 0),
                                    "total_input_tokens": total_input_tokens,
                                    "total_output_tokens": total_output_tokens,
                                    "total_reasoning_tokens": message.get("total_reasoning_tokens", 0),
                                    "model": model,
                                    "interaction_cost": message.get("interaction_cost", 0.0),
                                    "total_cost": total_cost
                                }
                            )
                else:
                    # Print regular assistant message
                    cli_print_agent_messages(
                        display_sender,
                        content or "",
                        interaction_counter,
                        model,
                        debug,
                        interaction_input_tokens=message.get("input_tokens", 0),
                        interaction_output_tokens=message.get("output_tokens", 0),
                        interaction_reasoning_tokens=message.get("reasoning_tokens", 0),
                        total_input_tokens=total_input_tokens,
                        total_output_tokens=total_output_tokens,
                        total_reasoning_tokens=message.get("total_reasoning_tokens", 0),
                        interaction_cost=message.get("interaction_cost", 0.0),
                        total_cost=total_cost
                    )
                interaction_counter += 1  # iterate the interaction counter

            # Handle tool messages - only those not already displayed with assistant messages
            elif role == "tool":
                # Check if we've already displayed this tool output with an assistant message
                tool_call_id = message.get("tool_call_id", "")

                # Skip tool messages that have been displayed with an assistant message
                is_already_displayed = False
                for prev_msg in messages[:i]:
                    if prev_msg.get("role") == "assistant" and tool_call_id in prev_msg.get("tool_outputs", {}):
                        is_already_displayed = True
                        break

                if not is_already_displayed and content:  # Only show if there's actual content
                    tool_name = message.get("name", message.get("tool_call_id", "unknown"))
                    cli_print_tool_output(
                        tool_name=tool_name,
                        args="",
                        output=content,
                        token_info={
                            "interaction_input_tokens": message.get("input_tokens", 0),
                            "interaction_output_tokens": message.get("output_tokens", 0),
                            "interaction_reasoning_tokens": message.get("reasoning_tokens", 0),
                            "total_input_tokens": total_input_tokens,
                            "total_output_tokens": total_output_tokens,
                            "total_reasoning_tokens": message.get("total_reasoning_tokens", 0),
                            "model": model,
                            "interaction_cost": message.get("interaction_cost", 0.0),
                            "total_cost": total_cost
                        }
                    )

            # Handle any other message types (including final messages)
            else:
                # Always show the last message even if it seems empty
                if content or (i == total_messages - 1 and role not in ["system", "tool"]):
                    cli_print_agent_messages(
                        sender or role,
                        content or "[Session ended]",
                        interaction_counter,
                        model,
                        debug,
                        interaction_input_tokens=message.get("input_tokens", 0),
                        interaction_output_tokens=message.get("output_tokens", 0),
                        interaction_reasoning_tokens=message.get("reasoning_tokens", 0),
                        total_input_tokens=total_input_tokens,
                        total_output_tokens=total_output_tokens,
                        total_reasoning_tokens=message.get("total_reasoning_tokens", 0),
                        interaction_cost=message.get("interaction_cost", 0.0),
                        total_cost=total_cost
                    )

            # Force flush stdout to ensure immediate printing
            sys.stdout.flush()

        except Exception as e:
            # Handle any errors during message processing
            print(color(f"Warning: Error processing message {i+1}: {str(e)}", fg="yellow"))
            print(color("Continuing with next message...", fg="yellow"))
            continue
    
    # Display graph at the end if parallel agents detected
    if is_parallel and agent_messages:
        display_parallel_graph(agent_messages, parallel_agents)


def display_parallel_graph(agent_messages: Dict[str, List[Dict]], parallel_agents: Dict[str, str]) -> None:
    """Display a graph showing the parallel agent interactions."""
    print("\n" + "=" * 80)
    print(color("\n🎯 Parallel Agent Interaction Graph", fg="cyan", style="bold"))
    print("=" * 80 + "\n")
    
    graphs = []
    
    for agent_id in sorted(parallel_agents.keys()):
        agent_name = parallel_agents[agent_id]
        messages = agent_messages.get(agent_id, [])
        
        if not messages:
            continue
        
        # Build graph for this agent
        graph_lines = []
        turn_counter = 0
        
        for i, msg in enumerate(messages):
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "user":
                # User messages don't get turn numbers
                if len(content) > 50:
                    content = content[:47] + "..."
                graph_lines.append(f"[cyan]● User[/cyan]")
                graph_lines.append(f"  {content}")
            elif role == "assistant":
                turn_counter += 1
                tool_calls = msg.get("tool_calls", [])
                if tool_calls:
                    tools_str = ", ".join([tc.get("function", {}).get("name", "?") for tc in tool_calls[:3]])
                    if len(tool_calls) > 3:
                        tools_str += f" (+{len(tool_calls)-3})"
                    graph_lines.append(f"[bold red][{turn_counter}][/bold red] [yellow]▶ Agent[/yellow]")
                    graph_lines.append(f"  [dim]Tools: {tools_str}[/dim]")
                else:
                    graph_lines.append(f"[bold red][{turn_counter}][/bold red] [yellow]▶ Agent[/yellow]")
                    if content and len(content.strip()) > 0:
                        preview = content[:50] + "..." if len(content) > 50 else content
                        graph_lines.append(f"  [dim]{preview}[/dim]")
            elif role == "tool":
                # Tool responses get the same turn number as their assistant
                graph_lines.append(f"[bold red][{turn_counter}][/bold red] [magenta]◆ Tool[/magenta]")
                if content:
                    preview = content[:50] + "..." if len(content) > 50 else content
                    graph_lines.append(f"  [dim]{preview}[/dim]")
            
            if i < len(messages) - 1:
                graph_lines.append("    ↓")
        
        # Create panel for this agent
        agent_panel = Panel(
            "\n".join(graph_lines),
            title=f"[bold cyan]{agent_name} [{agent_id}][/bold cyan]",
            border_style="blue",
            padding=(0, 1),
            expand=False
        )
        graphs.append(agent_panel)
    
    # Display graphs in columns
    if len(graphs) > 1:
        console.print(Columns(graphs, equal=False, expand=False, padding=(1, 2)))
    elif graphs:
        console.print(graphs[0])
    
    # Print summary
    console.print("\n[bold]Summary:[/bold]")
    total_messages = sum(len(msgs) for msgs in agent_messages.values())
    unique_user_messages = len(set(
        msg.get("content", "") 
        for msgs in agent_messages.values() 
        for msg in msgs 
        if msg.get("role") == "user"
    ))
    
    console.print(f"• Total agents: {len(parallel_agents)}")
    console.print(f"• Total messages: {total_messages}")
    console.print(f"• User messages: {unique_user_messages}")
    console.print(f"• Average messages per agent: {total_messages / len(parallel_agents) if parallel_agents else 0:.1f}")
    print("\n" + "=" * 80)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Tool to convert JSONL files to a replay format that simulates the CLI output.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using environment variables:
  JSONL_FILE_PATH="path/to/file.jsonl" REPLAY_DELAY="0.5" python3 tools/replay.py

  # Using positional arguments:
  python3 tools/replay.py path/to/file.jsonl 0.5
  cai-replay path/to/file.jsonl 0.5

  # Using command line arguments:
  python3 tools/replay.py --jsonl-file-path path/to/file.jsonl --replay-delay 0.5

  # Using positional argument for file only:
  python3 tools/replay.py path/to/file.jsonl --replay-delay 0.5

  # With asciinema:
  asciinema rec --command="python3 tools/replay.py path/to/file.jsonl 0.5" --overwrite
"""
    )

    parser.add_argument(
        "jsonl_file",
        nargs="?",
        default=None,
        help="Path to the JSONL file containing conversation history"
    )

    parser.add_argument(
        "replay_delay_pos",
        nargs="?",
        type=float,
        default=None,
        help="Time in seconds to wait between actions (positional argument)"
    )

    parser.add_argument(
        "--jsonl-file-path",
        type=str,
        help="Path to the JSONL file containing conversation history"
    )

    parser.add_argument(
        "--replay-delay",
        type=float,
        default=0.5,
        help="Time in seconds to wait between actions (default: 0.5)"
    )

    return parser.parse_args()


def main():
    """Main function to process JSONL files and generate replay output."""
    # Display banner
    display_banner(console)
    print("\n")

    # Parse command line arguments
    args = parse_arguments()

    # Get environment variables or command line arguments
    # First check for --jsonl-file-path, then positional argument, then environment variable
    jsonl_file_path = args.jsonl_file_path or args.jsonl_file or os.environ.get("JSONL_FILE_PATH")

    # For replay delay, prioritize: positional arg > --replay-delay > environment variable > default
    if args.replay_delay_pos is not None:
        replay_delay = args.replay_delay_pos
    elif args.replay_delay != 0.5:  # Check if --replay-delay was explicitly set
        replay_delay = args.replay_delay
    else:
        replay_delay = float(os.environ.get("REPLAY_DELAY", "0.5"))

    # Validate required parameters
    if not jsonl_file_path:
        print(color("Error: JSONL file path is required. Use a positional argument, --jsonl-file-path option, or set JSONL_FILE_PATH environment variable.",
                    fg="red"))
        sys.exit(1)

    print(color(f"Loading JSONL file: {jsonl_file_path}", fg="blue"))

    try:
        # Load the full JSONL file to extract tool outputs and agent names
        full_data = load_jsonl(jsonl_file_path)

        # Extract tool outputs from events and find last assistant message
        tool_outputs = {}
        agent_names = {}  # Store agent names by timestamp or other identifier

        # Extract agent names from full data
        current_agent_name = None
        for entry in full_data:
            # Track the current agent name from various events
            if entry.get("agent_name"):
                current_agent_name = entry.get("agent_name")
                # Store agent name with timestamp or other identifier
                timestamp = entry.get("timestamp")
                if timestamp:
                    agent_names[timestamp] = entry.get("agent_name")
            
            # Also look for agent_run_start events which contain agent names
            if entry.get("event") == "agent_run_start" and entry.get("agent_name"):
                current_agent_name = entry.get("agent_name")
        
        # Load the JSONL file for messages
        messages = load_history_from_jsonl(jsonl_file_path)

        # Attach tool outputs and agent names to messages
        # Also track current agent for messages without timestamps
        last_known_agent = current_agent_name
        
        for i, message in enumerate(messages):
            # Try to match agent names by timestamp
            msg_timestamp = message.get("timestamp")
            if msg_timestamp and msg_timestamp in agent_names:
                message["agent_name"] = agent_names[msg_timestamp]
                last_known_agent = agent_names[msg_timestamp]
            elif message.get("role") == "assistant" and not message.get("agent_name") and last_known_agent:
                # If no timestamp match but we have a last known agent, use it
                message["agent_name"] = last_known_agent
            
            if message.get("role") == "assistant" and message.get("tool_calls"):
                if "tool_outputs" not in message:
                    message["tool_outputs"] = {}

                for tool_call in message.get("tool_calls", []):
                    call_id = tool_call.get("id", "")
                    if call_id in tool_outputs:
                        message["tool_outputs"][call_id] = tool_outputs[call_id]

        print(color(f"Loaded {len(messages)} messages from JSONL file", fg="blue"))

        # Get token stats and cost from the JSONL file
        usage = get_token_stats(jsonl_file_path)

        # Display timing information if available (new format)
        if len(usage) > 4:
            print(color(f"Active time: {usage[4]:.2f}s", fg="blue"))
            print(color(f"Idle time: {usage[5]:.2f}s", fg="blue"))

        # Pass full_data to replay_conversation for agent name lookup
        replay_conversation(messages, replay_delay, usage, jsonl_file_path, full_data)
        print(color("Replay completed successfully", fg="green"))

        # Display the total cost
        active_time = usage[4] if len(usage) > 4 else 0
        idle_time = usage[5] if len(usage) > 5 else 0
        total_time = active_time + idle_time

        # Format time values as strings with units
        def format_time(seconds):
            """Format time in seconds to a human-readable string."""
            if seconds < 60:
                return f"{seconds:.1f}s"
            else:
                # Convert seconds to hours, minutes, seconds
                hours, remainder = divmod(seconds, 3600)
                minutes, seconds = divmod(remainder, 60)

                if hours > 0:
                    return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
                else:
                    return f"{int(minutes)}m {int(seconds)}s"

        metrics = {
            'session_time': format_time(total_time),
            'llm_time': "0.0s",
            'llm_percentage': 0,
            'active_time': format_time(active_time),
            'idle_time': format_time(idle_time)
        }
        display_execution_time(metrics)

    except FileNotFoundError:
        print(color(f"Error: File {jsonl_file_path} not found", fg="red"))
        sys.exit(1)
    except json.JSONDecodeError:
        print(color(f"Error: Invalid JSON in {jsonl_file_path}", fg="red"))
        sys.exit(1)
    except Exception as e:
        print(color(f"Error: {str(e)}", fg="red"))
        sys.exit(1)


if __name__ == "__main__":
    main()
