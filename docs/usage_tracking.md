# CAI Global Usage Tracking

CAI now includes automatic global usage tracking that persists token usage and costs across all sessions to `$HOME/.cai/usage.json`.

## Features

- **Automatic Tracking**: All LLM interactions are automatically tracked
- **Global Persistence**: Usage data persists across all CAI sessions
- **Model-Specific Stats**: Track usage per model (GPT-4, Claude, etc.)
- **Daily Breakdowns**: View usage by day
- **Session History**: Track individual session costs and tokens
- **Cost Calculation**: Automatic cost calculation based on model pricing

## Usage Data Structure

The `$HOME/.cai/usage.json` file contains:

```json
{
  "global_totals": {
    "total_cost": 0.049836,
    "total_input_tokens": 12067,
    "total_output_tokens": 909,
    "total_requests": 8,
    "total_sessions": 4
  },
  "model_usage": {
    "claude-sonnet-4": {
      "total_cost": 0.049836,
      "total_input_tokens": 12067,
      "total_output_tokens": 909,
      "total_requests": 8
    }
  },
  "daily_usage": {
    "2025-06-11": {
      "total_cost": 0.049836,
      "total_input_tokens": 12067,
      "total_output_tokens": 909,
      "total_requests": 8
    }
  },
  "sessions": [...]
}
```

## Viewing Usage Statistics

### Command Line Tool
```bash
python examples/basic/usage_tracking_example.py
```

This displays:
- Overall usage totals
- Usage by model
- Recent daily usage
- Recent session history

### Export Usage Report
```bash
python examples/basic/usage_tracking_example.py export [filename]
```

### Reset Usage Statistics
```bash
python examples/basic/usage_tracking_example.py reset
```

## Disabling Usage Tracking

If you prefer not to track usage globally, set the environment variable:

```bash
export CAI_DISABLE_USAGE_TRACKING=true
```

## Implementation Details

The usage tracking is implemented in:
- `src/cai/sdk/agents/global_usage_tracker.py` - Core tracking logic
- `src/cai/sdk/agents/models/openai_chatcompletions.py` - Integration points
- `src/cai/cli.py` - Session start/end hooks

### Key Features:
- **Thread-Safe**: Uses locks to ensure data consistency
- **Interrupt-Safe**: Handles Ctrl+C gracefully without blocking
- **Atomic Writes**: Uses temporary files and atomic rename operations
- **Periodic Saves**: Saves every 10 requests to minimize I/O
- **Error Resilient**: Silently continues if tracking fails

## Privacy

All usage data is stored locally in your home directory. No data is sent to external servers. The tracking only records:
- Token counts
- Costs
- Model names
- Timestamps
- Session IDs

No conversation content or sensitive data is tracked.