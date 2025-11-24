#!/usr/bin/env python3
"""
Example: Using CAI Continue Mode for Security Jokes

This example demonstrates how to use CAI's --continue flag to have an agent
continuously tell cybersecurity jokes without manual intervention.

Usage:
    python examples/continue_mode_jokes.py
    
Or directly from command line:
    cai --continue --prompt "tell me a joke about security"
"""

import subprocess
import sys
import os
import signal

def run_joke_session():
    """Run CAI with continue mode to tell security jokes"""
    
    print("🎭 CAI Security Joke Session")
    print("=" * 60)
    print("Starting CAI in continue mode to tell cybersecurity jokes...")
    print("Press Ctrl+C to stop when you've had enough laughs!")
    print("=" * 60)
    
    # Command to run CAI with continue flag
    cmd = [
        sys.executable, 
        "src/cai/cli.py",
        "--continue",
        "--prompt", "tell me a joke about cybersecurity"
    ]
    
    try:
        # Run CAI
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Close stdin to prevent hanging
        proc.stdin.close()
        
        # Read and display output
        for line in proc.stdout:
            print(line, end='')
            
            # Highlight continuation messages
            if "Auto-continuing with:" in line:
                print("🔄 " + "=" * 56)
                
    except KeyboardInterrupt:
        print("\n\n✋ Joke session interrupted by user")
        if proc.poll() is None:
            proc.terminate()
            print("   Gracefully stopping CAI...")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        
    print("\n" + "=" * 60)
    print("Thanks for using CAI joke mode! 🎉")

if __name__ == "__main__":
    # Change to project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    
    run_joke_session()