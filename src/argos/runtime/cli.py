"""Command Line Interface adapter for ARGOS runtime."""

import argparse
import sys
from collections.abc import Sequence

from argos.runtime.argos_runtime import ArgosRuntime
from argos.runtime.models import RuntimeStatus


def main(args: Sequence[str] | None = None) -> int:
    """Main CLI entry point for ARGOS.

    Args:
        args: Optional command line argument strings.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    parser = argparse.ArgumentParser(
        prog="argos",
        description="ARGOS - Adaptive Reasoning & General Operating System",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: run
    run_parser = subparsers.add_parser(
        "run", help="Run a single user request end-to-end"
    )
    run_parser.add_argument(
        "request",
        type=str,
        help="Raw text user request (e.g. 'open calculator')",
    )
    run_parser.add_argument(
        "--db",
        type=str,
        default=":memory:",
        help="Path to SQLite database storage (default: :memory:)",
    )
    run_parser.add_argument(
        "--session",
        type=str,
        default="default",
        help="Session identifier string (default: default)",
    )

    # Command: interactive
    interactive_parser = subparsers.add_parser(
        "interactive", help="Start an interactive ARGOS REPL session"
    )
    interactive_parser.add_argument(
        "--db",
        type=str,
        default=":memory:",
        help="Path to SQLite database storage (default: :memory:)",
    )
    interactive_parser.add_argument(
        "--session",
        type=str,
        default="interactive_session",
        help="Session identifier string (default: interactive_session)",
    )

    parsed_args = parser.parse_args(args)

    if not parsed_args.command:
        parser.print_help()
        return 0

    if parsed_args.command == "run":
        with ArgosRuntime.create_default(db_path=parsed_args.db) as runtime:
            response = runtime.handle(
                request=parsed_args.request,
                session_id=parsed_args.session,
            )
            print(f"Status: {response.status.value}")
            if response.output:
                print(f"Output: {response.output}")
            if response.error_message:
                print(f"Error:  {response.error_message}")
            return 0 if response.status == RuntimeStatus.SUCCESS else 1

    if parsed_args.command == "interactive":
        print("ARGOS Interactive Session (type 'exit' or 'quit' to end)")
        with ArgosRuntime.create_default(db_path=parsed_args.db) as runtime:
            while True:
                try:
                    user_input = input("ARGOS> ").strip()
                    if not user_input:
                        continue
                    if user_input.lower() in ("exit", "quit"):
                        print("Ending session.")
                        break
                    response = runtime.handle(
                        request=user_input,
                        session_id=parsed_args.session,
                    )
                    out_text = response.output or response.error_message or ""
                    print(f"[{response.status.value}] {out_text}")
                except (EOFError, KeyboardInterrupt):
                    print("\nEnding session.")
                    break
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
