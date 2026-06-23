from __future__ import annotations

import chess
import chess.pgn
from pathlib import Path
from typing import List, Optional, Tuple

from .game import Game, CommitMove
from .models import path_to_square, get_piece_for_path


def import_pgn(pgn_path: Path, repo_path: Optional[Path] = None) -> Tuple[Game, List[str]]:
    """
    Import a PGN file and reconstruct a Game object along with the list of
    commit hashes (as strings) that were associated with each move.

    The PGN must have been exported by git-blame-chess (or follow the same
    convention), where each move's comment contains the commit hash and
    file information.

    Args:
        pgn_path: Path to the PGN file.
        repo_path: Optional path to the git repository (for metadata).

    Returns:
        A tuple (game, commit_hashes) where game is a Game instance with
        moves populated from the PGN, and commit_hashes is a list of the
        original commit hashes (one per move).

    Raises:
        ValueError: If the PGN file cannot be parsed or is malformed.
    """
    with open(pgn_path, "r") as f:
        pgn_text = f.read()

    pgn_game = chess.pgn.read_game(pgn_text)
    if pgn_game is None:
        raise ValueError(f"Could not parse PGN file: {pgn_path}")

    # Extract headers
    event = pgn_game.headers.get("Event", "").replace("Git Blame Chess - ", "")
    site = pgn_game.headers.get("Site", "")
    white = pgn_game.headers.get("White", "Unknown")
    black = pgn_game.headers.get("Black", "Unknown")
    result = pgn_game.headers.get("Result", "*")

    # Determine branch name from event header
    branch = event if event else "imported"

    # Determine repo path
    if repo_path is None:
        repo_path = Path(site) if site else Path.cwd()

    # Create Game object
    game = Game(
        repo_path=repo_path,
        branch=branch,
        repo=None,  # Not needed for imported game
    )

    # Walk through moves
    commit_hashes: List[str] = []
    node = pgn_game
    while node.variations:
        node = node.variations[0]
        move = node.move
        comment = node.comment

        # Parse the comment to extract commit hash and file info
        # Expected format: "commit <hash> | <file_path>"
        commit_hash = ""
        file_path = ""
        if comment:
            # Try to extract commit hash
            for part in comment.split("|"):
                part = part.strip()
                if part.startswith("commit "):
                    commit_hash = part[7:].strip()
                else:
                    file_path = part.strip()

        commit_hashes.append(commit_hash)

        # Determine piece and square from the move
        # We need to reconstruct the CommitMove from the board state
        # This is an approximation: we use the destination square of the move
        # and try to map it back to a file path.
        # For a perfect reconstruction, we would need the original game's
        # metadata. Here we create a placeholder CommitMove.
        cm = CommitMove(
            commit_hash=commit_hash or f"imported-{len(game.moves)}",
            author=white if len(game.moves) % 2 == 0 else black,
            timestamp="",
            message="Imported from PGN",
            files_changed=[file_path] if file_path else [],
            piece=get_piece_for_path(file_path) if file_path else chess.PAWN,
            from_square=move.from_square if move else chess.E1,
            to_square=move.to_square if move else chess.E1,
            piece_color=chess.WHITE if len(game.moves) % 2 == 0 else chess.BLACK,
        )
        game.moves.append(cm)

    return game, commit_hashes
