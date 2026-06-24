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
    from .duel import BranchDuel

    if not args.left_branch or not args.right_branch:
        print("Error: duel mode requires --left and --right branches.")
        sys.exit(1)

    duel = BranchDuel(Path(args.repo), args.left_branch, args.right_branch)
    player = InteractivePlayer.from_duel(duel)
    player.run()


def cmd_export(args: argparse.Namespace) -> None:
    """Export the game as PGN."""
    from .export import export_pgn

    game = Game.from_repo(Path(args.repo), branch=args.branch)
    output = Path(args.output) if args.output else None
    pgn = export_pgn(game, output_path=output)
    if not args.output:
        print(pgn)


def cmd_import_pgn(args: argparse.Namespace) -> None:
    """Import a PGN file into the repo as a git branch."""
    from .import_pgn import import_pgn

    pgn_path = Path(args.pgn_file)
    if not pgn_path.exists():
        print(f"Error: PGN file {pgn_path} not found.")
        sys.exit(1)
    branch_name = args.branch_name or "imported-game"
    import_pgn(Path(args.repo), pgn_path, branch_name)
    print(f"Imported game to branch '{branch_name}'")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Git Blame Chess - Play chess with your git history"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Play command
    play_parser = subparsers.add_parser("play", help="Play through commit history interactively")
    add_arguments(play_parser)
    play_parser.set_defaults(func=cmd_play)

    # Duel command
    duel_parser = subparsers.add_parser("duel", help="Play a duel between two branches")
    add_arguments(duel_parser)
    duel_parser.add_argument("--left", dest="left_branch", type=str, required=True, help="Left branch")
    duel_parser.add_argument("--right", dest="right_branch", type=str, required=True, help="Right branch")
    duel_parser.set_defaults(func=cmd_duel)

    # Export command
    export_parser = subparsers.add_parser("export", help="Export game as PGN")
    add_arguments(export_parser)
    export_parser.add_argument("-o", "--output", type=str, help="Output PGN file path")
    export_parser.set_defaults(func=cmd_export)

    # Import PGN command
    import_parser = subparsers.add_parser("import", help="Import a PGN file as a git branch")
    add_arguments(import_parser)
    import_parser.add_argument("pgn_file", type=str, help="Path to PGN file")
    import_parser.add_argument("-b", "--branch-name", type=str, default=None, help="Target branch name")
    import_parser.set_defaults(func=cmd_import_pgn)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
