#!/usr/bin/env python3
"""
Tool to record asciinema sessions of JSONL replay files.

Usage:
    cai-asciinema path/to/file.jsonl 0.5

This tool wraps asciinema recording to capture replay sessions.
"""
import argparse
import os
import subprocess
import sys


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Record asciinema sessions of JSONL replay files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cai-asciinema path/to/file.jsonl 0.5
  cai-asciinema conversation.jsonl 1.0
"""
    )

    parser.add_argument(
        "jsonl_file",
        help="Path to the JSONL file containing conversation history"
    )

    parser.add_argument(
        "replay_delay",
        type=float,
        help="Time in seconds to wait between actions"
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path for the recording (optional)"
    )

    return parser.parse_args()


def main():
    """Main function to record asciinema session."""
    args = parse_arguments()

    # Validate that the JSONL file exists
    if not os.path.exists(args.jsonl_file):
        print(f"Error: File {args.jsonl_file} not found", file=sys.stderr)
        sys.exit(1)

    # Build the command to record using the same Python interpreter
    replay_command = f"{sys.executable} tools/replay.py {args.jsonl_file} {args.replay_delay}"

    # Build asciinema command
    asciinema_cmd = ["asciinema", "rec", f"--command={replay_command}", "--overwrite"]

    # Add output file if specified
    if args.output:
        asciinema_cmd.append(args.output)

    print(f"Recording asciinema session for {args.jsonl_file} with delay {args.replay_delay}s...")
    print(f"Running: {' '.join(asciinema_cmd)}")

    try:
        # Execute the asciinema command
        result = subprocess.run(asciinema_cmd, check=True)
        # result = subprocess.run(replay_command, check=True)
        print("Recording completed successfully!")
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"Error: asciinema recording failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)
    except FileNotFoundError:
        print("Error: asciinema not found. Please install asciinema first.", file=sys.stderr)
        print("Install with: pip install asciinema", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
