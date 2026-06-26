"""Import PGN files into git-blame-chess games."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import chess
import chess.pgn

from .game import Game, CommitMove
from .models import piece_to_extension, square_to_path


def import_pgn(file_path: Path) -> Game:
    """
    Import a PGN file and reconstruct a Game object.

    The PGN must contain specific tags that store git metadata:
    - GitRepo: path to the repository
    - GitBranch: branch name
    - GitCommit: list of commit hashes (space-separated)
    - GitAuthor: list of author names (space-separated)
    - GitTimestamp: list of UNIX timestamps (space-separated)

    Each move in the PGN corresponds to a CommitMove with the corresponding
    commit metadata from these tags. The board is reconstructed by replaying
    all moves.

    Args:
        file_path: Path to the PGN file.

    Returns:
        A Game object with all commits and moves replayed.

    Raises:
        ValueError: If the PGN is malformed or missing required tags.
    """
    with open(file_path, "r") as f:
        game_node = chess.pgn.read_game(f)
    if game_node is None:
        raise ValueError("Empty or invalid PGN file")

    headers = game_node.headers
    # Extract git metadata from headers
    repo_path = headers.get("GitRepo", "")
    branch = headers.get("GitBranch", "main")
    commit_hashes_str = headers.get("GitCommit", "")
    authors_str = headers.get("GitAuthor", "")
    timestamps_str = headers.get("GitTimestamp", "")

    commit_hashes = commit_hashes_str.split() if commit_hashes_str else []
    authors = authors_str.split() if authors_str else []
    timestamps = [int(ts) for ts in timestamps_str.split() if timestamps_str]

    # Build the list of commits from the PGN headers
    commits: List[CommitMove] = []
    # Validate that the number of moves matches the number of commits
    num_moves = sum(1 for _ in game_node.mainline_moves())
    if num_moves == 0:
        raise ValueError("PGN contains no moves")
    if num_moves != len(commit_hashes):
        raise ValueError(
            f"Mismatch between number of moves ({num_moves}) and number of commit hashes ({len(commit_hashes)})"
        )

    # Replay moves to reconstruct commit moves
    board = chess.Board()
    move_index = 0
    for node in game_node.mainline():
        move = node.move
        if move is None:
            break
        # Validate the move is legal on the current board
        if move not in board.legal_moves:
            raise ValueError(f"Illegal move {move.uci()} at move {move_index + 1}")
        board.push(move)
        commit_hash = commit_hashes[move_index] if move_index < len(commit_hashes) else ""
        author = authors[move_index] if move_index < len(authors) else ""
        timestamp = timestamps[move_index] if move_index < len(timestamps) else 0
        # Determine file path from move (reversing the piece-to-extension mapping)
        # In a real implementation, the move's square could encode the file path.
        # For now, we store the move as-is and reconstruct later.
        file_path_str = ""
        # Attempt to parse comment for file path
        if node.comment:
            # Look for a comment like "file: path/to/file.py"
            match = re.search(r'file:\s*(\S+)', node.comment)
            if match:
                file_path_str = match.group(1)
        commit_move = CommitMove(
            commit_hash=commit_hash,
            author=author,
            timestamp=timestamp,
            move=move,
            file_path=file_path_str,
        )
        commits.append(commit_move)
        move_index += 1

    # Create Game object with the reconstructed commits
    # We need to pass the board state after each move; but Game expects a list of commits.
    # The Game constructor should accept a list of CommitMove and reconstruct the board.
    game = Game(repo_path=Path(repo_path) if repo_path else Path("."), branch=branch)
    game.commits = commits
    # Replay all moves to set the board
    game.board = chess.Board()
    for cm in commits:
        if cm.move not in game.board.legal_moves:
            raise ValueError(f"Illegal move {cm.move.uci()} during replay")
        game.board.push(cm.move)
    return game


def validate_pgn(file_path: Path) -> Tuple[bool, str]:
    """
    Validate a PGN file for import.

    Checks:
    - File exists and is readable
    - PGN is well-formed
    - Contains required git tags
    - Number of moves matches number of commits
    - All moves are legal on the reconstructed board

    Args:
        file_path: Path to the PGN file.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not file_path.exists():
        return False, f"File not found: {file_path}"
    if not file_path.is_file():
        return False, f"Not a file: {file_path}"

    try:
        with open(file_path, "r") as f:
            game_node = chess.pgn.read_game(f)
        if game_node is None:
            return False, "Empty or invalid PGN file"

        headers = game_node.headers
        required_tags = ["GitRepo", "GitBranch", "GitCommit", "GitAuthor", "GitTimestamp"]
        missing_tags = [tag for tag in required_tags if tag not in headers]
        if missing_tags:
            return False, f"Missing required tags: {', '.join(missing_tags)}"

        # Validate move count matches commit count
        commit_hashes_str = headers.get("GitCommit", "")
        commit_hashes = commit_hashes_str.split() if commit_hashes_str else []
        num_moves = sum(1 for _ in game_node.mainline_moves())
        if num_moves != len(commit_hashes):
            return False, f"Number of moves ({num_moves}) does not match number of commit hashes ({len(commit_hashes)})"

        # Replay moves to validate legality
        board = chess.Board()
        for node in game_node.mainline():
            move = node.move
            if move is None:
                break
            if move not in board.legal_moves:
                return False, f"Illegal move {move.uci()}