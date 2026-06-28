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
) -> str:
    """Render a chess board with colored squares and pieces.

    Args:
        board: The chess board to render.
        last_move: The last move made, to highlight from/to squares.
        legal_moves: Set of squares that are legal move targets.
        highlight_squares: Additional squares to highlight.

    Returns:
        A string with ANSI color codes for terminal display.
    """
    lines: list[str] = []
    # Build a set of squares to highlight
    highlight: set[chess.Square] = set()
    if last_move:
        highlight.add(last_move.from_square)
        highlight.add(last_move.to_square)
    if legal_moves:
        highlight.update(legal_moves)
    if highlight_squares:
        highlight.update(highlight_squares)

    # File labels at top
    file_labels = '  ' + ''.join(f' {chr(ord("a") + f)} ' for f in range(8))
    lines.append(COLOR_COORD_LABEL + file_labels + COLOR_RESET)

    for rank in range(7, -1, -1):  # rank 8 to 1
        row_parts: list[str] = []
        # Rank label
        row_parts.append(f'{COLOR_COORD_LABEL}{rank + 1} {COLOR_RESET}')
        for file in range(8):
            square = chess.square(file, rank)
            piece = board.piece_at(square)
            is_light = square_color(square)
            # Determine background color
            if square in highlight:
                bg = COLOR_LAST_MOVE if (last_move and square in (last_move.from_square, last_move.to_square)) else COLOR_HIGHLIGHT
            elif is_light:
                bg = COLOR_WHITE_SQUARE
            else:
                bg = COLOR_BLACK_SQUARE

            # Piece symbol
            if piece:
                fg = COLOR_WHITE_PIECE if piece.color == chess.WHITE else COLOR_BLACK_PIECE
                symbol = get_piece_symbol(piece)
                row_parts.append(f'{bg}{fg} {symbol} {COLOR_RESET}')
            else:
                # Empty square: show a dot or space
                row_parts.append(f'{bg}   {COLOR_RESET}')
        lines.append(''.join(row_parts) + f'{COLOR_COORD_LABEL} {rank + 1}{COLOR_RESET}')

    # File labels at bottom
    lines.append(COLOR_COORD_LABEL + file_labels + COLOR_RESET)
    return '\n'.join(lines)


def render_move_history(moves: list[str], max_lines: int = 10) -> str:
    """Render a compact move history list.

    Args:
        moves: List of move strings in algebraic notation.
        max_lines: Maximum number of lines to show (oldest moves are trimmed).

    Returns:
        A string showing the move history.
    """
    if not moves:
        return '  (no moves played yet)'

    # Format moves in pairs: 1. e4 e5 2. Nf3 ...
    numbered: list[str] = []
    i = 0
    while i < len(moves):
        move_num = (i // 2) + 1
        if i % 2 == 0:
            line = f'{move_num:>3}. {moves[i]}'
        else:
            line = f'      {moves[i]}'
        numbered.append(line)
        i += 1

    # Show last max_lines moves
    if len(numbered) > max_lines:
        truncated = numbered[-max_lines:]
        truncated.insert(0, f'  ... ({len(numbered) - max_lines} more moves)')
        return '\n'.join(truncated)
    else:
        return '\n'.join(numbered)


def render_turn_indicator(board: chess.Board, player_name: str = '') -> str:
    """Render a turn indicator showing whose turn it is.

    Args:
        board: The chess board.
        player_name: Optional player name to display.

    Returns:
        A string indicating the current turn.
    """
    turn_str = 'White' if board.turn == chess.WHITE else 'Black'
    if player_name:
        return f'{turn_str} to move ({player_name})'
    return f'{turn_sz} to move'