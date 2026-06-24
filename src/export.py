from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import chess
import chess.pgn

from .game import Game, CommitMove
from .duel import BranchDuel, DuelState


def export_game_to_pgn(game: Game, output_path: Optional[Path] = None) -> str:
    """Export a single-branch game to PGN format."""
    game_node = chess.pgn.Game()
    game_node.headers["Event"] = "Git Blame Chess - Single Branch"
    game_node.headers["Site"] = str(game.repo_path)
    game_node.headers["Date"] = "????.??.??"
    game_node.headers["Round"] = "1"
    game_node.headers["White"] = game.branch or "main"
    game_node.headers["Black"] = "History"
    game_node.headers["Result"] = "*"

    current_node = game_node
    for move in game.moves:
        if move.uci is None:
            continue
        try:
            chess_move = chess.Move.from_uci(move.uci)
            if chess_move in game.board.legal_moves:
                game.board.push(chess_move)
                current_node = current_node.add_variation(chess_move)
                current_node.comment = f"Commit: {move.commit_hash[:8]} - {move.message.split(chr(10))[0]}"
        except (ValueError, chess.InvalidMoveError):
            continue

    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
    pgn_str = game_node.accept(exporter)

    if output_path:
        output_path.write_text(pgn_str)
    return pgn_str


def export_duel_to_pgn(duel: BranchDuel, output_path: Optional[Path] = None) -> str:
    """Export a branch duel to PGN format, tracking board state.

    The duel alternates between left and right branches. Each move is annotated
    with its branch and commit hash. Merge commits reset to common ancestor.
    """
    if duel.state is None:
        duel.initialize()

    state = duel.state
    game_node = chess.pgn.Game()
    game_node.headers["Event"] = "Git Blame Chess - Branch Duel"
    game_node.headers["Site"] = str(duel.repo.working_dir)
    game_node.headers["Date"] = "????.??.??"
    game_node.headers["Round"] = "1"
    game_node.headers["White"] = duel.left_branch
    game_node.headers["Black"] = duel.right_branch
    game_node.headers["Result"] = "*"

    current_node = game_node
    board = chess.Board()

    # Simulate the duel turn by turn
    left_idx = 0
    right_idx = 0
    turn = 0  # 0 = left, 1 = right

    left_moves = state.left_game.moves
    right_moves = state.right_game.moves

    while left_idx < len(left_moves) or right_idx < len(right_moves):
        if turn == 0:
            if left_idx >= len(left_moves):
                break
            move = left_moves[left_idx]
            left_idx += 1
            player = duel.left_branch
        else:
            if right_idx >= len(right_moves):
                break
            move = right_moves[right_idx]
            right_idx += 1
            player = duel.right_branch

        if move.uci is None:
            turn = 1 - turn
            continue

        try:
            chess_move = chess.Move.from_uci(move.uci)
            if chess_move in board.legal_moves:
                board.push(chess_move)
                current_node = current_node.add_variation(chess_move)
                current_node.comment = (
                    f"{player} | Commit: {move.commit_hash[:8]} - {move.message.split(chr(10))[0]}