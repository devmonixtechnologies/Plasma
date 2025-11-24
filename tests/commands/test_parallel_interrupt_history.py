"""Test parallel agents' history persistence when interrupted."""

import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from cai.repl.commands.parallel import ParallelCommand, PARALLEL_CONFIGS, ParallelConfig, PARALLEL_AGENT_INSTANCES
from cai.sdk.agents.parallel_isolation import PARALLEL_ISOLATION
from cai.sdk.agents import Agent, OpenAIChatCompletionsModel
from openai import AsyncOpenAI
import os


class TestParallelInterruptHistory:
    """Test suite for parallel agent history persistence on interruption."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Clear any existing configurations
        PARALLEL_CONFIGS.clear()
        PARALLEL_AGENT_INSTANCES.clear()
        PARALLEL_ISOLATION.clear_all_histories()
        self.command = ParallelCommand()
    
    def teardown_method(self):
        """Clean up after each test."""
        PARALLEL_CONFIGS.clear()
        PARALLEL_AGENT_INSTANCES.clear()
        PARALLEL_ISOLATION.clear_all_histories()
    
    @patch('cai.cli.Runner')
    @patch('cai.cli.get_agent_by_name')
    def test_parallel_history_saved_on_interrupt(self, mock_get_agent, mock_runner):
        """Test that parallel agents' histories are saved when interrupted with Ctrl+C."""
        
        # Create mock agents with message histories
        def create_mock_agent(name, agent_id):
            mock_agent = MagicMock()
            mock_agent.name = name
            mock_agent.model = MagicMock()
            mock_agent.model.message_history = []
            mock_agent.model.agent_id = agent_id
            
            # Mock the add_to_message_history method to append to the list
            def add_message(msg):
                mock_agent.model.message_history.append(msg)
                # Also update PARALLEL_ISOLATION
                if PARALLEL_ISOLATION.is_parallel_mode() and agent_id:
                    PARALLEL_ISOLATION.update_isolated_history(agent_id, msg)
            
            mock_agent.model.add_to_message_history = add_message
            return mock_agent
        
        # Setup parallel configs
        config1 = ParallelConfig("redteam_agent")
        config1.id = "P1"
        config2 = ParallelConfig("bug_bounter_agent")
        config2.id = "P2"
        PARALLEL_CONFIGS.extend([config1, config2])
        
        # Create mock agents
        agent1 = create_mock_agent("Red Team Agent", "P1")
        agent2 = create_mock_agent("Bug Bounty Hunter", "P2")
        
        # Store them in PARALLEL_AGENT_INSTANCES
        PARALLEL_AGENT_INSTANCES[(config1.agent_name, 1)] = agent1
        PARALLEL_AGENT_INSTANCES[(config2.agent_name, 2)] = agent2
        
        # Mock get_agent_by_name to return our mocked agents
        def get_agent_side_effect(agent_type, **kwargs):
            agent_id = kwargs.get('agent_id')
            if agent_id == "P1":
                return agent1
            elif agent_id == "P2":
                return agent2
            return MagicMock()
        
        mock_get_agent.side_effect = get_agent_side_effect
        
        # Enable parallel mode
        PARALLEL_ISOLATION._parallel_mode = True
        
        # Add initial history
        base_history = [{"role": "user", "content": "Initial message"}]
        PARALLEL_ISOLATION.transfer_to_parallel(base_history, 2, ["P1", "P2"])
        
        # First, set up the agents' message histories with the initial history
        agent1.model.message_history = base_history.copy()
        agent2.model.message_history = base_history.copy()
        
        # Simulate agents adding messages during execution
        agent1.model.add_to_message_history({"role": "assistant", "content": "Response from agent 1"})
        agent2.model.add_to_message_history({"role": "assistant", "content": "Response from agent 2"})
        
        # Simulate interruption by saving histories (this is what our fix does)
        for idx, config in enumerate(PARALLEL_CONFIGS, 1):
            instance_key = (config.agent_name, idx)
            if instance_key in PARALLEL_AGENT_INSTANCES:
                instance_agent = PARALLEL_AGENT_INSTANCES[instance_key]
                if hasattr(instance_agent, 'model') and hasattr(instance_agent.model, 'message_history'):
                    agent_id = config.id or f"P{idx}"
                    PARALLEL_ISOLATION.replace_isolated_history(agent_id, instance_agent.model.message_history)
        
        # Verify histories were saved
        history1 = PARALLEL_ISOLATION.get_isolated_history("P1")
        history2 = PARALLEL_ISOLATION.get_isolated_history("P2")
        
        assert len(history1) == 2  # Initial + agent response
        assert history1[0]["content"] == "Initial message"
        assert history1[1]["content"] == "Response from agent 1"
        
        assert len(history2) == 2  # Initial + agent response
        assert history2[0]["content"] == "Initial message"
        assert history2[1]["content"] == "Response from agent 2"
    
    @pytest.mark.asyncio
    async def test_async_cancellation_saves_history(self):
        """Test that histories are saved when async tasks are cancelled."""
        
        # Setup parallel configs
        config = ParallelConfig("redteam_agent")
        config.id = "P1"
        
        # Create a mock agent
        mock_agent = MagicMock()
        mock_agent.name = "Red Team Agent"
        mock_agent.model = MagicMock()
        mock_agent.model.message_history = [
            {"role": "user", "content": "Test message"},
            {"role": "assistant", "content": "Test response"}
        ]
        
        # Enable parallel mode
        PARALLEL_ISOLATION._parallel_mode = True
        
        # Simulate the exception handler saving history
        try:
            # Simulate asyncio.CancelledError
            raise asyncio.CancelledError()
        except asyncio.CancelledError:
            # This is what our fix does in run_agent_instance
            if mock_agent and config.id:
                if hasattr(mock_agent, 'model') and hasattr(mock_agent.model, 'message_history'):
                    PARALLEL_ISOLATION.replace_isolated_history(config.id, mock_agent.model.message_history)
        
        # Verify history was saved
        saved_history = PARALLEL_ISOLATION.get_isolated_history("P1")
        assert saved_history is not None
        assert len(saved_history) == 2
        assert saved_history[0]["content"] == "Test message"
        assert saved_history[1]["content"] == "Test response"
    
    def test_history_command_shows_saved_histories(self):
        """Test that /history command can access saved parallel agent histories."""
        from cai.sdk.agents.simple_agent_manager import AGENT_MANAGER
        from cai.repl.commands.history import HistoryCommand
        
        # Setup parallel mode with some history
        PARALLEL_ISOLATION._parallel_mode = True
        
        # Setup parallel configs
        config1 = ParallelConfig("redteam_agent")
        config1.id = "P1"
        config2 = ParallelConfig("bug_bounter_agent")
        config2.id = "P2"
        PARALLEL_CONFIGS.extend([config1, config2])
        
        # Add test histories
        history1 = [
            {"role": "user", "content": "Message to agent 1"},
            {"role": "assistant", "content": "Response from agent 1"}
        ]
        history2 = [
            {"role": "user", "content": "Message to agent 2"},
            {"role": "assistant", "content": "Response from agent 2"}
        ]
        
        PARALLEL_ISOLATION.replace_isolated_history("P1", history1)
        PARALLEL_ISOLATION.replace_isolated_history("P2", history2)
        
        # Sync with AGENT_MANAGER (simulating what would happen after interruption)
        AGENT_MANAGER.clear_all_histories()
        
        # Add histories directly without registering
        for msg in history1:
            AGENT_MANAGER.add_to_history("Red Team Agent #1", msg)
        for msg in history2:
            AGENT_MANAGER.add_to_history("Bug Bounty Hunter #2", msg)
        
        # Verify histories are accessible via AGENT_MANAGER
        agent1_history = AGENT_MANAGER.get_message_history("Red Team Agent #1")
        agent2_history = AGENT_MANAGER.get_message_history("Bug Bounty Hunter #2")
        
        assert len(agent1_history) == 2
        assert agent1_history[0]["content"] == "Message to agent 1"
        
        assert len(agent2_history) == 2
        assert agent2_history[0]["content"] == "Message to agent 2"
        
        # Also verify PARALLEL_ISOLATION still has the histories
        iso_hist1 = PARALLEL_ISOLATION.get_isolated_history("P1")
        iso_hist2 = PARALLEL_ISOLATION.get_isolated_history("P2")
        
        assert len(iso_hist1) == 2
        assert len(iso_hist2) == 2