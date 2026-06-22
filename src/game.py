from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import chess
from git import Repo

from .models import EXTENSION_PIECE_MAP, DEFAULT_PIECE, get_piece_for_path, path_to_square


@dataclass
class CommitMove:
    """A chess move derived from a single commit."""
    commit_hash: str
    author: str
    message: str
    move: chess.Move
    board_before: chess.Board
    board_after: chess.Board
    files_changed: List[str]
    lines_added: int
    lines_deleted: int


@dataclass
class Game:
    """Represents the full chess game derived from a git repository."""
    repo_path: Path
    branch: str
    starting_board: chess.Board = field(default_factory=chess.Board)
    moves: List[CommitMove] = field(default_factory=list)
    current_index: int = 0

    @classmethod
    def from_repo(cls, repo_path: Path, branch: Optional[str] = None) -> Game:
        """
        Parse a git repository and return a Game object.

        Args:
            repo_path: Path to the git repository.
            branch: Branch name to parse. If None, uses the current branch.

        Returns:
            A Game instance populated with moves derived from commits.
        """
        repo = Repo(repo_path)
        if branch is None:
            branch = repo.active_branch.name

        commits = list(repo.iter_commits(branch))
        commits.reverse()  # chronological order

        board = chess.Board()
        moves: List[CommitMove] = []

        for commit in commits:
            if not commit.parents:
                continue  # skip initial commit (no diff)

            parent = commit.parents[0]
            diffs = parent.diff(commit, create_patch=True)

            # Collect file changes
            files_changed: List[str] = []
            total_added = 0
            total_deleted = 0

            for diff in diffs:
                if diff.change_type in ('A', 'M', 'R'):
                    file_path = diff.b_path if diff.b_path else diff.a_path
                    files_changed.append(file_path)
                    if diff.diff:
                        for line in diff.diff.decode('utf-8', errors='replace').split('\n'):
                            if line.startswith('+') and not line.startswith('+++'):
                                total_added += 1
                            elif line.startswith('-') and not line.startswith('---'):
                                total_deleted += 1

            if not files_changed:
                continue

            # Generate a chess move from the commit
            move = cls._commit_to_move(commit, files_changed, total_added, total_deleted, board)
            if move is None:
                continue

            board_before = board.copy()
            board.push(move)
            board_after = board.copy()

            commit_move = CommitMove(
                commit_hash=commit.hexsha,
                author=str(commit.author),
                message=commit.message.strip(),
                move=move,
                board_before=board_before,
                board_after=board_after,
                files_changed=files_changed,
                lines_added=total_added,
                lines_deleted=total_deleted,
            )
            moves.append(commit_move)

        return cls(repo_path=repo_path, branch=branch, starting_board=chess.Board(), moves=moves)

    @staticmethod
    def _commit_to_move(
        commit: object,
        files_changed: List[str],
        lines_added: int,
        lines_deleted: int,
        board: chess.Board,
    ) -> Optional[chess.Move]:
        """
        Convert a commit's diff into a chess move.

        The move is determined by:
        - The first file changed is the 'from' piece
        - The number of lines added/removed determines the target square
        - We use a deterministic hash to pick a legal move if available

        Args:
            commit: GitPython commit object (unused but kept for future extensions).
            files_changed: List of file paths that were changed.
            lines_added: Number of lines added.
            lines_deleted: Number of lines deleted.
            board: Current board state.

        Returns:
            A chess.Move if a legal move can be derived, else None.
        """
        if not files_changed:
            return None

        # Use the first changed file to determine piece type and source square
        file_path = files_changed[0]
        piece_type = get_piece_for_path(file_path)
        from_square = path_to_square(file_path)

        # Determine target square based on line changes
        # We hash the commit message and line counts to get a deterministic offset
        hash_input = f"{lines_added}-{lines_deleted}".encode()
        hash_digest = hashlib.sha256(hash_input).hexdigest()
        offset = int(hash_digest[:8], 16) % 64

        # Try to find a legal move from from_square with the given piece
        legal_moves = [m for m in board.legal_moves if m.from_square == from_square]
        if not legal_moves:
            # If no legal move from that square, try any move with the same piece type
            legal_moves = [
                m for m in board.legal_moves
                if board.piece_at(m.from_square) and board.piece_at(m.from_square).piece_type == piece_type
            ]

        if not legal_moves:
            # Fallback: any legal move
            legal_moves = list(board.legal_moves)

        if not legal_moves:
            return None

        # Pick a move deterministically
        move_index = offset % len(legal_moves)
        return legal_moves[move_index]

    def get_current_board(self) -> chess.Board:
        """Return the board state at the current move index."""
        if self.current_index == 0:
            return self.starting_board.copy()
        return self.moves[self.current_index - 1].board_after.copy()

    def go_to_move(self, index: int) -> chess.Board:
        """Jump to a specific move index (0 = starting position)."""
        if index < 0 or index > len(self.moves):
            raise IndexError(f"Move index {index} out of range (0-{len(self.moves)})")
        self.current_index = index
        return self.get_current_board()

    def next_move(self) -> Optional[CommitMove]:
        """Advance to the next move and return it, or None if at the end."""
        if self.current_index >= len(self.moves):
            return None
        move = self.moves[self.current_index]
        self.current_index += 1
        return move

    def prev_move(self) -> Optional[CommitMove]:
        """Go back one move and return the previous move, or None if at start."""
        if self.current_index <= 0:
            return None
        self.current_index -= 1
        if self.current_index == 0:
            return None
        return self.moves[self.current_index - 1]

    def reset(self) -> None:
        """Reset to the starting position."""
        self.current_index = 0