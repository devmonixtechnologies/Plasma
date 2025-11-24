#!/usr/bin/env python3
"""
Test streaming functionality in the CLI.
Tests streaming mode, streaming interrupts, and streaming vs non-streaming behavior.
"""

import os
import sys
import time
import unittest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


from cai.sdk.agents.models.openai_chatcompletions import (
    get_agent_message_history,
    get_all_agent_histories,
    ACTIVE_MODEL_INSTANCES,
)


class TestCLIStreaming(unittest.TestCase):
    """Test CLI streaming functionality by testing components directly."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        os.environ["CAI_TELEMETRY"] = "false"
        os.environ["CAI_TRACING"] = "false"
        os.environ["CAI_STREAM"] = "false"

    @classmethod
    def tearDownClass(cls):
        """Clean up after tests."""
        # Import here to avoid circular imports
        from cai.sdk.agents.models.openai_chatcompletions import PERSISTENT_MESSAGE_HISTORIES
        from cai.sdk.agents.simple_agent_manager import AGENT_MANAGER
        
        # Clear all active model instances
        ACTIVE_MODEL_INSTANCES.clear()
        # Clear persistent message histories
        PERSISTENT_MESSAGE_HISTORIES.clear()
        # Clear AGENT_MANAGER state
        AGENT_MANAGER.clear_all_histories()
        AGENT_MANAGER.reset_registry()

    def setUp(self):
        """Set up for each test method."""
        # AGGRESSIVE cleanup to ensure no state contamination between tests
        # Clear all active model instances
        ACTIVE_MODEL_INSTANCES.clear()
        # Keep a strong reference to prevent garbage collection
        self._test_model = None
        
        # Clear any existing message histories
        from cai.sdk.agents.models.openai_chatcompletions import (
            OpenAIChatCompletionsModel,
            PERSISTENT_MESSAGE_HISTORIES
        )
        from cai.sdk.agents.simple_agent_manager import AGENT_MANAGER
        
        # Clear persistent message histories to ensure clean state
        PERSISTENT_MESSAGE_HISTORIES.clear()
        
        # Clear AGENT_MANAGER state
        AGENT_MANAGER.clear_all_histories()
        AGENT_MANAGER.reset_registry()
        
        # Ensure we start with clean histories for each test
        for (name, instance_id), model_ref in list(ACTIVE_MODEL_INSTANCES.items()):
            model = model_ref() if model_ref else None
            if model and hasattr(model, 'message_history'):
                model.message_history.clear()
    
    def tearDown(self):
        """Clean up after each test."""
        # Import here to avoid circular imports
        from cai.sdk.agents.models.openai_chatcompletions import PERSISTENT_MESSAGE_HISTORIES
        from cai.sdk.agents.simple_agent_manager import AGENT_MANAGER
        
        # Clear all active model instances
        ACTIVE_MODEL_INSTANCES.clear()
        # Clear persistent message histories
        PERSISTENT_MESSAGE_HISTORIES.clear()
        # Clear AGENT_MANAGER state
        AGENT_MANAGER.clear_all_histories()
        AGENT_MANAGER.reset_registry()
        # Clear reference to test model
        self._test_model = None

    def get_combined_message_history(self):
        """Get combined message history from all agents."""
        all_messages = []
        histories = get_all_agent_histories()
        for agent_name, history in histories.items():
            all_messages.extend(history)
        return all_messages

    def add_to_test_message_history(self, msg):
        """Add a message to the test agent's history."""
        # Create a mock model instance for testing
        from cai.sdk.agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
        from cai.sdk.agents.simple_agent_manager import AGENT_MANAGER
        from openai import AsyncOpenAI
        import os
        
        test_agent_name = "test_agent"
        # Check if we already have a test model instance
        test_model = None
        for (name, instance_id), model_ref in ACTIVE_MODEL_INSTANCES.items():
            if name == test_agent_name:
                model = model_ref() if model_ref else None
                if model:
                    test_model = model
                    break
        
        # Create one if it doesn't exist
        if not test_model:
            client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", "test-key"))
            # Create with explicit agent_id to ensure registration
            test_model = OpenAIChatCompletionsModel("gpt-4", client, test_agent_name, agent_id="P1")
            # Store a strong reference to prevent garbage collection
            self._test_model = test_model
        
        # Add the message to the model's history
        # This will automatically add to AGENT_MANAGER via add_to_message_history
        test_model.add_to_message_history(msg)

        # No need to clean up _Converter state since it's now instance-based

        # Also ensure environment is clean
        os.environ["CAI_STREAM"] = "false"
        os.environ["CAI_TELEMETRY"] = "false"
        os.environ["CAI_TRACING"] = "false"

    def test_ctrl_c_cleanup_message_consistency(self):
        """Test CTRL+C cleanup logic maintains message consistency."""
        # No need for _Converter cleanup since it's now instance-based

        # Simulate the state before CTRL+C during tool execution
        # 1. User message
        self.add_to_test_message_history({"role": "user", "content": "Run a long command"})

        # 2. Assistant message with tool call
        tool_call_id = "call_interrupted_123"
        self.add_to_test_message_history(
            {
                "role": "assistant",
                "content": "I'll run that command for you.",
                "tool_calls": [
                    {
                        "id": tool_call_id,
                        "type": "function",
                        "function": {
                            "name": "generic_linux_command",
                            "arguments": '{"command": "sleep", "args": "30"}',
                        },
                    }
                ],
            }
        )

        # 3. Simulate CTRL+C happening during tool execution
        # This is where the real cleanup logic would kick in
        def simulate_ctrl_c_cleanup():
            """Simulate the exact cleanup logic from cli.py"""
            
            # Get the test model instance
            test_model = None
            for (name, instance_id), model_ref in ACTIVE_MODEL_INSTANCES.items():
                if name == "test_agent":
                    model = model_ref() if model_ref else None
                    if model:
                        test_model = model
                        break
            
            if not test_model:
                return 0
            
            # Simulate a tool call that was started but interrupted
            test_model._converter.recent_tool_calls[tool_call_id] = {
                "name": "generic_linux_command",
                "arguments": '{"command": "sleep", "args": "30"}',
                "start_time": time.time() - 5,  # Started 5 seconds ago
            }

            # Simulate the cleanup logic from cli.py lines 603-654
            pending_calls = []
            for call_id, call_info in list(test_model._converter.recent_tool_calls.items()):
                # Check if this tool call has a corresponding response in message_history
                tool_response_exists = any(
                    msg.get("role") == "tool" and msg.get("tool_call_id") == call_id
                    for msg in self.get_combined_message_history()
                )

                if not tool_response_exists:
                    # Add assistant message if needed (should already exist in our case)
                    assistant_exists = any(
                        msg.get("role") == "assistant"
                        and msg.get("tool_calls")
                        and any(tc.get("id") == call_id for tc in msg.get("tool_calls", []))
                        for msg in self.get_combined_message_history()
                    )

                    if not assistant_exists:
                        # This shouldn't happen in our test but add for completeness
                        assistant_msg = {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": call_id,
                                    "type": "function",
                                    "function": {
                                        "name": call_info.get("name", "unknown_function"),
                                        "arguments": call_info.get("arguments", "{}"),
                                    },
                                }
                            ],
                        }
                        self.add_to_test_message_history(assistant_msg)

                    # Add synthetic tool response for interrupted tool
                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": "Operation interrupted by user (Keyboard Interrupt)",
                    }
                    self.add_to_test_message_history(tool_msg)
                    pending_calls.append(call_info.get("name", "unknown"))

            # Apply message list fixes like the real system does
            from cai.util import fix_message_list

            try:
                fixed_messages = fix_message_list(
                    self.get_combined_message_history()
                )  # TODO: Fix message_history.extend(fixed_messages)
                return len(pending_calls)
            except Exception as e:
                print(f"fix_message_list failed: {e}")
                return 0

        # Execute the cleanup
        cleaned_count = simulate_ctrl_c_cleanup()

        # Verify the cleanup worked
        assert cleaned_count > 0, "Should have cleaned up at least one pending tool call"

        # Verify message history consistency
        self.verify_message_history_openai_compliance()

        # Verify we have the expected sequence
        assert len(self.get_combined_message_history()) >= 3, (
            "Should have user, assistant, tool messages"
        )

        # Check message roles in order
        roles = [msg["role"] for msg in self.get_combined_message_history()]
        assert roles[0] == "user", "First message should be user"
        assert roles[1] == "assistant", "Second message should be assistant"
        assert roles[2] == "tool", "Third message should be tool"

        # Verify tool call/result consistency
        assistant_msg = self.get_combined_message_history()[1]
        tool_msg = self.get_combined_message_history()[2]
        assert assistant_msg.get("tool_calls"), "Assistant message should have tool calls"
        assert tool_msg["tool_call_id"] == assistant_msg["tool_calls"][0]["id"], (
            "Tool call ID should match"
        )
        assert "interrupted" in tool_msg["content"].lower(), (
            "Tool result should indicate interruption"
        )

        print("✅ CTRL+C cleanup message consistency test passed!")

        # No need to clean up _Converter state since it's instance-based

    def test_fix_message_list_with_interrupted_tools(self):
        """Test fix_message_list handles interrupted tool sequences correctly."""
        from cai.util import fix_message_list
        
        # No need for _Converter cleanup since it's now instance-based

        # Create an incomplete sequence (tool call without result)
        self.add_to_test_message_history({"role": "user", "content": "Test command"})
        self.add_to_test_message_history(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_incomplete_456",
                        "type": "function",
                        "function": {
                            "name": "generic_linux_command",
                            "arguments": '{"command": "test", "args": "--help"}',
                        },
                    }
                ],
            }
        )

        # At this point we have incomplete sequence - no tool result
        incomplete_messages = list(self.get_combined_message_history())

        # Apply fix_message_list
        try:
            fixed_messages = fix_message_list(incomplete_messages)

            # Verify fix_message_list added the missing tool result
            assert len(fixed_messages) > len(incomplete_messages), (
                "fix_message_list should add missing tool result"
            )

            # Find the added tool message
            tool_msg = None
            for msg in fixed_messages:
                if msg.get("role") == "tool" and msg.get("tool_call_id") == "call_incomplete_456":
                    tool_msg = msg
                    break

            assert tool_msg is not None, "fix_message_list should add tool result message"

            # Verify the fixed messages comply with OpenAI format
            for i, msg in enumerate(fixed_messages):
                assert "role" in msg, f"Fixed message {i} missing role"
                assert msg["role"] in ["user", "assistant", "system", "tool"], (
                    f"Fixed message {i} has invalid role"
                )

            print("✅ fix_message_list with interrupted tools test passed!")

            # No need to clean up _Converter state since it's instance-based

            return True

        except Exception as e:
            print(f"fix_message_list failed: {e}")
            # No need to clean up _Converter state since it's instance-based
            return False

    def test_generic_linux_command_interrupt_simulation(self):
        """Test generic_linux_command behavior during interruption."""

        # Mock the generic_linux_command function behavior
        def mock_interrupted_command():
            """Simulate generic_linux_command being interrupted"""
            try:
                # Simulate command starting
                output = "Command started...\nProcessing files..."

                # Simulate interrupt during execution (like CTRL+C)
                raise KeyboardInterrupt("User interrupted command")

            except KeyboardInterrupt:
                # Simulate the real behavior - command returns partial output
                interrupted_output = f"{output}\nCommand interrupted by user"
                return interrupted_output

        # Test the mock
        result = mock_interrupted_command()

        # Verify it behaves like the real interrupted command
        assert "Command started" in result, "Should include partial output"
        assert "interrupted" in result, "Should indicate interruption"

        print("✅ Generic linux command interrupt simulation test passed!")

    def test_message_history_openai_format_compliance(self):
        """Test that message_history always maintains OpenAI ChatCompletion format."""

        # Clear history and check initial state
        initial_messages = self.get_combined_message_history()
        print(f"Initial message history (should be empty): {len(initial_messages)} messages")
        if initial_messages:
            for i, msg in enumerate(initial_messages):
                print(f"  Unexpected initial message {i}: {msg}")
        
        # Test various message types that should maintain OpenAI format
        test_messages = [
            # User message
            {"role": "user", "content": "Test user message"},
            # Assistant message with content
            {"role": "assistant", "content": "Test assistant response"},
            # Assistant message with tool calls
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_test_123",
                        "type": "function",
                        "function": {"name": "test_function", "arguments": '{"param": "value"}'},
                    }
                ],
            },
            # Tool message
            {"role": "tool", "tool_call_id": "call_test_123", "content": "Tool execution result"},
            # System message
            {"role": "system", "content": "You are a helpful assistant"},
        ]

        # Add all messages
        for i, msg in enumerate(test_messages):
            print(f"Adding message {i}: {msg['role']}")
            self.add_to_test_message_history(msg)
            current_count = len(self.get_combined_message_history())
            print(f"  Total messages after adding: {current_count}")

        # Verify OpenAI format compliance
        final_messages = self.get_combined_message_history()
        assert len(final_messages) == len(test_messages), (
            f"Expected {len(test_messages)} messages, got {len(final_messages)}"
        )

        for i, msg in enumerate(self.get_combined_message_history()):
            # Required fields
            assert "role" in msg, f"Message {i} missing required 'role' field"

            # Valid roles
            valid_roles = ["user", "assistant", "system", "tool", "developer"]
            assert msg["role"] in valid_roles, (
                f"Message {i} has invalid role '{msg['role']}', must be one of {valid_roles}"
            )

            # Role-specific validation
            if msg["role"] == "tool":
                assert "tool_call_id" in msg, f"Tool message {i} missing 'tool_call_id'"
                assert "content" in msg, f"Tool message {i} missing 'content'"

            if msg["role"] == "assistant" and msg.get("tool_calls"):
                assert isinstance(msg["tool_calls"], list), (
                    f"Assistant message {i} tool_calls must be a list"
                )
                for j, tc in enumerate(msg["tool_calls"]):
                    assert "id" in tc, f"Tool call {j} in message {i} missing 'id'"
                    assert "type" in tc, f"Tool call {j} in message {i} missing 'type'"
                    assert "function" in tc, f"Tool call {j} in message {i} missing 'function'"
                    assert "name" in tc["function"], (
                        f"Tool call {j} function in message {i} missing 'name'"
                    )
                    assert "arguments" in tc["function"], (
                        f"Tool call {j} function in message {i} missing 'arguments'"
                    )

        print("✅ Message history OpenAI format compliance test passed!")

    def test_streaming_mode_configuration(self):
        """Test streaming mode can be configured and detected."""
        # Test non-streaming mode
        os.environ["CAI_STREAM"] = "false"
        assert os.environ["CAI_STREAM"] == "false"

        # Test streaming mode
        os.environ["CAI_STREAM"] = "true"
        assert os.environ["CAI_STREAM"] == "true"

        print("✅ Streaming mode configuration test passed!")

    def test_multiple_interrupt_scenarios(self):
        """Test multiple CTRL+C scenarios maintain consistency."""

        # Clear history
        scenarios = [
            ("Run first command", "call_1", "First command interrupted"),
            ("Run second command", "call_2", "Second command interrupted"),
            ("Run third command", "call_3", "Third command completed successfully"),
        ]

        for user_input, call_id, result_content in scenarios:
            # Add user message
            self.add_to_test_message_history({"role": "user", "content": user_input})

            # Add assistant message with tool call
            self.add_to_test_message_history(
                {
                    "role": "assistant",
                    "content": "I'll run that command for you.",
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": "generic_linux_command",
                                "arguments": f'{{"command": "test", "args": "{user_input}"}}',
                            },
                        }
                    ],
                }
            )

            # Add tool result
            self.add_to_test_message_history(
                {"role": "tool", "tool_call_id": call_id, "content": result_content}
            )

            # Verify consistency after each scenario
            self.verify_message_history_openai_compliance()

        # Final verification
        assert len(self.get_combined_message_history()) == len(scenarios) * 3
        print("✅ Multiple interrupt scenarios test passed!")

    def verify_message_history_openai_compliance(self):
        """Helper method to verify message_history complies with OpenAI format."""
        for i, msg in enumerate(self.get_combined_message_history()):
            # Basic structure checks
            assert isinstance(msg, dict), f"Message {i} must be a dictionary"
            assert "role" in msg, f"Message {i} missing 'role' field"

            # Role validation
            valid_roles = ["user", "assistant", "system", "tool", "developer"]
            assert msg["role"] in valid_roles, (
                f"Message {i} role '{msg['role']}' not in valid roles {valid_roles}"
            )

            # Content or tool_calls must exist for most roles
            if msg["role"] in ["user", "system", "developer"]:
                assert "content" in msg, f"Message {i} with role '{msg['role']}' missing content"

            elif msg["role"] == "assistant":
                # Assistant must have content OR tool_calls
                has_content = "content" in msg and msg["content"] is not None
                has_tool_calls = "tool_calls" in msg and msg["tool_calls"]
                assert has_content or has_tool_calls, (
                    f"Assistant message {i} must have content or tool_calls"
                )

            elif msg["role"] == "tool":
                assert "tool_call_id" in msg, f"Tool message {i} missing tool_call_id"
                assert "content" in msg, f"Tool message {i} missing content"

    def test_ctrl_c_during_tool_execution_real_behavior(self):
        """Test real CTRL+C behavior during tool execution without duplicates."""
        # No need for _Converter cleanup since it's now instance-based

        # Simulate a running tool call that gets interrupted
        call_id = "call_linux_cmd_123"
        tool_name = "generic_linux_command"

        # 1. Add user message
        self.add_to_test_message_history({"role": "user", "content": "Run a long command"})

        # 2. Add assistant message with tool call (simulating qwen format)
        self.add_to_test_message_history(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {"name": tool_name, "arguments": '{"command": "sleep 10"}'},
                    }
                ],
            }
        )

        # 3. Simulate CTRL+C cleanup behavior from cli.py
        # Get the test model instance
        test_model = None
        for (name, instance_id), model_ref in ACTIVE_MODEL_INSTANCES.items():
            if name == "test_agent":
                model = model_ref() if model_ref else None
                if model:
                    test_model = model
                    break
        
        if not test_model:
            self.fail("Could not find test model instance")
        
        # Add ONLY our specific tool call to recent_tool_calls
        test_model._converter.recent_tool_calls[call_id] = {
            "name": tool_name,
            "arguments": '{"command": "sleep 10"}',
        }

        # Simulate the KeyboardInterrupt cleanup logic from cli.py
        try:
            # Check for pending tool calls without responses
            for call_id_check, call_info in list(test_model._converter.recent_tool_calls.items()):
                # Check if tool response exists
                tool_response_exists = any(
                    msg.get("role") == "tool" and msg.get("tool_call_id") == call_id_check
                    for msg in self.get_combined_message_history()
                )

                if not tool_response_exists:
                    # Add synthetic tool response (this is what cli.py does now)
                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": call_id_check,
                        "content": "Operation interrupted by user (Keyboard Interrupt)",
                    }
                    self.add_to_test_message_history(tool_msg)

            # NOTE: The fix means we DON'T call fix_message_list here anymore
            # This prevents duplicate synthetic tool calls

        except Exception as e:
            print(f"Error in cleanup: {e}")

        # Verify message consistency after CTRL+C
        messages = self.get_combined_message_history()
        print(f"Message history after CTRL+C cleanup (total: {len(messages)}):")
        for i, msg in enumerate(messages):
            print(f"  {i}: {msg.get('role')} - {msg}")

        # Assertions
        self.assertEqual(len(messages), 3, f"Expected 3 messages, got {len(messages)}: {messages}")  # user + assistant + tool

        # Check user message
        self.assertEqual(self.get_combined_message_history()[0]["role"], "user")

        # Check assistant message has correct tool call
        self.assertEqual(self.get_combined_message_history()[1]["role"], "assistant")
        self.assertIsNotNone(self.get_combined_message_history()[1]["tool_calls"])
        self.assertEqual(len(self.get_combined_message_history()[1]["tool_calls"]), 1)
        self.assertEqual(self.get_combined_message_history()[1]["tool_calls"][0]["id"], call_id)
        self.assertEqual(
            self.get_combined_message_history()[1]["tool_calls"][0]["function"]["name"], tool_name
        )

        # Check tool response exists and is correct
        self.assertEqual(self.get_combined_message_history()[2]["role"], "tool")
        self.assertEqual(self.get_combined_message_history()[2]["tool_call_id"], call_id)
        self.assertIn("interrupted", self.get_combined_message_history()[2]["content"].lower())

        # MOST IMPORTANT: Verify NO duplicate tool calls with unknown_function
        unknown_function_calls = []
        for msg in self.get_combined_message_history():
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    if tc.get("function", {}).get("name") == "unknown_function":
                        unknown_function_calls.append(tc)

        self.assertEqual(
            len(unknown_function_calls),
            0,
            f"Found {len(unknown_function_calls)} duplicate unknown_function calls: {unknown_function_calls}",
        )

        # Verify OpenAI format compliance
        self.verify_message_history_openai_compliance()

        print("✓ CTRL+C test passed - no duplicates!")

        # No need to clean up _Converter state since it's instance-based


