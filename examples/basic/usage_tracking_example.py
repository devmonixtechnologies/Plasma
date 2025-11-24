"""
Example demonstrating global usage tracking functionality.

This example shows how CAI tracks usage globally across all executions
and saves the data to $HOME/.cai/usage.json
"""

import json
import os
from pathlib import Path

def display_usage_stats():
    """Display the current global usage statistics"""
    usage_file = Path.home() / ".cai" / "usage.json"
    
    if not usage_file.exists():
        print("No usage data found yet. Run CAI to start tracking usage.")
        return
    
    try:
        with open(usage_file, 'r') as f:
            usage_data = json.load(f)
        
        print("\n=== CAI Global Usage Statistics ===\n")
        
        # Display global totals
        totals = usage_data.get("global_totals", {})
        print("📊 Overall Usage:")
        print(f"  Total Cost: ${totals.get('total_cost', 0):.4f}")
        print(f"  Total Sessions: {totals.get('total_sessions', 0)}")
        print(f"  Total Requests: {totals.get('total_requests', 0)}")
        print(f"  Total Input Tokens: {totals.get('total_input_tokens', 0):,}")
        print(f"  Total Output Tokens: {totals.get('total_output_tokens', 0):,}")
        print(f"  Total Tokens: {totals.get('total_input_tokens', 0) + totals.get('total_output_tokens', 0):,}")
        
        # Display model usage
        model_usage = usage_data.get("model_usage", {})
        if model_usage:
            print("\n🤖 Usage by Model:")
            for model, stats in sorted(model_usage.items(), 
                                     key=lambda x: x[1].get('total_cost', 0), 
                                     reverse=True):
                print(f"\n  {model}:")
                print(f"    Cost: ${stats.get('total_cost', 0):.4f}")
                print(f"    Requests: {stats.get('total_requests', 0)}")
                print(f"    Input Tokens: {stats.get('total_input_tokens', 0):,}")
                print(f"    Output Tokens: {stats.get('total_output_tokens', 0):,}")
        
        # Display daily usage for the last 7 days
        daily_usage = usage_data.get("daily_usage", {})
        if daily_usage:
            print("\n📅 Recent Daily Usage:")
            sorted_days = sorted(daily_usage.items(), reverse=True)[:7]
            for day, stats in sorted_days:
                print(f"\n  {day}:")
                print(f"    Cost: ${stats.get('total_cost', 0):.4f}")
                print(f"    Requests: {stats.get('total_requests', 0)}")
                print(f"    Tokens: {stats.get('total_input_tokens', 0) + stats.get('total_output_tokens', 0):,}")
        
        # Display recent sessions
        sessions = usage_data.get("sessions", [])
        if sessions:
            print("\n🔄 Recent Sessions:")
            recent_sessions = sessions[-5:]  # Last 5 sessions
            for session in recent_sessions:
                print(f"\n  Session ID: {session.get('session_id', 'Unknown')[:8]}...")
                print(f"    Start: {session.get('start_time', 'Unknown')}")
                print(f"    Cost: ${session.get('total_cost', 0):.4f}")
                print(f"    Requests: {session.get('total_requests', 0)}")
                print(f"    Models: {', '.join(session.get('models_used', []))}")
                if session.get('end_time'):
                    print(f"    End: {session.get('end_time')}")
                else:
                    print("    Status: Active")
        
        print("\n" + "="*35 + "\n")
        
    except json.JSONDecodeError:
        print("Error: Unable to read usage data. File may be corrupted.")
    except Exception as e:
        print(f"Error: {str(e)}")


def reset_usage_stats():
    """Reset usage statistics (with confirmation)"""
    usage_file = Path.home() / ".cai" / "usage.json"
    
    if not usage_file.exists():
        print("No usage data to reset.")
        return
    
    response = input("Are you sure you want to reset all usage statistics? (yes/no): ")
    if response.lower() == 'yes':
        # Create backup
        backup_file = usage_file.with_suffix('.json.backup')
        import shutil
        shutil.copy2(usage_file, backup_file)
        print(f"Backup created at: {backup_file}")
        
        # Reset the file
        usage_file.unlink()
        print("Usage statistics have been reset.")
    else:
        print("Reset cancelled.")


def export_usage_report(output_file="cai_usage_report.json"):
    """Export usage statistics to a file"""
    usage_file = Path.home() / ".cai" / "usage.json"
    
    if not usage_file.exists():
        print("No usage data to export.")
        return
    
    import shutil
    shutil.copy2(usage_file, output_file)
    print(f"Usage report exported to: {output_file}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "reset":
            reset_usage_stats()
        elif command == "export":
            export_usage_report(sys.argv[2] if len(sys.argv) > 2 else "cai_usage_report.json")
        else:
            print("Usage: python usage_tracking_example.py [reset|export [filename]]")
    else:
        display_usage_stats()