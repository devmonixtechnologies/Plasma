#!/usr/bin/env python3
"""
Tool to create GIF recordings of JSONL replay files.

Usage:
    cai-gif path/to/file.jsonl 0.5 output.gif

This tool wraps asciinema recording and agg to create GIF animations.
"""
import argparse
import os
import subprocess
import sys
import tempfile


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Create GIF recordings of JSONL replay files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cai-gif path/to/file.jsonl 0.5 output.gif
  cai-gif conversation.jsonl 1.0 demo.gif
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
        "output_gif",
        help="Output GIF file path"
    )

    return parser.parse_args()


def check_dependencies():
    """Check if required tools are installed."""
    missing_deps = []

    # Check for asciinema
    try:
        subprocess.run(["asciinema", "--version"], 
                     check=True, 
                     capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        missing_deps.append("asciinema")

    # Check for agg
    try:
        subprocess.run(["agg", "--version"], 
                     check=True, 
                     capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        missing_deps.append("agg")

    if missing_deps:
        print("Error: Missing required dependencies:", file=sys.stderr)
        if "asciinema" in missing_deps:
            print("  - asciinema: Install with 'pip install asciinema'", 
                  file=sys.stderr)
        if "agg" in missing_deps:
            print("  - agg: Install with 'npm install -g @asciinema/agg'", 
                  file=sys.stderr)
        sys.exit(1)


def main():
    """Main function to create GIF recording."""
    args = parse_arguments()
    check_dependencies()

    # Validate that the JSONL file exists
    if not os.path.exists(args.jsonl_file):
        print(f"Error: File {args.jsonl_file} not found", file=sys.stderr)
        sys.exit(1)

    # Create a temporary file for the asciinema cast
    with tempfile.NamedTemporaryFile(suffix='.cast', delete=False) as temp_cast:
        temp_cast_path = temp_cast.name

    try:
        # Build the command to record using the same Python interpreter
        replay_command = f"{sys.executable} tools/replay.py {args.jsonl_file} {args.replay_delay}"

        # Build asciinema command
        asciinema_cmd = [
            "asciinema", "rec",
            f"--command={replay_command}",
            "--overwrite",
            temp_cast_path
        ]

        print(f"Recording asciinema session for {args.jsonl_file} with delay {args.replay_delay}s...")
        print(f"Running: {' '.join(asciinema_cmd)}")

        # Execute the asciinema command
        subprocess.run(asciinema_cmd, check=True)

        # Convert the cast file to GIF using agg
        print(f"Converting recording to GIF: {args.output_gif}")
        agg_cmd = ["agg", temp_cast_path, args.output_gif]
        subprocess.run(agg_cmd, check=True)

        print("GIF creation completed successfully!")
        return 0

    except subprocess.CalledProcessError as e:
        print(f"Error: Command failed with exit code {e.returncode}", 
              file=sys.stderr)
        return e.returncode
    except Exception as e:  # pylint: disable=broad-except
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1
    finally:
        # Clean up the temporary cast file
        try:
            os.unlink(temp_cast_path)
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main()) 