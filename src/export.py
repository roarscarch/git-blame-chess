from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, TextIO

import chess
import chess.pgn

from .game import Game, CommitMove
from .models import get_piece_for_path, path_to_square


def _sanitize_tag(value: str) -> str:
    """Remove problematic characters from PGN tag values."""
    return re.sub(r'[\r\n"]', ' ', value).strip()


def _build_metadata(game: Game) -> Dict[str, str]:
    """Build PGN metadata tags from the game and its repository."""
    repo = game.repo
    active_branch = repo.active_branch.name if not repo.head.is_detached else "HEAD"
    
    try:
        remote_url = repo.remotes.origin.url if repo.remotes else ""
    except Exception:
        remote_url = ""
    
    meta: Dict[str, str] = {
        "Event": "Git Blame Chess",
        "Site": _sanitize_tag(remote_url) if remote_url else str(game.repo_path.resolve()),
        "Date": datetime.now(timezone.utc).strftime("%Y.%m.%d"),
        "Round": "1",
        "White": _sanitize_tag(active_branch),
        "Black": _sanitize_tag(active_branch),  # same branch for single-branch play
        "Result": "*",  # unknown until game ends
        "Annotator": "git-blame-chess",
        "Source": f"Git repository: {_sanitize_tag(str(game.repo_path.resolve()))}",
        "Branch": _sanitize_tag(active_branch),
    }
    
    # Add commit count as a custom tag
    meta["PlyCount"] = str(len(game.moves))
    
    # If there's a starting commit, include its hash
    if game.moves:
        first_move = game.moves[0]
        meta["WhiteTeam"] = first_move.commit.hexsha[:8]
    
    return meta


def _build_move_annotation(move: CommitMove) -> str:
    """Build a commentary annotation for a commit move."""
    parts = []
    
    # Commit message (first line)
    msg = move.commit.message.split('\n')[0].strip()
    if msg:
        parts.append(msg)
    
    # Files changed
    if move.files_changed:
        files_str = ", ".join(move.files_changed[:5])  # limit to 5 files
        if len(move.files_changed) > 5:
            files_str += f" (+{len(move.files_changed) - 5} more)"
        parts.append(f"Files: {files_str}")
    
    # Author
    author = move.commit.author.name if move.commit.author else "unknown"
    parts.append(f"Author: {author}")
    
    return " | ".join(parts)


def export_pgn(game: Game, output: Optional[TextIO] = None, include_annotations: bool = True) -> str:
    """
    Export the game as a PGN string.
    
    Args:
        game: The Game instance to export.
        output: Optional file-like object to write to. If None, returns the PGN as a string.
        include_annotations: Whether to include commit annotations in braces {}