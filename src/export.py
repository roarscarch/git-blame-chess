from __future__ import annotations

import chess
import chess.pgn
from pathlib import Path
from typing import Optional, List

from .duel import DuelState
from .game import Game, CommitMove
from .models import path_to_square


def export_game_pgn(game: Game, output_path: Optional[Path] = None) -> str:
    """Export a single Game to PGN string, optionally writing to file."""
    pgn_game = chess.pgn.Game()
    pgn_game.headers["Event"] = "Git Blame Chess"
    pgn_game.headers["Site"] = str(game.repo_path)
    pgn_game.headers["Date"] = "????.??.??"
    pgn_game.headers["Round"] = "1"
    pgn_game.headers["White"] = "Commits"
    pgn_game.headers["Black"] = "Commits"
    pgn_game.headers["Result"] = "*"

    node = pgn_game
    for move_data in game.moves:
        board = chess.Board()
        node = node.add_variation(move_data.move)
        node.comment = _format_move_comment(move_data)

    pgn_str = str(pgn_game)
    if output_path:
        output_path.write_text(pgn_str)
    return pgn_str


def _format_move_comment(move_data: CommitMove) -> str:
    """Format a commit move as a PGN comment."""
    parts = []
    if move_data.commit_hash:
        parts.append(f"commit: {move_data.commit_hash[:8]}")
    if move_data.author:
        parts.append(f"author: {move_data.author}")
    if move_data.message:
        parts.append(f"message: {move_data.message}")
    if move_data.files_changed:
        parts.append(f"files: {', '.join(move_data.files_changed[:5])}")
    if move_data.lines_added:
        parts.append(f"+{move_data.lines_added}")
    if move_data.lines_deleted:
        parts.append(f"-{move_data.lines_deleted}")
    return "; ".join(parts)


def export_duel_pgn(duel: DuelState, output_path: Optional[Path] = None) -> str:
    """Export a branch duel to PGN string with branch metadata.

    The PGN will include the moves from both branches interleaved according to
    the turn order, with annotations indicating which branch each move belongs to.
    """
    pgn_game = chess.pgn.Game()
    pgn_game.headers["Event"] = "Git Blame Chess - Branch Duel"
    pgn_game.headers["Site"] = str(duel.left_game.repo_path)
    pgn_game.headers["Date"] = "????.??.??"
    pgn_game.headers["Round"] = "1"
    pgn_game.headers["White"] = f"Branch: {duel.left_game.branch}"
    pgn_game.headers["Black"] = f"Branch: {duel.right_game.branch}"
    pgn_game.headers["Result"] = "*"

    # Replay the duel moves from the saved state
    node = pgn_game
    left_game = duel.left_game
    right_game = duel.right_game
    left_idx = 0
    right_idx = 0
    turn = duel.current_turn
    board = chess.Board()

    # Determine total number of moves from each branch
    left_total = len(left_game.moves)
    right_total = len(right_game.moves)

    while left_idx < left_total or right_idx < right_total:
        if turn == 0 and left_idx < left_total:
            move_data = left_game.moves[left_idx]
            node = node.add_variation(move_data.move)
            branch_label = f"[left branch: {left_game.branch}]"
            node.comment = f"{branch_label} {_format_move_comment(move_data)}"
            left_idx += 1
            turn = 1
        elif turn == 1 and right_idx < right_total:
            move_data = right_game.moves[right_idx]
            node = node.add_variation(move_data.move)
            branch_label = f"[right branch: {right_game.branch}]"
            node.comment = f"{branch_label} {_format_move_comment(move_data)}"
            right_idx += 1
            turn = 0
        else:
            # If one branch is exhausted, continue with the other
            if left_idx < left_total:
                move_data = left_game.moves[left_idx]
                node = node.add_variation(move_data.move)
                branch_label = f"[left branch: {left_game.branch}]"
                node.comment = f"{branch_label} {_format_move_comment(move_data)}"
                left_idx += 1
            elif right_idx < right_total:
                move_data = right_game.moves[right_idx]
                node = node.add_variation(move_data.move)
                branch_label = f"[right branch: {right_game.branch}]"
                node.comment = f"{branch_label} {_format_move_comment(move_data)}