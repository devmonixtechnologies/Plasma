"""
Data recorder
"""

import os  # pylint: disable=import-error
from datetime import datetime
import json
import socket
import urllib.request
import getpass
import platform
from urllib.error import URLError
import pytz  # pylint: disable=import-error
import uuid  # Add uuid import
from cai.util import get_active_time, get_idle_time
import atexit
from typing import List, Dict, Tuple

# Global recorder instance for session-wide logging
_session_recorder = None


def get_session_recorder(workspace_name=None):
    """
    Get the global session recorder instance.
    If one doesn't exist, it will be created.

    Args:
        workspace_name (str | None): Optional workspace name.

    Returns:
        DataRecorder: The session recorder instance.
    """
    global _session_recorder
    
    # Check if session recording is disabled (e.g., during replay)
    if os.environ.get("CAI_DISABLE_SESSION_RECORDING", "").lower() == "true":
        return None
    
    if _session_recorder is None:
        _session_recorder = DataRecorder(workspace_name)
    return _session_recorder


class DataRecorder:  # pylint: disable=too-few-public-methods
    """
    Records training data from litellm.completion
    calls in OpenAI-like JSON format.

    Stores both input messages and completion
    responses during execution in a single JSONL file.
    """

    def __init__(self, workspace_name: str | None = None):
        """
        Initializes the DataRecorder.

        Args:
            workspace_name (str | None): The name of the current workspace.
        """
        # Generate a session ID that will be used for the entire session
        self.session_id = str(uuid.uuid4())

        # Track the last message to ensure it's logged
        self.last_assistant_message = None
        self.last_assistant_tool_calls = None
        self._last_message_logged = False
        self._session_end_logged = False

        log_dir = 'logs'
        os.makedirs(log_dir, exist_ok=True)

        # Get current username
        try:
            username = getpass.getuser()
        except Exception:  # pylint: disable=broad-except
            username = "unknown"

        # Get operating system and version information
        try:
            os_name = platform.system().lower()
            os_version = platform.release()
            os_info = f"{os_name}_{os_version}"
        except Exception:  # pylint: disable=broad-except
            os_info = "unknown_os"

        # Check internet connection and get public IP
        public_ip = "127.0.0.1"
        try:
            # Quick connection check with minimal traffic
            socket.create_connection(("1.1.1.1", 53), timeout=1)

            # If connected, try to get public IP
            try:
                # Using a simple and lightweight service
                with urllib.request.urlopen(  # nosec: B310
                    "https://api.ipify.org",
                    timeout=2
                ) as response:
                    public_ip = response.read().decode('utf-8')
            except (URLError, socket.timeout):
                # Fallback to another service if the first one fails
                try:
                    with urllib.request.urlopen(  # nosec: B310
                        "https://ifconfig.me",
                        timeout=2
                    ) as response:
                        public_ip = response.read().decode('utf-8')
                except (URLError, socket.timeout):
                    # If both services fail, keep the default value
                    pass
        except (OSError, socket.timeout, socket.gaierror):
            # No internet connection, keep the default value
            pass

        # Create filename with username, OS info, and IP
        timestamp = datetime.now().astimezone(
            pytz.timezone("Europe/Madrid")).strftime("%Y%m%d_%H%M%S")
        base_filename = f'cai_{self.session_id}_{timestamp}_{username}_{os_info}_{public_ip.replace(".", "_")}.jsonl'

        if workspace_name:
            self.filename = os.path.join(
                log_dir, f'{workspace_name}_{base_filename}'
            )
        else:
            self.filename = os.path.join(log_dir, base_filename)

        # Inicializar el coste total acumulado
        self.total_cost = 0.0

        # Log the session start
        with open(self.filename, 'a', encoding='utf-8') as f:
            session_start = {
                "event": "session_start",
                "timestamp": datetime.now().astimezone(
                    pytz.timezone("Europe/Madrid")).isoformat(),
                "session_id": self.session_id
            }
            json.dump(session_start, f)
            f.write('\n')

    def rec_training_data(self, create_params, msg, total_cost=None, agent_name=None) -> None:
        """
        Records a single training data entry to the JSONL file

        Args:
            create_params: Parameters used for the LLM call
            msg: Response from the LLM
            total_cost: Optional total accumulated cost from CAI instance
            agent_name: Optional agent name/type for tracking
        """
        request_data = {
            "model": create_params["model"],
            "messages": create_params["messages"],
            "stream": create_params["stream"]
        }
        if "tools" in create_params:
            request_data.update({
                "tools": create_params["tools"],
                "tool_choice": create_params["tool_choice"],
            })

        # Obtener el coste de la interacción
        interaction_cost = 0.0
        if hasattr(msg, "cost"):
            interaction_cost = float(msg.cost) if msg.cost is not None else 0.0

        # Usar el total_cost proporcionado o actualizar el interno
        if total_cost is not None:
            self.total_cost = float(total_cost)
        else:
            self.total_cost += interaction_cost

        # Get timing metrics (without units, just numeric values)
        active_time_str = get_active_time()
        idle_time_str = get_idle_time()

        # Convert string time to seconds for storage
        def time_str_to_seconds(time_str):
            if "h" in time_str:
                parts = time_str.split()
                hours = float(parts[0].replace("h", ""))
                minutes = float(parts[1].replace("m", ""))
                seconds = float(parts[2].replace("s", ""))
                return hours * 3600 + minutes * 60 + seconds
            if "m" in time_str:
                parts = time_str.split()
                minutes = float(parts[0].replace("m", ""))
                seconds = float(parts[1].replace("s", ""))
                return minutes * 60 + seconds
            return float(time_str.replace("s", ""))

        active_time_seconds = time_str_to_seconds(active_time_str)
        idle_time_seconds = time_str_to_seconds(idle_time_str)

        # Get token usage from the usage object - handle both field names
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        
        if hasattr(msg, "usage"):
            # Try input_tokens first (ResponseUsage)
            if hasattr(msg.usage, "input_tokens"):
                prompt_tokens = msg.usage.input_tokens
            # Fall back to prompt_tokens (ChatCompletion)
            elif hasattr(msg.usage, "prompt_tokens"):
                prompt_tokens = msg.usage.prompt_tokens
                
            # Try output_tokens first (ResponseUsage)
            if hasattr(msg.usage, "output_tokens"):
                completion_tokens = msg.usage.output_tokens
            # Fall back to completion_tokens (ChatCompletion)
            elif hasattr(msg.usage, "completion_tokens"):
                completion_tokens = msg.usage.completion_tokens
                
            # Get total tokens - calculate if not available
            if hasattr(msg.usage, "total_tokens"):
                total_tokens = msg.usage.total_tokens
            else:
                total_tokens = prompt_tokens + completion_tokens

        completion_data = {
            "id": msg.id,
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": msg.model,
            "agent_name": agent_name if agent_name else "unknown",
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "tool_calls": [t.model_dump() for t in (m.tool_calls or [])]  # pylint: disable=line-too-long  # noqa: E501
                }
                for m in msg.messages
            ] if hasattr(msg, "messages") else [],
            "choices": [{
                "index": 0,
                "message": {
                    "role": msg.choices[0].message.role if hasattr(msg, "choices") and msg.choices else "assistant",
                    "content": msg.choices[0].message.content if hasattr(msg, "choices") and msg.choices else None,
                    "tool_calls": [t.model_dump() for t in (msg.choices[0].message.tool_calls or [])] if hasattr(msg, "choices") and msg.choices else []  # pylint: disable=line-too-long  # noqa: E501
                },
                "finish_reason": msg.choices[0].finish_reason if hasattr(msg, "choices") and msg.choices else "stop"
            }],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            },
            "cost": {
                "interaction_cost": interaction_cost,
                "total_cost": self.total_cost
            },
            "timing": {
                "active_seconds": active_time_seconds,
                "idle_seconds": idle_time_seconds
            },
            "timestamp_iso": datetime.now().astimezone(
                pytz.timezone("Europe/Madrid")).isoformat()
        }

        # Append both request and completion to the instance's jsonl file
        with open(self.filename, 'a', encoding='utf-8') as f:
            json.dump(request_data, f)
            f.write('\n')
            json.dump(completion_data, f)
            f.write('\n')

    def log_user_message(self, user_message):
        """
        Logs a user message to the JSONL file.
        
        Args:
            user_message: The message from the user to log
        """
        with open(self.filename, 'a', encoding='utf-8') as f:
            user_data = {
                "event": "user_message",
                "timestamp": datetime.now().astimezone(
                    pytz.timezone("Europe/Madrid")).isoformat(),
                "content": user_message
            }
            json.dump(user_data, f)
            f.write('\n')
    
    def log_assistant_message(self, assistant_message, tool_calls=None):
        """
        Logs an assistant message to the JSONL file.
        
        Args:
            assistant_message: The message from the assistant to log
            tool_calls: Optional tool calls included in the assistant message
        """
        # Store the last message in case we need to log it at exit
        self.last_assistant_message = assistant_message
        self.last_assistant_tool_calls = tool_calls
        
        with open(self.filename, 'a', encoding='utf-8') as f:
            assistant_data = {
                "event": "assistant_message",
                "timestamp": datetime.now().astimezone(
                    pytz.timezone("Europe/Madrid")).isoformat(),
                "content": assistant_message
            }
            if tool_calls:
                assistant_data["tool_calls"] = tool_calls
            json.dump(assistant_data, f)
            f.write('\n')
            
        # Mark that the message has been logged
        self._last_message_logged = True
    
    def log_session_end(self):
        """
        Logs the end of the session to the JSONL file.
        Includes timing metrics from active/idle time tracking.
        """
        # Set a flag to indicate we've already logged the session end
        self._session_end_logged = True
        
        try:
            from cai.util import get_active_time_seconds, get_idle_time_seconds, COST_TRACKER
            active_time = get_active_time_seconds()
            idle_time = get_idle_time_seconds()
            # Get the global session cost from COST_TRACKER
            session_cost = COST_TRACKER.session_total_cost
        except ImportError:
            active_time = 0.0
            idle_time = 0.0
            session_cost = self.total_cost
            
        with open(self.filename, 'a', encoding='utf-8') as f:
            session_end = {
                "event": "session_end",
                "timestamp": datetime.now().astimezone(
                    pytz.timezone("Europe/Madrid")).isoformat(),
                "session_id": self.session_id,
                "timing_metrics": {
                    "active_time_seconds": active_time,
                    "idle_time_seconds": idle_time,
                    "total_time_seconds": active_time + idle_time,
                    "active_percentage": round((active_time / (active_time + idle_time)) * 100, 2) if (active_time + idle_time) > 0 else 0.0
                },
                "cost": {
                    "total_cost": session_cost  # Use the global session cost
                }
            }
            json.dump(session_end, f)
            f.write('\n')

