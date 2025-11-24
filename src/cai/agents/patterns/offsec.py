from cai.repl.commands.parallel import ParallelConfig

# Pattern configuration  
offsec_pattern = {
    "name": "offsec_pattern",
    "type": "parallel",
    "description": (
        "Bug bounty and red team with different contexts for "
        "offensive security ops"
    ),
    "configs": [
        ParallelConfig("redteam_agent"),
        ParallelConfig("bug_bounter_agent")
    ],
    "unified_context": False
}