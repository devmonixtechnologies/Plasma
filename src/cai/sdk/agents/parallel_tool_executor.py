"""
Parallel Tool Executor - Enables tool execution across multiple agents in parallel.

This module provides a shared tool execution pool that allows multiple agents to submit
tool calls that execute in parallel, breaking the sequential LLM->Tools->LLM bottleneck.
"""

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from collections import defaultdict
import weakref
import logging

from .tool import FunctionTool
from .items import ToolCallOutputItem, ItemHelpers
from .agent import Agent
from .run_context import RunContextWrapper

logger = logging.getLogger(__name__)


@dataclass
class PendingToolCall:
    """Represents a tool call waiting to be executed."""
    tool_call_id: str
    tool_name: str
    tool_function: Callable
    arguments: Dict[str, Any]
    agent_name: str
    context_wrapper: RunContextWrapper
    submitted_at: float = field(default_factory=time.time)
    result: Optional[Any] = None
    error: Optional[Exception] = None
    completed: bool = False


class ParallelToolExecutor:
    """
    Manages parallel tool execution across multiple agents.
    
    This executor allows agents to submit tool calls that execute immediately
    in parallel, rather than waiting for the LLM response cycle to complete.
    """
    
    def __init__(self, max_concurrent_tools: int = 50):
        self.max_concurrent_tools = max_concurrent_tools
        self.pending_calls: Dict[str, PendingToolCall] = {}
        self.active_tasks: List[asyncio.Task] = []
        self.agent_queues: Dict[str, List[str]] = defaultdict(list)  # agent_name -> [tool_call_ids]
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max_concurrent_tools)
        self._running = True
        self._executor_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the background executor task."""
        if self._executor_task is None:
            self._executor_task = asyncio.create_task(self._run_executor())
            logger.debug("Started parallel tool executor")
    
    async def stop(self):
        """Stop the executor and wait for pending tasks."""
        self._running = False
        if self._executor_task:
            await self._executor_task
        
        # Cancel any remaining tasks
        for task in self.active_tasks:
            if not task.done():
                task.cancel()
        
        if self.active_tasks:
            await asyncio.gather(*self.active_tasks, return_exceptions=True)
    
    async def submit_tool_call(
        self,
        tool_name: str,
        tool_function: Callable,
        arguments: Dict[str, Any],
        agent_name: str,
        context_wrapper: RunContextWrapper,
        tool_call_id: Optional[str] = None
    ) -> str:
        """
        Submit a tool call for parallel execution.
        
        Returns the tool_call_id that can be used to retrieve the result.
        """
        if tool_call_id is None:
            tool_call_id = f"call_{uuid.uuid4().hex[:16]}"
        
        async with self._lock:
            pending_call = PendingToolCall(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                tool_function=tool_function,
                arguments=arguments,
                agent_name=agent_name,
                context_wrapper=context_wrapper
            )
            
            self.pending_calls[tool_call_id] = pending_call
            self.agent_queues[agent_name].append(tool_call_id)
            
        logger.debug(f"Submitted tool call {tool_call_id} for {tool_name} from {agent_name}")
        return tool_call_id
    
    async def get_tool_result(self, tool_call_id: str, timeout: float = 300) -> Tuple[Any, Optional[Exception]]:
        """
        Wait for and retrieve the result of a tool call.
        
        Returns (result, error) tuple.
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            async with self._lock:
                if tool_call_id in self.pending_calls:
                    call = self.pending_calls[tool_call_id]
                    if call.completed:
                        # Remove from pending and return result
                        self.pending_calls.pop(tool_call_id)
                        if call.agent_name in self.agent_queues:
                            self.agent_queues[call.agent_name].remove(tool_call_id)
                        return call.result, call.error
            
            await asyncio.sleep(0.1)
        
        raise asyncio.TimeoutError(f"Tool call {tool_call_id} timed out after {timeout} seconds")
    
    async def get_agent_results(self, agent_name: str) -> List[Tuple[str, Any, Optional[Exception]]]:
        """
        Get all completed results for a specific agent.
        
        Returns list of (tool_call_id, result, error) tuples.
        """
        results = []
        
        async with self._lock:
            tool_call_ids = list(self.agent_queues.get(agent_name, []))
            
            for tool_call_id in tool_call_ids:
                if tool_call_id in self.pending_calls:
                    call = self.pending_calls[tool_call_id]
                    if call.completed:
                        results.append((tool_call_id, call.result, call.error))
                        self.pending_calls.pop(tool_call_id)
                        self.agent_queues[agent_name].remove(tool_call_id)
        
        return results
    
    async def _run_executor(self):
        """Background task that processes pending tool calls."""
        while self._running:
            try:
                # Get pending calls that need execution
                async with self._lock:
                    pending = [
                        call for call in self.pending_calls.values()
                        if not call.completed and not any(
                            task for task in self.active_tasks
                            if hasattr(task, '_tool_call_id') and task._tool_call_id == call.tool_call_id
                        )
                    ]
                
                # Execute pending calls
                for call in pending:
                    if len(self.active_tasks) >= self.max_concurrent_tools:
                        # Clean up completed tasks
                        self.active_tasks = [t for t in self.active_tasks if not t.done()]
                        
                        if len(self.active_tasks) >= self.max_concurrent_tools:
                            break
                    
                    # Create execution task
                    task = asyncio.create_task(self._execute_tool_call(call))
                    task._tool_call_id = call.tool_call_id  # type: ignore
                    self.active_tasks.append(task)
                
                # Clean up completed tasks
                self.active_tasks = [t for t in self.active_tasks if not t.done()]
                
                # Brief sleep to avoid busy waiting
                await asyncio.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error in parallel tool executor: {e}")
                await asyncio.sleep(0.1)
    
    async def _execute_tool_call(self, call: PendingToolCall):
        """Execute a single tool call."""
        async with self._semaphore:
            try:
                logger.debug(f"Executing tool {call.tool_name} (ID: {call.tool_call_id}) for {call.agent_name}")
                
                # Execute the tool function
                result = await call.tool_function(call.context_wrapper, call.arguments)
                
                async with self._lock:
                    if call.tool_call_id in self.pending_calls:
                        call.result = result
                        call.completed = True
                        
                logger.debug(f"Completed tool {call.tool_name} (ID: {call.tool_call_id})")
                
            except Exception as e:
                logger.error(f"Error executing tool {call.tool_name}: {e}")
                async with self._lock:
                    if call.tool_call_id in self.pending_calls:
                        call.error = e
                        call.completed = True