def load_history_from_jsonl(file_path: str, system_prompt: bool = False) -> List[Dict]:
    """
    Load conversation history from JSONL using only model and completion records.    
    
    This implementation ignores event records to avoid confusion and ensures
    we get the complete conversation history as it was sent to and received from
    the models.
    
    Args:
        file_path: Path to the JSONL file
        system_prompt: Whether to include system prompts
        
    Returns:
        List of message dictionaries in conversation order
    """
    records = []
    
    # Load all records
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except Exception as e:
                    print(f"Error loading line: {e}")
                    continue
    
    # Simple approach: collect all messages and system prompts, then deduplicate
    messages = []
    system_prompts_by_agent = {}
    tool_outputs = {}
    
    i = 0
    while i < len(records):
        record = records[i]
        
        # Skip event records
        if "event" in record:
            i += 1
            continue
        
        # Process model record
        if "model" in record and "messages" in record:
            model_messages = record["messages"]
            
            # Get agent name from next completion record (Format 1) or infer from system message (Format 2)
            agent_name = None
            if i + 1 < len(records) and records[i + 1].get("agent_name"):
                agent_name = records[i + 1]["agent_name"]
            elif i + 1 < len(records):
                agent_name = "Agent"  # Default agent name
            
            # Process messages
            for msg in model_messages:
                role = msg.get("role")
                
                if role == "system" and system_prompt and agent_name:
                    # Store system prompt for this agent
                    system_prompts_by_agent[agent_name] = msg.get("content", "")
                elif role == "tool":
                    # Store tool output
                    tool_id = msg.get("tool_call_id")
                    if tool_id:
                        tool_outputs[tool_id] = msg.get("content", "")
                else:
                    # Regular message (user or assistant)
                    messages.append(msg)
            
            # Process completion record if it exists (only if model record doesn't have assistant message)
            if i + 1 < len(records) and "choices" in records[i + 1]:
                next_record = records[i + 1]
                choice = next_record["choices"][0]
                if "message" in choice:
                    response_msg = choice["message"].copy()
                    # Handle both Format 1 (with agent_name) and Format 2 (without agent_name)
                    if next_record.get("agent_name") and response_msg.get("role") == "assistant":
                        response_msg["agent_name"] = next_record["agent_name"]
                    elif response_msg.get("role") == "assistant" and agent_name:
                        # For Format 2, use the inferred agent name
                        response_msg["agent_name"] = agent_name
                    
                    # Only add if this exact assistant message is not already in model record
                    is_duplicate = any(
                        msg.get("role") == "assistant" and
                        msg.get("content") == response_msg.get("content") and
                        str(msg.get("tool_calls", [])) == str(response_msg.get("tool_calls", []))
                        for msg in model_messages
                    )
                    if not is_duplicate:
                        messages.append(response_msg)
                i += 1  # Skip the completion record
        
        i += 1
    
    # Simple deduplication: remove exact duplicates but preserve user messages that trigger different agents
    unique_messages = []
    
    for i, msg in enumerate(messages):
        is_duplicate = False
        
        # For user messages, check if there's a subsequent assistant message with a different agent
        if msg.get("role") == "user":
            # Look ahead to see which agent responds to this user message
            responding_agent = None
            for j in range(i + 1, len(messages)):
                if messages[j].get("role") == "assistant" and messages[j].get("agent_name"):
                    responding_agent = messages[j].get("agent_name")
                    break
            
            # Check if we already have this user message with the same responding agent
            for existing_msg in unique_messages:
                if (existing_msg.get("role") == "user" and 
                    existing_msg.get("content") == msg.get("content")):
                    # Find the agent that responded to the existing message
                    existing_responding_agent = None
                    existing_idx = unique_messages.index(existing_msg)
                    for k in range(existing_idx + 1, len(unique_messages)):
                        if (unique_messages[k].get("role") == "assistant" and 
                            unique_messages[k].get("agent_name")):
                            existing_responding_agent = unique_messages[k].get("agent_name")
                            break
                    
                    # Only consider it a duplicate if same content AND same responding agent
                    if responding_agent == existing_responding_agent:
                        is_duplicate = True
                        break
        else:
            # For non-user messages, use the original logic
            for existing_msg in unique_messages:
                if (existing_msg.get("role") == msg.get("role") and 
                    existing_msg.get("content") == msg.get("content") and
                    existing_msg.get("tool_call_id") == msg.get("tool_call_id") and
                    str(existing_msg.get("tool_calls", [])) == str(msg.get("tool_calls", [])) and
                    existing_msg.get("agent_name") == msg.get("agent_name")):
                    is_duplicate = True
                    break
        
        if not is_duplicate:
            unique_messages.append(msg)
    
    messages = unique_messages
    
    # Now insert system prompts and tool outputs
    final_messages = []
    last_agent = None
    
    for i, msg in enumerate(messages):
        role = msg.get("role")
        
        # Insert system prompt before user message if agent changes
        if system_prompt and role == "user":
            # Look ahead to find responding agent
            next_agent = None
            for j in range(i + 1, len(messages)):
                if messages[j].get("role") == "assistant" and messages[j].get("agent_name"):
                    next_agent = messages[j]["agent_name"]
                    break
            
            # Insert system prompt if agent changes
            if next_agent and next_agent != last_agent and next_agent in system_prompts_by_agent:
                system_msg = {
                    "role": "system",
                    "content": system_prompts_by_agent[next_agent],
                    "agent_name": next_agent
                }
                final_messages.append(system_msg)
                last_agent = next_agent
        
        final_messages.append(msg)
        
        # Update last agent
        if msg.get("agent_name"):
            last_agent = msg["agent_name"]
        
        # Add tool outputs
        if role == "assistant" and msg.get("tool_calls"):
            for tool_call in msg["tool_calls"]:
                tool_id = tool_call.get("id")
                if tool_id and tool_id in tool_outputs:
                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": tool_outputs[tool_id]
                    }
                    final_messages.append(tool_msg)
    
    return final_messages

