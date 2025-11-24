"""
Parallel security assessment pattern - red/blue team with shared context.

This pattern demonstrates the use of the unified Pattern class for
parallel agent execution, where both red and blue team agents share
the same context.
"""

from cai.repl.commands.parallel import ParallelConfig

# Pattern configuration
blue_team_red_team_shared_context_pattern = {
    "name": "blue_team_red_team_shared_context",
    "type": "parallel",
    "description": "Red and blue team agent with shared context",
    "configs": [
        ParallelConfig("redteam_agent", unified_context=True),
        ParallelConfig("blueteam_agent", unified_context=True)
    ],
    "unified_context": True
}