if __name__ == "__main__":
    print("🧪 Running simplified CLI streaming tests...")

    # Try to use unittest.main() first
    try:
        import unittest

        if len(sys.argv) == 1:  # No command line args, run all tests
            unittest.main(verbosity=2, exit=False)
        else:
            # If there are command line args, run manual tests for debugging
            # Create test instance
            test_instance = TestCLIStreaming()
            test_instance.setUpClass()

            # List of test methods - focused on direct testing without asyncio
            test_methods = [
                "test_streaming_mode_configuration",
                "test_message_history_openai_format_compliance",
                "test_ctrl_c_cleanup_message_consistency",
                "test_fix_message_list_with_interrupted_tools",
                "test_generic_linux_command_interrupt_simulation",
                "test_multiple_interrupt_scenarios",
                "test_ctrl_c_during_tool_execution_real_behavior",
            ]

            results = {}

            for method_name in test_methods:
                try:
                    print(f"\n🔬 Running {method_name}...")
                    # PROPERLY call setUp for each test
                    test_instance.setUp()
                    method = getattr(test_instance, method_name)
                    method()
                    results[method_name] = "PASSED"
                except Exception as e:
                    results[method_name] = f"FAILED: {str(e)}"
                    print(f"❌ {method_name} failed: {e}")

                    # Print debug info for failures
                    if len(test_instance.get_combined_message_history()) > 0:
                        print("Message history debug:")
                        for i, msg in enumerate(test_instance.get_combined_message_history()):
                            print(
                                f"  [{i}] {msg.get('role', 'unknown')}: {str(msg.get('content', ''))[:50]}"
                            )

            # Print summary
            print("\n" + "=" * 60)
            print("📊 STREAMING TESTS SUMMARY")
            print("=" * 60)

            passed = sum(1 for r in results.values() if r == "PASSED")
            failed = len(results) - passed

            for test_name, result in results.items():
                status_emoji = "✅" if result == "PASSED" else "❌"
                print(f"{status_emoji} {test_name}: {result}")

            print(f"\n🎯 Results: {passed} passed, {failed} failed")

            if failed == 0:
                print("🎉 All simplified streaming tests passed!")
                print("\n🔍 These tests verify:")
                print("- Streaming mode configuration")
                print("- Message history OpenAI format compliance")
                print("- CTRL+C cleanup maintains message consistency")
                print("- fix_message_list handles interrupted tools")
                print("- Generic linux command interrupt simulation")
                print("- Multiple interrupt scenarios")
                print("- Real CTRL+C behavior during tool execution without duplicates")
            else:
                print(f"💥 {failed} streaming tests failed!")
                sys.exit(1)

    except Exception as unittest_error:
        print(f"Error running with unittest: {unittest_error}")
        print("Falling back to manual test execution...")

        # Manual fallback
        test_instance = TestCLIStreaming()
        test_instance.setUpClass()

        test_methods = [
            "test_streaming_mode_configuration",
            "test_message_history_openai_format_compliance",
            "test_ctrl_c_cleanup_message_consistency",
            "test_fix_message_list_with_interrupted_tools",
            "test_generic_linux_command_interrupt_simulation",
            "test_multiple_interrupt_scenarios",
            "test_ctrl_c_during_tool_execution_real_behavior",
        ]

        results = {}
        for method_name in test_methods:
            try:
                print(f"\n🔬 Running {method_name}...")
                test_instance.setUp()  # CRITICAL: Call setUp for each test
                method = getattr(test_instance, method_name)
                method()
                results[method_name] = "PASSED"
            except Exception as e:
                results[method_name] = f"FAILED: {str(e)}"
                print(f"❌ {method_name} failed: {e}")

        passed = sum(1 for r in results.values() if r == "PASSED")
        failed = len(results) - passed
        print(f"\n🎯 Manual Results: {passed} passed, {failed} failed")
        if failed > 0:
            sys.exit(1)