def get_token_stats(file_path):
    """
    Get token usage statistics from a JSONL file.

    Args:
        file_path (str): Path to the JSONL file

    Returns:
        tuple: (model_name, total_prompt_tokens, total_completion_tokens,
                total_cost, active_time, idle_time)
    """
    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_cost = 0.0
    model_name = None
    last_total_cost = 0.0
    last_active_time = 0.0
    last_idle_time = 0.0

    with open(file_path, encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if "usage" in record:
                    total_prompt_tokens += record["usage"]["prompt_tokens"]
                    total_completion_tokens += (
                        record["usage"]["completion_tokens"]
                    )
                if "cost" in record:
                    if isinstance(record["cost"], dict):
                        # Si cost es un diccionario, obtener total_cost
                        last_total_cost = record["cost"].get("total_cost", 0.0)
                    else:
                        # Si cost es un valor directo
                        last_total_cost = float(record["cost"])
                if "timing_metrics" in record:
                    if isinstance(record["timing_metrics"], dict):
                        last_active_time = record["timing_metrics"].get(
                            "active_time_seconds", 0.0)
                        last_idle_time = record["timing_metrics"].get(
                            "idle_time_seconds", 0.0)
                if "model" in record:
                    model_name = record["model"]
                # Keep track of the last record for session_end event
                if record.get("event") == "session_end":
                    if "timing_metrics" in record and isinstance(record["timing_metrics"], dict):
                        last_active_time = record["timing_metrics"].get(
                            "active_time_seconds", 0.0)
                        last_idle_time = record["timing_metrics"].get(
                            "idle_time_seconds", 0.0)
                    if "cost" in record and isinstance(record["cost"], dict):
                        last_total_cost = record["cost"].get("total_cost", 0.0)
            except Exception as e:  # pylint: disable=broad-except
                print(f"Error loading line: {line}: {e}")
                continue

    # Usar el último total_cost encontrado como el total
    total_cost = last_total_cost

    return (model_name, total_prompt_tokens, total_completion_tokens,
            total_cost, last_active_time, last_idle_time)

def atexit_handler():
    """
    Ensure session_end is logged when the program exits.
    Only logs if a session recorder exists and session_end hasn't already been logged.
    """
    global _session_recorder
    if _session_recorder is None:
        return
    
    # Check if we have an unlogged assistant message and log it
    if hasattr(_session_recorder, 'last_assistant_message') and not getattr(_session_recorder, '_last_message_logged', False):
        if _session_recorder.last_assistant_message or _session_recorder.last_assistant_tool_calls:
            _session_recorder.log_assistant_message(
                _session_recorder.last_assistant_message,
                _session_recorder.last_assistant_tool_calls
            )
    
    # Check if we've already logged the session end (via KeyboardInterrupt)
    if getattr(_session_recorder, '_session_end_logged', False):
        return
    
    # Log the session end
    _session_recorder.log_session_end()

# Register the exit handler
atexit.register(atexit_handler)