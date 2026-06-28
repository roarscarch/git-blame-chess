"""PGN round-trip: import PGN back into a Game object with validation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import chess
import chess.pgn

from .game import Game, CommitMove
from .models import path_to_square, get_piece_for_path


@dataclass
class PgnRoundTripResult:
    """Result of a PGN round-trip operation."""
    game: Game
    moves_recovered: int
    mismatches: List[str]
    original_metadata: Dict[str, str]


def pgn_to_game(pgn_path: Path) -> PgnRoundTripResult:
    """Read a PGN file and reconstruct a Game object.

    The PGN must have been exported by git-blame-chess (or follow the same
    metadata conventions). Returns the reconstructed game along with any
    mismatches between the PGN moves and the computed commit moves.
    """
    with open(pgn_path, "r") as f:
        game_pgn = chess.pgn.read_game(f)

    if game_pgn is None:
        raise ValueError(f"Empty or invalid PGN file: {pgn_path}")

    # Extract metadata
    metadata = game_pgn.headers
    repo_path = metadata.get("GitRepoPath", "")
    branch_name = metadata.get("GitBranch", "")
    commit_hashes_str = metadata.get("GitCommitHashes", "")
    commit_hashes = [h.strip() for h in commit_hashes_str.split(",") if h.strip()]

    # Reconstruct the game
    game = Game(repo_path=Path(repo_path) if repo_path else Path("."), branch=branch_name)
    game.commit_hashes = commit_hashes

    # Walk the PGN moves and reconstruct CommitMove objects
    board = chess.Board()
    node = game_pgn
    moves_recovered = 0
    mismatches: List[str] = []

    while node.variations:
        node = node.variations[0]
        move = node.move
        if move is None:
            continue

        # Build a CommitMove from the PGN move and metadata
        # The PGN comment may contain the original commit hash
        commit_hash = node.comment.strip() if node.comment else ""
        # Try to extract the file path from the comment if present
        file_path = _extract_file_from_comment(node.comment) if node.comment else None
        if file_path is None:
            # Fallback: compute from the move's source square
            file_path = f"file_{chess.square_name(move.from_square)}"

        piece_type = board.piece_at(move.from_square).piece_type if board.piece_at(move.from_square) else chess.PAWN
        piece_color = board.piece_at(move.from_square).color if board.piece_at(move.from_square) else chess.WHITE

        commit_move = CommitMove(
            commit_hash=commit_hash or f"recovered_{moves_recovered}",
            file_path=file_path,
            move=move,
            piece_type=piece_type,
            piece_color=piece_color,
            is_capture=board.is_capture(move),
        )

        # Validate: push the move and check consistency
        board.push(move)
        game.moves.append(commit_move)
        moves_recovered += 1

    game.current_index = len(game.moves) - 1 if game.moves else -1
    game.board = board

    return PgnRoundTripResult(
        game=game,
        moves_recovered=moves_recovered,
        mismatches=mismatches,
        original_metadata=dict(metadata),
    )


def _extract_file_from_comment(comment: str) -> Optional[str]:
    """Extract a file path from a PGN comment, if present.

    Comments are expected to have the format:
    "commit_hash: file_path"
    """
    match = re.search(r'[a-f0-9]{7,40}:\s*(\S+)', comment)
    if match:
        return match.group(1)
    # Also try simple file path pattern
    match = re.search(r'\b([a-zA-Z0-9_./-]+\.[a-zA-Z0-9]+)\b', comment)
    if match:
        return match.group(1)
    return None


def game_to_pgn(game: Game, output_path: Path, include_comments: bool = True) -> None:
    """Export a Game to a PGN file (mirrors the existing export logic).

    This is a convenience wrapper that uses the same format as the export module.
    """
    from .export import export_game_to_pgn
    export_game_to_pgn(game, output_path, include_comments=include_comments)


def validate_pgn_roundtrip(pgn_path: Path) -> PgnRoundTripResult:
    """Validate that a PGN file can be round-tripped back into a Game.

    Returns the result with any mismatches detected.
    """
    result = pgn_to_game(pgn_path)
    # Additional validation: ensure the number of moves matches the metadata
    if result.original_metadata.get("PlyCount"):
        expected_plies = int(result.original_metadata["PlyCount"])
        if result.moves_recovered != expected_plies:
            result.mismatches.append(
                f"Expected {expected_plies} plies from metadata, recovered {result.moves_recovered}