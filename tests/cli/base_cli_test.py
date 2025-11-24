#!/usr/bin/env python3
"""
Base class for CLI testing with comprehensive mocking and utilities.
"""

import os
import sys
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)
from openai.types.completion_usage import CompletionUsage

from cai.sdk.agents import Agent, ModelResponse, OpenAIChatCompletionsModel
from cai.sdk.agents.models.openai_chatcompletions import (
    get_agent_message_history,
    get_all_agent_histories,
    ACTIVE_MODEL_INSTANCES,
)


class CLIMessageSimulator:
    """Simulates message flow in the CLI with proper timing and state management."""

    def __init__(self):
        self.messages = []
        self.current_index = 0
        self.completion_responses = []
        self.tool_call_responses = {}
        self.interrupt_triggers = {}

    def add_user_message(self, content: str, interrupt_after: bool = False):
        """Add a user message to the simulation."""
        self.messages.append(
            {"role": "user", "content": content, "interrupt_after": interrupt_after}
        )

    def add_assistant_response(self, content: str, tool_calls: Optional[List[Dict]] = None):
        """Add an expected assistant response."""
        response_data = {"role": "assistant", "content": content}
        if tool_calls:
            response_data["tool_calls"] = tool_calls

        self.completion_responses.append(response_data)

    def add_tool_response(self, call_id: str, output: str):
        """Add a tool call response."""
        self.tool_call_responses[call_id] = output

    def set_interrupt_trigger(self, message_index: int, during_execution: bool = False):
        """Set when to trigger a KeyboardInterrupt."""
        self.interrupt_triggers[message_index] = {"during_execution": during_execution}

    def get_next_message(self) -> Optional[Dict]:
        """Get the next message in the simulation."""
        if self.current_index < len(self.messages):
            msg = self.messages[self.current_index]
            self.current_index += 1
            return msg
        return None

    def get_completion_response(self, index: int) -> Optional[Dict]:
        """Get the completion response for a given index."""
        if index < len(self.completion_responses):
            return self.completion_responses[index]
        return None

    def should_interrupt(self, index: int, during_execution: bool = False) -> bool:
        """Check if an interrupt should be triggered."""
        trigger = self.interrupt_triggers.get(index)
        if trigger:
            return trigger["during_execution"] == during_execution
        return False

    def reset(self):
        """Reset the simulator state."""
        self.current_index = 0


