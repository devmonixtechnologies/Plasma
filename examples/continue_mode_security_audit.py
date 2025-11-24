#!/usr/bin/env python3
"""
Example: Autonomous Security Audit with CAI Continue Mode

This example shows how to use CAI's --continue flag to perform an autonomous
security audit that continues analyzing files and finding vulnerabilities
without manual intervention.

Usage:
    python examples/continue_mode_security_audit.py
    
Or directly from command line:
    cai --continue --prompt "perform a security audit of all Python files"
"""

import subprocess
import sys
import os
import time
import signal

def run_security_audit():
    """Run CAI with continue mode for autonomous security auditing"""
    
    print("🔒 CAI Autonomous Security Audit")
    print("=" * 60)
    print("Starting autonomous security audit...")
    print("CAI will continuously analyze code for vulnerabilities.")
    print("Press Ctrl+C to stop the audit.")
    print("=" * 60)
    
    # Create a sample vulnerable file for demonstration
    sample_file = "sample_vulnerable.py"
    with open(sample_file, "w") as f:
        f.write('''
# Sample file with security vulnerabilities for CAI to find

import os
import sqlite3

def login(username, password):
    # SQL Injection vulnerability
    conn = sqlite3.connect('users.db')
    query = f"SELECT * FROM users WHERE name='{username}' AND pass='{password}'"
    cursor = conn.execute(query)
    return cursor.fetchone()

def execute_command(user_input):
    # Command Injection vulnerability
    os.system(f"echo {user_input}")
    
def read_file(filename):
    # Path Traversal vulnerability
    with open(f"/app/data/{filename}", "r") as f:
        return f.read()

# Hardcoded credentials
API_KEY = "sk-1234567890abcdef"
DB_PASSWORD = "admin123"
''')
    
    # Command to run CAI audit
    cmd = [
        sys.executable, 
        "src/cai/cli.py",
        "--continue",
        "--prompt", f"Perform a comprehensive security audit of {sample_file}, "
                   f"identify all vulnerabilities, and suggest fixes"
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
        
        # Close stdin
        proc.stdin.close()
        
        # Track findings
        vulnerabilities_found = []
        continuation_count = 0
        
        # Read output
        for line in proc.stdout:
            print(line, end='')
            
            # Track vulnerabilities
            vuln_keywords = ["injection", "vulnerability", "security issue", 
                           "hardcoded", "insecure", "exposed"]
            if any(keyword in line.lower() for keyword in vuln_keywords):
                vulnerabilities_found.append(line.strip())
            
            # Track continuations
            if "Auto-continuing with:" in line:
                continuation_count += 1
                print(f"🔄 Continuation #{continuation_count} " + "=" * 40)
                
                # Stop after finding multiple issues
                if continuation_count >= 5:
                    print("\n📋 Audit Summary: Found multiple security issues.")
                    print("   Stopping audit after thorough analysis.")
                    proc.terminate()
                    break
                    
    except KeyboardInterrupt:
        print("\n\n✋ Security audit interrupted by user")
        if proc and proc.poll() is None:
            proc.terminate()
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        
    finally:
        # Cleanup
        if os.path.exists(sample_file):
            os.remove(sample_file)
            print(f"\n🗑️  Cleaned up {sample_file}")
    
    print("\n" + "=" * 60)
    print("🔒 Security Audit Complete")
    if vulnerabilities_found:
        print(f"   Found {len(set(vulnerabilities_found))} potential security issues")
    print("=" * 60)

if __name__ == "__main__":
    # Change to project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    
    run_security_audit()