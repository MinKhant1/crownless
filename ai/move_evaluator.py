from game.board import Board
from game.move import Move
from game.move_validator import legal_moves


def allowed_moves(board: Board, rules, side: str) -> list[Move]:
    moves = legal_moves(board, side)
    if rules is None:
        return moves
    allowed = []
    for move in moves:
        piece = board.piece_at(move.from_col, move.from_row)
        if piece is None:
            continue
        if rules.locks.get(piece.id, 0) > 0:
            continue
        if any(block(board, move) for block in rules.capture_blocks):
            continue
        allowed.append(move)
    return allowed


def score_move(board: Board, rules, move: Move, previous: Move | None = None, trait: str | None = None) -> dict:
    from ai.trait_evaluator import evaluate_move

    return evaluate_move(board, rules, move, previous, trait)
