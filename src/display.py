from __future__ import annotations

import chess

# Unicode chess piece symbols
PIECE_SYMBOLS = {
    chess.PAWN: {True: '\u2659', False: '\u265F'},
    chess.KNIGHT: {True: '\u2658', False: '\u265E'},
    chess.BISHOP: {True: '\u2657', False: '\u265D'},
    chess.ROOK: {True: '\u2656', False: '\u265C'},
    chess.QUEEN: {True: '\u2655', False: '\u265B'},
    chess.KING: {True: '\u2654', False: '\u265A'},
}

# ANSI color codes for terminal output
COLOR_RESET = '\033[0m'
COLOR_WHITE_SQUARE = '\033[48;5;250m'
COLOR_BLACK_SQUARE = '\033[48;5;240m'
COLOR_WHITE_PIECE = '\033[38;5;15m'
COLOR_BLACK_PIECE = '\033[38;5;0m'
COLOR_COORD_LABEL = '\033[38;5;8m'
COLOR_HIGHLIGHT = '\033[48;5;226m'  # yellow background
COLOR_LAST_MOVE = '\033[48;5;46m'   # green background
COLOR_LEGAL_MOVE = '\033[48;5;214m' # orange background


def get_piece_symbol(piece: chess.Piece) -> str:
    """Get the Unicode symbol for a chess piece."""
    return PIECE_SYMBOLS[piece.piece_type][piece.color]


def square_color(square: chess.Square) -> bool:
    """Return True if square is light, False if dark."""
    return (square // 8 + square % 8) % 2 == 0


def render_board(
    board: chess.Board,
    last_move: chess.Move | None = None,
    legal_moves: set[chess.Square] | None = None,
    highlight_squares: set[chess.Square] | None = None,
    show_coords: bool = True,
) -> str:
    """Render a chess board as a colored string for terminal output.

    Args:
        board: The chess board to render.
        last_move: The last move made (to highlight from/to squares).
        legal_moves: Set of squares that are legal move targets for the current side.
        highlight_squares: Additional squares to highlight (e.g., selected piece).
        show_coords: Whether to show rank/file labels.

    Returns:
        A string representation of the board with ANSI color codes.
    """
    lines = []
    
    # Determine which squares to highlight
    highlighted: set[chess.Square] = set()
    if highlight_squares:
        highlighted.update(highlight_squares)
    if legal_moves:
        highlighted.update(legal_moves)
    if last_move:
        highlighted.add(last_move.from_square)
        highlighted.add(last_move.to_square)
    
    # Build the board row by row (rank 8 to rank 1)
    for rank in range(7, -1, -1):
        row_parts = []
        if show_coords:
            row_parts.append(f"{COLOR_COORD_LABEL}{rank + 1} {COLOR_RESET}")
        for file in range(8):
            square = rank * 8 + file
            piece = board.piece_at(square)
            is_light = square_color(square)
            
            # Determine background color
            if square in highlighted:
                if square == last_move.from_square or square == last_move.to_square:
                    bg = COLOR_LAST_MOVE
                elif legal_moves and square in legal_moves:
                    bg = COLOR_LEGAL_MOVE
                else:
                    bg = COLOR_HIGHLIGHT
            else:
                bg = COLOR_WHITE_SQUARE if is_light else COLOR_BLACK_SQUARE
            
            # Piece symbol and color
            if piece:
                piece_color = COLOR_WHITE_PIECE if piece.color == chess.WHITE else COLOR_BLACK_PIECE
                symbol = get_piece_symbol(piece)
                cell = f"{bg}{piece_color} {symbol} {COLOR_RESET}"
            else:
                cell = f"{bg}   {COLOR_RESET}"
            row_parts.append(cell)
        lines.append("".join(row_parts))
    
    if show_coords:
        file_labels = "   " + "".join(f" {chr(ord('a') + f)}  " for f in range(8))
        lines.append(f"{COLOR_COORD_LABEL}{file_labels}{COLOR_RESET}")
    
    return "\
".join(lines)


def render_move_info(
    move: chess.Move | None,
    board: chess.Board,
    move_number: int,
    turn: bool,
) -> str:
    """Render information about the current move.

    Args:
        move: The move object, or None if no move has been made.
        board: The board state after the move.
        move_number: The current move number (fullmove count).
        turn: True if it's white's turn, False for black.

    Returns:
        A string describing the move and current turn.
    """
    if move is None:
        return f"Move {move_number}: {'White' if turn else 'Black'} to move"
    
    # Get SAN notation
    board_copy = board.copy()
    board_copy.push(move)
    san = board_copy.san(move)
    
    turn_str = "White" if turn else "Black"
    return f"Move {move_number}: {turn_str} played {san}"


def render_game_status(
    board: chess.Board,
    move_number: int,
    turn: bool,
    game_over: bool = False,
    result: str | None = None,
) -> str:
    """Render the current game status line.

    Args:
        board: The current board state.
        move_number: The current move number.
        turn: True if it's white's turn, False for black.
        game_over: Whether the game has ended.
        result: The game result (e.g., "1-0", "0-1", "1/2-1/2").

    Returns:
        A string describing the game status.
    """
    if game_over:
        if result:
            return f"Game over: {result}"
        return "Game over"
    
    turn_str = "White" if turn else "Black"
    return f"Move {move_number}: {turn_str}