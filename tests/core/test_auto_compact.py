"""Test automatic context compaction when limit is reached."""
import os
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from cai.sdk.agents.models.openai_chatcompletions import OpenAIChatCompletionsModel


class TestAutoCompact:
    """Test automatic context compaction functionality."""

    @pytest.mark.asyncio
    async def test_auto_compact_triggers_at_threshold(self):
        """Test that auto-compact triggers when context exceeds threshold."""
        # Set up environment
        os.environ['CAI_AUTO_COMPACT'] = 'true'
        os.environ['CAI_AUTO_COMPACT_THRESHOLD'] = '0.8'  # 80% threshold
        os.environ['CAI_CONTEXT_USAGE'] = '0.0'
        
        # Mock the internal auto_compact method directly
        model = MagicMock(spec=OpenAIChatCompletionsModel)
        model._get_model_max_tokens = MagicMock(return_value=1000)
        
        # Test the _auto_compact_if_needed method
        with patch('cai.sdk.agents.models.openai_chatcompletions.count_tokens_with_tiktoken') as mock_count:
            mock_count.return_value = (850, 0)  # 85% of max
            
            with patch('cai.repl.commands.memory.MEMORY_COMMAND_INSTANCE') as mock_memory:
                mock_memory._ai_summarize_history = AsyncMock(return_value="Summary")
                
                with patch('cai.repl.commands.memory.COMPACTED_SUMMARIES', {}):
                    with patch('rich.console.Console'):
                        # Create actual model instance
                        from openai import AsyncOpenAI
                        client = AsyncMock(spec=AsyncOpenAI)
                        
                        with patch('cai.sdk.agents.models.openai_chatcompletions.get_session_recorder'):
                            model = OpenAIChatCompletionsModel(
                                model="gpt-4",
                                openai_client=client,
                                agent_name="Test Agent",
                                agent_id="TEST123"
                            )
                            
                            # Mock the model's max tokens method
                            with patch.object(model, '_get_model_max_tokens', return_value=1000):
                                # Call the auto-compact method directly
                                input_text = "Test message"
                                new_input, new_instructions, compacted = await model._auto_compact_if_needed(
                                    estimated_tokens=850,
                                    input=input_text,
                                    system_instructions=None
                                )
                            
                                # Verify compaction occurred
                                assert compacted is True
                                assert "Previous conversation summary" in new_instructions
                                mock_memory._ai_summarize_history.assert_called_once_with("Test Agent")

    @pytest.mark.asyncio
    async def test_auto_compact_disabled(self):
        """Test that auto-compact doesn't trigger when disabled."""
        os.environ['CAI_AUTO_COMPACT'] = 'false'
        
        from openai import AsyncOpenAI
        client = AsyncMock(spec=AsyncOpenAI)
        
        with patch('cai.sdk.agents.models.openai_chatcompletions.get_session_recorder'):
            model = OpenAIChatCompletionsModel(
                model="gpt-4",
                openai_client=client,
                agent_name="Test Agent",
                agent_id="TEST123"
            )
            
            # Call the auto-compact method directly
            new_input, new_instructions, compacted = await model._auto_compact_if_needed(
                estimated_tokens=900,  # High token count
                input="Test",
                system_instructions=None
            )
            
            # Verify no compaction occurred
            assert compacted is False
            assert new_input == "Test"
            assert new_instructions is None

    @pytest.mark.asyncio
    async def test_auto_compact_below_threshold(self):
        """Test that auto-compact doesn't trigger below threshold."""
        os.environ['CAI_AUTO_COMPACT'] = 'true'
        os.environ['CAI_AUTO_COMPACT_THRESHOLD'] = '0.8'
        
        from openai import AsyncOpenAI
        client = AsyncMock(spec=AsyncOpenAI)
        
        with patch('cai.sdk.agents.models.openai_chatcompletions.get_session_recorder'):
            model = OpenAIChatCompletionsModel(
                model="gpt-4",
                openai_client=client,
                agent_name="Test Agent",
                agent_id="TEST123"
            )
            
            with patch.object(model, '_get_model_max_tokens', return_value=1000):
                # Call the auto-compact method directly
                new_input, new_instructions, compacted = await model._auto_compact_if_needed(
                    estimated_tokens=700,  # 70% - below threshold
                    input="Test",
                    system_instructions=None
                )
                
                # Verify no compaction occurred
                assert compacted is False

    @pytest.mark.asyncio
    async def test_auto_compact_with_custom_threshold(self):
        """Test auto-compact with custom threshold value."""
        os.environ['CAI_AUTO_COMPACT'] = 'true'
        os.environ['CAI_AUTO_COMPACT_THRESHOLD'] = '0.5'  # 50% threshold
        
        from openai import AsyncOpenAI
        client = AsyncMock(spec=AsyncOpenAI)
        
        with patch('cai.sdk.agents.models.openai_chatcompletions.get_session_recorder'):
            model = OpenAIChatCompletionsModel(
                model="gpt-4",
                openai_client=client,
                agent_name="Test Agent",
                agent_id="TEST123"
            )
            
            with patch.object(model, '_get_model_max_tokens', return_value=1000):
                with patch('cai.sdk.agents.models.openai_chatcompletions.count_tokens_with_tiktoken') as mock_count:
                    mock_count.return_value = (600, 0)  # 60% - exceeds 50% threshold
                    
                    with patch('cai.repl.commands.memory.MEMORY_COMMAND_INSTANCE') as mock_memory:
                        mock_memory._ai_summarize_history = AsyncMock(return_value="Summary")
                        
                        with patch('cai.repl.commands.memory.COMPACTED_SUMMARIES', {}):
                            with patch('rich.console.Console'):
                                # Call the auto-compact method
                                new_input, new_instructions, compacted = await model._auto_compact_if_needed(
                                    estimated_tokens=600,
                                    input="Test",
                                    system_instructions=None
                                )
                                
                                # Verify compaction occurred at 60% with 50% threshold
                                assert compacted is True
                                mock_memory._ai_summarize_history.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_compact_error_handling(self):
        """Test that errors during auto-compact are handled gracefully."""
        os.environ['CAI_AUTO_COMPACT'] = 'true'
        os.environ['CAI_AUTO_COMPACT_THRESHOLD'] = '0.8'
        
        from openai import AsyncOpenAI
        client = AsyncMock(spec=AsyncOpenAI)
        
        with patch('cai.sdk.agents.models.openai_chatcompletions.get_session_recorder'):
            model = OpenAIChatCompletionsModel(
                model="gpt-4", 
                openai_client=client,
                agent_name="Test Agent",
                agent_id="TEST123"
            )
            
            with patch.object(model, '_get_model_max_tokens', return_value=1000):
                with patch('cai.repl.commands.memory.MEMORY_COMMAND_INSTANCE') as mock_memory:
                    # Make the summarization fail
                    mock_memory._ai_summarize_history = AsyncMock(side_effect=Exception("Failed"))
                    
                    with patch('rich.console.Console'):
                        # Call the auto-compact method
                        new_input, new_instructions, compacted = await model._auto_compact_if_needed(
                            estimated_tokens=850,
                            input="Test",
                            system_instructions=None
                        )
                        
                        # Should return without compaction on error
                        assert compacted is False
                        assert new_input == "Test"
                        assert new_instructions is None

    @pytest.mark.asyncio
    @pytest.mark.allow_call_model_methods
    async def test_auto_compact_integration(self):
        """Integration test for auto-compact during get_response."""
        os.environ['CAI_AUTO_COMPACT'] = 'true'
        os.environ['CAI_AUTO_COMPACT_THRESHOLD'] = '0.8'
        
        from openai import AsyncOpenAI
        from openai.types.chat import ChatCompletion, ChatCompletionMessage
        from openai.types.chat.chat_completion import Choice, CompletionUsage
        from cai.sdk.agents.model_settings import ModelSettings
        from cai.sdk.agents.models.interface import ModelTracing
        
        client = AsyncMock(spec=AsyncOpenAI)
        client.base_url = "https://api.openai.com"
        
        # Create mock response
        mock_response = ChatCompletion(
            id="test-id",
            object="chat.completion", 
            created=1234567890,
            model="gpt-4",
            choices=[
                Choice(
                    index=0,
                    message=ChatCompletionMessage(
                        role="assistant",
                        content="Response after compaction"
                    ),
                    finish_reason="stop"
                )
            ],
            usage=CompletionUsage(
                prompt_tokens=200,  # After compaction
                completion_tokens=50,
                total_tokens=250
            )
        )
        
        with patch('cai.sdk.agents.models.openai_chatcompletions.get_session_recorder'):
            model = OpenAIChatCompletionsModel(
                model="gpt-4",
                openai_client=client,
                agent_name="Test Agent",
                agent_id="TEST123"
            )
            
            # Mock dependencies
            with patch.object(model, '_get_model_max_tokens', return_value=1000):
                with patch('cai.sdk.agents.models.openai_chatcompletions.count_tokens_with_tiktoken') as mock_count:
                    # First count exceeds threshold, triggers compaction
                    mock_count.side_effect = [
                        (850, 0),  # Initial high count
                        (850, 0),  # Pre-compaction
                        (200, 0),  # Post-compaction
                    ]
                    
                    with patch('cai.repl.commands.memory.MEMORY_COMMAND_INSTANCE') as mock_memory:
                        mock_memory._ai_summarize_history = AsyncMock(return_value="Previous summary")
                        
                        with patch('cai.repl.commands.memory.COMPACTED_SUMMARIES', {}):
                            with patch('rich.console.Console'):
                                # Mock all the timer and tracking functions
                                with patch('cai.sdk.agents.models.openai_chatcompletions.stop_idle_timer'):
                                    with patch('cai.sdk.agents.models.openai_chatcompletions.start_active_timer'):
                                        with patch('cai.sdk.agents.models.openai_chatcompletions.stop_active_timer'):
                                            with patch('cai.sdk.agents.models.openai_chatcompletions.start_idle_timer'):
                                                with patch('cai.sdk.agents.models.openai_chatcompletions.COST_TRACKER'):
                                                    with patch.object(model, '_fetch_response', AsyncMock(return_value=mock_response)):
                                                        # Call get_response
                                                        result = await model.get_response(
                                                            system_instructions=None,
                                                            input="Test message",
                                                            model_settings=ModelSettings(),
                                                            tools=[],
                                                            output_schema=None,
                                                            handoffs=[],
                                                            tracing=ModelTracing.DISABLED
                                                        )
                                                        
                                                        # Verify compaction was triggered
                                                        mock_memory._ai_summarize_history.assert_called_once()
                                                        
                                                        # Verify response was returned
                                                        assert result is not None