class BaseCLITest:
    """
    Comprehensive base class for CLI testing with advanced mocking capabilities.

    This class provides:
    - Complete CLI environment mocking
    - Message flow simulation
    - Streaming and non-streaming mode testing
    - Keyboard interrupt simulation at various points
    - Tool call mocking and verification
    - Integration with openai_chatcompletions.py logic
    """

    @classmethod
    def setup_class(cls):
        """Set up test environment."""
        # Disable external services for testing
        os.environ["CAI_TELEMETRY"] = "false"
        os.environ["CAI_TRACING"] = "false"
        os.environ["CAI_STREAM"] = "false"
        os.environ["CAI_MAX_TURNS"] = "5"

        # Ensure we're using a test model
        os.environ["CAI_MODEL"] = "test-model"

        # Disable any CTF components
        os.environ.pop("CTF_NAME", None)

    @classmethod
    def teardown_class(cls):
        """Clean up after tests."""
        # Clear all active model instances
        ACTIVE_MODEL_INSTANCES.clear()

    def setup_method(self):
        """Set up for each test method."""
        # Clear all active model instances
        ACTIVE_MODEL_INSTANCES.clear()
        self.simulator = CLIMessageSimulator()

    def get_combined_message_history(self):
        """Get combined message history from all agents."""
        all_messages = []
        histories = get_all_agent_histories()
        for agent_name, history in histories.items():
            all_messages.extend(history)
        return all_messages

    def create_mock_completion(
        self,
        content: str = "Test response",
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        usage: Optional[Dict[str, int]] = None,
    ) -> ChatCompletion:
        """
        Create a mock ChatCompletion response with proper structure.

        Args:
            content: The assistant's response content
            tool_calls: List of tool calls to include
            usage: Token usage information

        Returns:
            Properly formatted ChatCompletion object
        """
        message_data = {"role": "assistant", "content": content}

        if tool_calls:
            formatted_tool_calls = []
            for tc in tool_calls:
                tool_call = ChatCompletionMessageToolCall(
                    id=tc.get("id", f"call_{int(time.time() * 1000)}"),
                    type="function",
                    function=Function(
                        name=tc.get("function", {}).get("name", "test_function"),
                        arguments=tc.get("function", {}).get("arguments", "{}"),
                    ),
                )
                formatted_tool_calls.append(tool_call)
            message_data["tool_calls"] = formatted_tool_calls

        msg = ChatCompletionMessage(**message_data)
        choice = Choice(index=0, finish_reason="stop", message=msg)

        # Default usage if not provided
        if not usage:
            usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}

        return ChatCompletion(
            id=f"test-completion-{int(time.time() * 1000)}",
            created=int(time.time()),
            model="test-model",
            object="chat.completion",
            choices=[choice],
            usage=CompletionUsage(**usage),
        )

    def create_mock_agent(self, model_name: str = "test-model") -> Agent:
        """Create a mock agent with proper configuration."""
        mock_client = AsyncMock()
        mock_client.base_url = "http://test-url"

        test_model = OpenAIChatCompletionsModel(model=model_name, openai_client=mock_client)

        return Agent(name="TestAgent", instructions="You are a test assistant", model=test_model)

    def create_mock_model_response(
        self, content: str = "Test response", items: Optional[List] = None
    ) -> ModelResponse:
        """Create a mock ModelResponse for Runner.run."""
        from cai.sdk.agents.usage import Usage

        return ModelResponse(
            output=items or [],
            usage=Usage(requests=1, input_tokens=10, output_tokens=20, total_tokens=30),
            referenceable_id=None,
        )

    def create_input_simulator(
        self, messages: List[str], interrupts: Optional[Dict[int, str]] = None
    ):
        """
        Create an input simulator that provides predefined messages and can trigger interrupts.

        Args:
            messages: List of user input messages
            interrupts: Dict mapping message index to interrupt type
                       e.g., {1: "during_input", 2: "during_processing"}

        Returns:
            A function that can be used to mock user input
        """
        message_index = [0]

        def mock_input_function(*args, **kwargs):
            current_index = message_index[0]

            # Check if we should interrupt before providing input
            if interrupts and current_index in interrupts:
                interrupt_type = interrupts[current_index]
                if interrupt_type == "before_input":
                    raise KeyboardInterrupt(f"Simulated interrupt before message {current_index}")

            # Provide the next message if available
            if current_index < len(messages):
                message = messages[current_index]
                message_index[0] += 1

                # Check if we should interrupt after providing input
                if interrupts and current_index in interrupts:
                    interrupt_type = interrupts[current_index]
                    if interrupt_type == "after_input":
                        # Return the message but arrange for interrupt on next call
                        return message

                return message
            else:
                # No more messages, trigger completion interrupt
                raise KeyboardInterrupt("Test completed - no more messages")

        return mock_input_function

    def create_litellm_simulator(
        self, responses: List[ChatCompletion], interrupts: Optional[Dict[int, str]] = None
    ):
        """
        Create a LiteLLM simulator that provides predefined responses and can trigger interrupts.

        Args:
            responses: List of ChatCompletion responses to return
            interrupts: Dict mapping response index to interrupt type

        Returns:
            A function that can be used to mock litellm.completion
        """
        response_index = [0]

        def mock_litellm_function(*args, **kwargs):
            current_index = response_index[0]

            # Check if we should interrupt during processing
            if interrupts and current_index in interrupts:
                interrupt_type = interrupts[current_index]
                if interrupt_type == "during_llm_call":
                    raise KeyboardInterrupt(f"Simulated interrupt during LLM call {current_index}")

            # Return the next response if available
            if current_index < len(responses):
                response = responses[current_index]
                response_index[0] += 1
                return response
            else:
                # Return the last response for any additional calls
                return responses[-1] if responses else self.create_mock_completion()

        return mock_litellm_function

    def run_cli_simulation(
        self,
        agent: Agent,
        user_inputs: List[str],
        expected_responses: List[str],
        stream_mode: bool = False,
        interrupts: Optional[Dict[int, str]] = None,
        tool_calls: Optional[Dict[int, List[Dict]]] = None,
        verify_message_flow: bool = True,
    ) -> Dict[str, Any]:
        """
        Run a complete CLI simulation with full control over inputs, outputs, and interrupts.

        Args:
            agent: The agent to use for testing
            user_inputs: List of user input messages
            expected_responses: List of expected assistant responses
            stream_mode: Whether to test streaming mode
            interrupts: Dict mapping indices to interrupt types
            tool_calls: Dict mapping response indices to tool calls
            verify_message_flow: Whether to verify message history flow

        Returns:
            Dict with simulation results and verification data
        """
        # Set streaming mode
        os.environ["CAI_STREAM"] = "true" if stream_mode else "false"

        # Prepare mock responses
        mock_responses = []
        for i, response_content in enumerate(expected_responses):
            response_tool_calls = tool_calls.get(i) if tool_calls else None
            mock_responses.append(
                self.create_mock_completion(response_content, response_tool_calls)
            )

        # Create simulators
        input_simulator = self.create_input_simulator(user_inputs, interrupts)
        litellm_simulator = self.create_litellm_simulator(mock_responses, interrupts)

        # Track execution results
        results = {
            "user_inputs_processed": [],
            "assistant_responses": [],
            "tool_calls_made": [],
            "tool_outputs": [],
            "interrupts_caught": [],
            "message_history_final": [],
            "llm_calls": [],
            "exceptions": [],
            "stream_events": [] if stream_mode else None,
        }

        # Enhanced mocking for CLI components
        mock_patches = [
            # Core CLI input/output
            patch("cai.repl.ui.prompt.get_user_input", side_effect=input_simulator),
            patch("cai.repl.ui.logging.setup_session_logging", return_value="test_history.txt"),
            # Session recording
            patch("cai.sdk.agents.run_to_jsonl.get_session_recorder"),
            # CLI UI components
            patch("cai.repl.commands.FuzzyCommandCompleter"),
            patch("cai.repl.ui.keybindings.create_key_bindings"),
            patch("cai.repl.ui.banner.display_banner"),
            patch("cai.repl.ui.banner.display_quick_guide"),
            # LLM calls
            patch("litellm.completion", side_effect=litellm_simulator),
            patch("litellm.acompletion", side_effect=litellm_simulator),
            # Timing functions
            patch("cai.util.start_idle_timer"),
            patch("cai.util.stop_idle_timer"),
            patch("cai.util.start_active_timer"),
            patch("cai.util.stop_active_timer"),
            patch("cai.util.get_active_time_seconds", return_value=1.0),
            patch("cai.util.get_idle_time_seconds", return_value=2.0),
            # Rich console output
            patch("rich.console.Console.print"),
        ]

        # Apply all patches and run simulation
        from cai.cli import run_cai_cli

        def apply_patches_and_run():
            with (
                patch.multiple("cai.repl.ui.prompt", get_user_input=input_simulator),
                patch.multiple(
                    "litellm", completion=litellm_simulator, acompletion=litellm_simulator
                ),
                patch.multiple(
                    "cai.repl.ui.logging",
                    setup_session_logging=Mock(return_value="test_history.txt"),
                ),
                patch.multiple(
                    "cai.sdk.agents.run_to_jsonl",
                    get_session_recorder=Mock(
                        return_value=Mock(
                            filename="test_session.jsonl",
                            log_user_message=Mock(),
                            log_assistant_message=Mock(),
                            log_session_end=Mock(),
                            rec_training_data=Mock(),
                        )
                    ),
                ),
                patch.multiple("cai.repl.commands", FuzzyCommandCompleter=Mock()),
                patch.multiple("cai.repl.ui.keybindings", create_key_bindings=Mock()),
                patch.multiple(
                    "cai.repl.ui.banner", display_banner=Mock(), display_quick_guide=Mock()
                ),
                patch.multiple(
                    "cai.util",
                    start_idle_timer=Mock(),
                    stop_idle_timer=Mock(),
                    start_active_timer=Mock(),
                    stop_active_timer=Mock(),
                    get_active_time_seconds=Mock(return_value=1.0),
                    get_idle_time_seconds=Mock(return_value=2.0),
                ),
                patch.multiple("rich.console", Console=Mock()),
            ):
                try:
                    run_cai_cli(
                        starting_agent=agent, max_turns=len(user_inputs), force_until_flag=False
                    )
                except KeyboardInterrupt as e:
                    results["interrupts_caught"].append(str(e))
                except Exception as e:
                    results["exceptions"].append(str(e))

        # Execute the simulation
        apply_patches_and_run()

        # Capture final state
        results["message_history_final"] = list(self.get_combined_message_history())

        # Verify message flow if requested
        if verify_message_flow:
            results["message_flow_valid"] = self._verify_message_flow(
                user_inputs, expected_responses, tool_calls
            )

        return results

    def _verify_message_flow(
        self,
        user_inputs: List[str],
        expected_responses: List[str],
        tool_calls: Optional[Dict[int, List[Dict]]] = None,
    ) -> bool:
        """Verify that the message flow in message_history is correct."""
        try:
            # Check that we have the expected number of messages
            expected_message_count = len(user_inputs) + len(expected_responses)
            if tool_calls:
                # Add tool call messages and tool result messages
                expected_message_count += sum(len(calls) * 2 for calls in tool_calls.values())

            message_history = self.get_combined_message_history()
            if len(message_history) < len(user_inputs):
                return False

            # Verify message sequence
            message_index = 0
            for i in range(len(user_inputs)):
                # Check user message
                if message_index >= len(message_history):
                    return False

                user_msg = message_history[message_index]
                if user_msg.get("role") != "user" or user_inputs[i] not in str(
                    user_msg.get("content", "")
                ):
                    return False

                message_index += 1

                # Check assistant message if we expect one
                if i < len(expected_responses):
                    if message_index >= len(message_history):
                        return False

                    assistant_msg = message_history[message_index]
                    if assistant_msg.get("role") != "assistant":
                        return False

                    message_index += 1

            return True

        except Exception:
            return False

    def assert_message_history_contains(self, role: str, content_substring: str):
        """Assert that message history contains a message with the given role and content."""
        message_history = self.get_combined_message_history()
        for msg in message_history:
            if msg.get("role") == role and content_substring in str(msg.get("content", "")):
                return True
        raise AssertionError(
            f"Message history does not contain {role} message with content '{content_substring}'"
        )

    def assert_tool_call_made(self, function_name: str):
        """Assert that a tool call was made with the given function name."""
        message_history = self.get_combined_message_history()
        for msg in message_history:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tool_call in msg["tool_calls"]:
                    if tool_call.get("function", {}).get("name") == function_name:
                        return True
        raise AssertionError(f"No tool call found for function '{function_name}'")

    def assert_keyboard_interrupt_handled(self, results: Dict[str, Any]):
        """Assert that keyboard interrupts were properly handled."""
        assert len(results["interrupts_caught"]) > 0, "No keyboard interrupts were caught"

    def print_message_history_debug(self):
        """Print the current message history for debugging."""
        print("\n=== MESSAGE HISTORY DEBUG ===")
        message_history = self.get_combined_message_history()
        for i, msg in enumerate(message_history):
            role = msg.get("role", "unknown")
            content = str(msg.get("content", ""))[:100]
            tool_calls = msg.get("tool_calls", [])
            tool_call_id = msg.get("tool_call_id", "")

            print(f"[{i}] {role}: {content}")
            if tool_calls:
                print(f"    Tool calls: {len(tool_calls)}")
            if tool_call_id:
                print(f"    Tool call ID: {tool_call_id}")
        print("=== END MESSAGE HISTORY ===\n")