# Global instance for shared tool execution
_global_executor: Optional[ParallelToolExecutor] = None


def get_parallel_tool_executor() -> ParallelToolExecutor:
    """Get or create the global parallel tool executor."""
    global _global_executor
    if _global_executor is None:
        _global_executor = ParallelToolExecutor()
    return _global_executor


async def ensure_executor_started():
    """Ensure the global executor is started."""
    executor = get_parallel_tool_executor()
    if executor._executor_task is None:
        await executor.start()


class ParallelToolMixin:
    """
    Mixin for agents to enable parallel tool execution.
    
    This allows agents to submit tool calls that execute immediately
    rather than waiting for the full LLM response cycle.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._parallel_executor = get_parallel_tool_executor()
        self._pending_parallel_calls: List[str] = []
    
    async def submit_parallel_tool(
        self,
        tool_name: str,
        tool_function: Callable,
        arguments: Dict[str, Any],
        context_wrapper: RunContextWrapper
    ) -> str:
        """Submit a tool for parallel execution."""
        await ensure_executor_started()
        
        tool_call_id = await self._parallel_executor.submit_tool_call(
            tool_name=tool_name,
            tool_function=tool_function,
            arguments=arguments,
            agent_name=getattr(self, 'name', 'unknown'),
            context_wrapper=context_wrapper
        )
        
        self._pending_parallel_calls.append(tool_call_id)
        return tool_call_id
    
    async def collect_parallel_results(self) -> List[ToolCallOutputItem]:
        """Collect results from parallel tool executions."""
        results = []
        
        for tool_call_id in self._pending_parallel_calls[:]:
            try:
                result, error = await self._parallel_executor.get_tool_result(tool_call_id, timeout=1.0)
                
                if error:
                    output = f"Error: {str(error)}"
                else:
                    output = result
                
                # Create a mock tool call for the result
                from openai.types.responses import ResponseFunctionToolCall
                mock_tool_call = ResponseFunctionToolCall(
                    id=tool_call_id,
                    name="parallel_tool",
                    arguments="{}"
                )
                
                results.append(
                    ToolCallOutputItem(
                        output=output,
                        raw_item=ItemHelpers.tool_call_output_item(mock_tool_call, output),
                        agent=self  # type: ignore
                    )
                )
                
                self._pending_parallel_calls.remove(tool_call_id)
                
            except asyncio.TimeoutError:
                # Tool still running, skip for now
                pass
            except Exception as e:
                logger.error(f"Error collecting parallel result: {e}")
        
        return results