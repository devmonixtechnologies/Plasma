from cai.repl.commands.parallel import ParallelConfig

# Pattern configuration  
offsec_pattern = {
    "name": "offsec_pattern",
    "type": "parallel",
    "description": (
        "Bug bounty and red team swarms with different contexts for "
        "offensive security ops"
    ),
    "configs": [
        ParallelConfig("redteam_swarm_pattern"),
        ParallelConfig("bb_triage_swarm_pattern")
    ],
    "unified_context": False
}