import pytest
from pathlib import Path
from src.duel import BranchDuel, DuelState


def test_duel_initialization(tmp_path: Path) -> None:
    """Test that a BranchDuel can be initialized with two branches."""
    # Create a minimal git repo for testing
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    (repo_dir / "file.txt").write_text("initial content")
    from git import Repo
    repo = Repo.init(repo_dir)
    repo.index.add(["file.txt"])
    repo.index.commit("initial commit")
    # Create two branches
    repo.create_head("left")
    repo.create_head("right")
    # Initialize duel
    duel = BranchDuel(repo_dir, "left", "right")
    assert duel.left_branch == "left"
    assert duel.right_branch == "right"
    assert duel.state is None


def test_duel_state_dataclass() -> None:
    """Test that DuelState dataclass works as expected."""
    import chess
    from src.game import Game
    state = DuelState(
        left_game=Game(),
        right_game=Game(),
        left_index=0,
        right_index=0,
        current_turn=0,
        board=chess.Board(),
        merge_commit=None,
        conflict_squares=[],
    )
    assert state.left_index == 0
    assert state.current_turn == 0
    assert state.board.turn == chess.WHITE
    assert state.merge_commit is None
    assert state.conflict_squares == []
