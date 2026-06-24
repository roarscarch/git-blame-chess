from __future__ import annotations

import io
from typing import List, Optional, TextIO

import chess
import chess.pgn

from .game import Game, CommitMove


def export_game(game: Game, file: Optional[TextIO] = None) -> str:
    """Export a Game to PGN format.

    Args:
        game: The Game to export.
        file: Optional file-like object to write the PGN to.

    Returns:
        The PGN string.
    """
    pgn_game = chess.pgn.Game()
    pgn_game.headers["Event"] = "Git Blame Chess"
    pgn_game.headers["Site"] = "?"
    pgn_game.headers["Date"] = "????.??.??"
    pgn_game.headers["Round"] = "1"
    pgn_game.headers["White"] = _determine_side(game.moves, chess.WHITE)
    pgn_game.headers["Black"] = _determine_side(game.moves, chess.BLACK)
    pgn_game.headers["Result"] = "*"

    node = pgn_game
    for i, commit_move in enumerate(game.moves):
        move = commit_move.move
        if move is None:
            continue
        node = node.add_variation(move)
        # Add comment with commit info
        comment = _format_comment(commit_move)
        if comment:
            node.comment = comment

    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
    pgn_str = pgn_game.accept(exporter)

    if file is not None:
        file.write(pgn_str)

    return pgn_str


def export_duel_moves(moves: List[CommitMove], file: Optional[TextIO] = None) -> str:
    """Export a list of CommitMove objects to PGN format.

    This is used for duel mode where moves come from two branches.

    Args:
        moves: List of CommitMove objects.
        file: Optional file-like object to write the PGN to.

    Returns:
        The PGN string.
    """
    pgn_game = chess.pgn.Game()
    pgn_game.headers["Event"] = "Git Blame Chess Duel"
    pgn_game.headers["Site"] = "?"
    pgn_game.headers["Date"] = "????.??.??"
    pgn_game.headers["Round"] = "1"
    pgn_game.headers["White"] = "Branch Left"
    pgn_game.headers["Black"] = "Branch Right"
    pgn_game.headers["Result"] = "*"

    node = pgn_game
    for i, commit_move in enumerate(moves):
        move = commit_move.move
        if move is None:
            continue
        node = node.add_variation(move)
        comment = _format_comment(commit_move)
        if comment:
            node.comment = comment

    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
    pgn_str = pgn_game.accept(exporter)

    if file is not None:
        file.write(pgn_str)

    return pgn_str


def _determine_side(moves: List[CommitMove], color: chess.Color) -> str:
    """Determine a side name from the commit authors.

    Uses the first move of the given color to find the author.
    """
    for cm in moves:
        if cm.move is not None:
            # Simple: use the author of the first commit for that side
            # In practice, all moves of a color come from the same branch
            return cm.author or f"Side {color}"
    return f"Side {color}"


def _format_comment(commit_move: CommitMove) -> str:
    """Format a commit move as a PGN comment."""
    parts = []
    if commit_move.hexsha:
        parts.append(f"commit: {commit_move.hexsha[:7]}")
    if commit_move.author:
        parts.append(f"author: {commit_move.author}")
    if commit_move.message:
        # Truncate long messages
        msg = commit_move.message.replace('\n', ' ').strip()
        if len(msg) > 80:
            msg = msg[:77] + "..."
        parts.append(f"message: {msg}")
    if commit_move.files_changed:
        files_str = ", ".join(commit_move.files_changed[:5])
        if len(commit_move.files_changed) > 5:
            files_str += f" (+{len(commit_move.files_changed) - 5} more)"
        parts.append(f"files: {files_str}