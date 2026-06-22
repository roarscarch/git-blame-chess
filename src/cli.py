"""CLI entry point for git-blame-chess."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from .game import Game


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Add shared arguments to a subcommand parser."""
    parser.add_argument(
        "--repo",
        type=str,
        default=".",
        help="Path to the git repository (default: current directory)",
    )
    parser.add_argument(
        "--branch",
        type=str,
        default=None,
        help="Branch to analyze (default: current branch)",
    )


def cmd_play(args: argparse.Namespace) -> None:
    """Interactive play through commit history."""
    from .interactive import InteractivePlayer

    game = Game.from_repo(Path(args.repo), branch=args.branch)
    player = InteractivePlayer(game)
    player.run()


def cmd_duel(args: argparse.Namespace) -> None:
    """Play a duel between two branches."""
    from .interactive import InteractivePlayer

    if not args.branches or len(args.branches) < 2:
        print("Error: --branches requires at least two branch names.", file=sys.stderr)
        sys.exit(1)

    game = Game.from_repo_duel(Path(args.repo), branches=args.branches)
    player = InteractivePlayer(game)
    player.run()


def cmd_export(args: argparse.Namespace) -> None:
    """Export the game as a PGN file."""
    game = Game.from_repo(Path(args.repo), branch=args.branch)
    pgn = game.to_pgn()
    output_path = Path(args.output) if args.output else Path("game.pgn")
    output_path.write_text(pgn)
    print(f"Game exported to {output_path.resolve()}")


def main(argv: Optional[list[str]] = None) -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Play chess with your git history",
        prog="git-blame-chess",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Play subcommand
    play_parser = subparsers.add_parser("play", help="Play through commit history interactively")
    add_arguments(play_parser)
    play_parser.add_argument(
        "--ai",
        action="store_true",
        help="Let the AI (git history) play automatically",
    )
    play_parser.set_defaults(func=cmd_play)

    # Duel subcommand
    duel_parser = subparsers.add_parser("duel", help="Play a duel between two branches")
    add_arguments(duel_parser)
    duel_parser.add_argument(
        "--branches",
        type=str,
        nargs="+",
        required=True,
        help="Two or more branch names to duel",
    )
    duel_parser.set_defaults(func=cmd_duel)

    # Export subcommand
    export_parser = subparsers.add_parser("export", help="Export the game as a PGN file")
    add_arguments(export_parser)
    export_parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (default: game.pgn)",
    )
    export_parser.set_defaults(func=cmd_export)

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
