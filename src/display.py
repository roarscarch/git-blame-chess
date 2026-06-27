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
    """Render a chess board as a colored string for terminal output.

    Args:
        board: The chess board to render.
        last_move: The last move played (to highlight from/to squares).
        legal_moves: Set of squares that are legal move destinations.
        highlight_squares: Additional squares to highlight (e.g., selected piece).

    Returns:
        A string with ANSI color codes suitable for printing.
    """
    if highlight_squares is None:
        highlight_squares = set()
    if legal_moves is None:
        legal_moves = set()

    lines: list[str] = []
    # Top coordinate label
    lines.append('  ' + ' '.join(f'{COLOR_COORD_LABEL}{chr(ord("a") + col)}{COLOR_RESET}' for col in range(8)))

    for row in range(7, -1, -1):
        line_parts: list[str] = []
        # Row label
        line_parts.append(f'{COLOR_COORD_LABEL}{row + 1}{COLOR_RESET}')

        for col in range(8):
            square = chess.square(col, row)
            piece = board.piece_at(square)

            # Determine background color
            if square in highlight_squares:
                bg = COLOR_HIGHLIGHT
            elif last_move and (square == last_move.from_square or square == last_move.to_square):
                bg = COLOR_LAST_MOVE
            elif square in legal_moves:
                bg = COLOR_LEGAL_MOVE
            elif square_color(square):
                bg = COLOR_WHITE_SQUARE
            else:
                bg = COLOR_BLACK_SQUARE

            # Determine piece color
            if piece:
                if piece.color == chess.WHITE:
                    fg = COLOR_WHITE_PIECE
                else:
                    fg = COLOR_BLACK_PIECE
                symbol = get_piece_symbol(piece)
            else:
                fg = ''
                symbol = ' '

            line_parts.append(f'{bg}{fg} {symbol} {COLOR_RESET}')

        lines.append(''.join(line_parts))

    # Bottom coordinate label
    lines.append('  ' + ' '.join(f'{COLOR_COORD_LABEL}{chr(ord("a") + col)}{COLOR_RESET}' for col in range(8)))

    return '\n'.join(lines)


def render_move(move: chess.Move, board: chess.Board, san: bool = True) -> str:
    """Render a chess move in SAN notation or UCI."""
    if san:
        try:
            return board.san(move)
        except ValueError:
            return move.uci()
    return move.uci()


def print_board(
    board: chess.Board,
    last_move: chess.Move | None = None,
    legal_moves: set[chess.Square] | None = None,
    highlight_squares: set[chess.Square] | None = None,
) -> None:
    """Print a colored board to the terminal."""
    print(render_board(board, last_move, legal_moves, highlight_squares))


def print_game_status(board: chess.Board) -> None:
    """Print the current game status (check, checkmate, stalemate, etc.)."""
    if board.is_checkmate():
        winner = 'White' if board.turn == chess.BLACK else 'Black'
        print(f'Checkmate! {winner} wins.')
    elif board.is_stalemate():
        print('Stalemate! The game is a draw.')
    elif board.is_insufficient_material():
        print('Draw due to insufficient material.')
    elif board.is_check():
        print('Check!')
    else:
        print(f"Turn: {'White' if board.turn == chess.WHITE else 'Black'}")


def render_move_history(moves: list[chess.Move], board: chess.Board) -> str:
    """Render the move history in algebraic notation.

    Args:
        moves: List of moves played.
        board: The board to use for SAN generation.

    Returns:
        A string with move numbers and SAN notation.
    """
    lines: list[str] = []
    temp_board = board.copy()
    temp_board.clear()
    # We need to replay moves on a fresh board to get correct SAN
    # Actually, we'll just use the provided board which is assumed to be at the start
    # Better: replay from initial position
    replay_board = chess.Board()
    move_number = 1
    line = ''
    for i, move in enumerate(moves):
        try:
            san = replay_board.san(move)
        except ValueError:
            san = move.uci()
        replay_board.push(move)
        if i % 2 == 0:
            line = f'{move_number}. {san}'
            if i == len(moves) - 1:
                lines.append(line)
        else:
            line += f' {san}'
            lines.append(line)
            move_number += 1
            line = ''
    if line:
        lines.append(line)
    return '\n'.join(lines)
