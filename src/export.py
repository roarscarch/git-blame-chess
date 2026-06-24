from __future__ import annotations

import chess
import chess.pgn
from pathlib import Path
from typing import Optional
from datetime import datetime

from .game import Game, CommitMove
from .duel import BranchDuel, DuelState
from .models import path_to_square


def export_game_to_pgn(game: Game, output_path: Optional[Path] = None) -> str:
    """Export a single-branch game to PGN format."""
    board = chess.Board()
    game_node = chess.pgn.Game()
    game_node.headers["Event"] = "Git Blame Chess - Single Branch"
    game_node.headers["Site"] = "?"
    game_node.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
    game_node.headers["Round"] = "1"
    game_node.headers["White"] = "Commit Author"
    game_node.headers["Black"] = "Commit Author"
    game_node.headers["Result"] = "*"

    current_node = game_node
    for commit_move in game.moves:
        if commit_move.move in board.legal_moves:
            board.push(commit_move.move)
            next_node = current_node.add_variation(commit_move.move)
            next_node.comment = commit_move.commit_hash[:8] if commit_move.commit_hash else ""
            current_node = next_node
        else:
            break

    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
    pgn_string = game_node.accept(exporter)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(pgn_string)

    return pgn_string


def export_duel_to_pgn(duel: BranchDuel, output_path: Optional[Path] = None) -> str:
    """Export a branch duel game to PGN format."""
    board = chess.Board()
    game_node = chess.pgn.Game()
    game_node.headers["Event"] = f"Git Blame Chess - Duel: {duel.left_branch} vs {duel.right_branch}"
    game_node.headers["Site"] = str(duel.repo.working_dir)
    game_node.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
    game_node.headers["Round"] = "1"
    game_node.headers["White"] = duel.left_branch
    game_node.headers["Black"] = duel.right_branch
    game_node.headers["Result"] = "*"

    current_node = game_node
    state = duel.state
    if state is None:
        return ""

    # Convert moves from both branches in order
    moves_played: list[tuple[chess.Move, str, int]] = []  # (move, branch_name, turn)
    left_idx = state.left_index
    right_idx = state.right_index
    turn = state.current_turn

    left_moves = state.left_game.moves
    right_moves = state.right_game.moves

    while left_idx < len(left_moves) or right_idx < len(right_moves):
        if turn == 0 and left_idx < len(left_moves):
            move = left_moves[left_idx]
            if move.move in board.legal_moves:
                moves_played.append((move.move, duel.left_branch, turn))
                board.push(move.move)
                left_idx += 1
                turn = 1
                continue
        elif turn == 1 and right_idx < len(right_moves):
            move = right_moves[right_idx]
            if move.move in board.legal_moves:
                moves_played.append((move.move, duel.right_branch, turn))
                board.push(move.move)
                right_idx += 1
                turn = 0
                continue
        break  # no more legal moves

    # Build PGN tree
    for i, (move, branch, _) in enumerate(moves_played):
        next_node = current_node.add_variation(move)
        next_node.comment = f"{branch} move {i//2 + 1}"
        current_node = next_node

    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
    pgn_string = game_node.accept(exporter)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(pgn_string)

    return pgn_string


def export_game_to_file(game: Game, output_path: Path) -> None:
    """Export game to PGN file."""
    export_game_to_pgn(game, output_path)


def export_duel_to_file(duel: BranchDuel, output_path: Path) -> None:
    """Export duel to PGN file."""
    export_duel_to_pgn(duel, output_path)