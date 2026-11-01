"""Scores one enemy move.

Castle Wall blocks and Wooden locks come from the live battle rules, read
without changing them. Chain Fuse, recruitment, conversion, and squire are
not replayed: those effects write into the running battle, so a capture is
scored on its own. Capturing a Wooden piece is treated as hanging the mover,
because the lock is applied by the live capture and is not present on the copy.
"""

from game.board import Board
from game.move import Move
from game.move_generator import attacks_of
from game.move_validator import legal_moves
from game.piece import Piece
from ai.ai_config import AI_WEIGHTS, PIECE_VALUES


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


def piece_value(piece: Piece | None) -> int:
    if piece is None:
        return 0
    return PIECE_VALUES.get(piece.kind, 0)


def priority_target(board: Board, color: str) -> Piece | None:
    found = None
    best = -1
    for piece in board.pieces:
        if piece.color != color or piece.col is None:
            continue
        value = piece_value(piece)
        if value > best:
            best = value
            found = piece
    return found


def score_move(board: Board, rules, move: Move, previous: Move | None = None) -> dict:
    weights = AI_WEIGHTS
    mover = board.piece_at(move.from_col, move.from_row)
    captured = board.piece_at(move.to_col, move.to_row)
    target = priority_target(board, "white")
    before = None if target is None else _distance((mover.col, mover.row), (target.col, target.row))
    clone = board.copy()
    clone.apply_move(move)
    capture_value = piece_value(captured) * weights["capture_multiplier"]
    hanging = _best_capture_value(clone, rules, "white")
    danger = hanging * weights["danger_multiplier"]
    if captured is not None and captured.trait == "wooden":
        danger = max(danger, piece_value(mover) * weights["danger_multiplier"])
    threat_value, threat_name = _threatened(clone, "black")
    pressure = weights["attack_pressure"] * threat_value
    access = 0
    positional = 0
    survivor = None if target is None else clone.piece_by_id(target.id)
    if survivor is not None and mover is not None:
        if _aligned(mover.kind, move.to_col, move.to_row, survivor) or _attacks(clone, "black", survivor):
            access = weights["target_access"]
        after = _distance((move.to_col, move.to_row), (survivor.col, survivor.row))
        if before is not None and after < before:
            positional = weights["positional_bonus"]
    if previous is not None and (move.from_col, move.from_row) == (previous.to_col, previous.to_row) and (move.to_col, move.to_row) == (previous.from_col, previous.from_row):
        positional -= weights["repeat_penalty"]
    total = capture_value + pressure + access + positional - danger
    return {
        "score": total,
        "capture_value": capture_value,
        "target_pressure": pressure + access,
        "positional_bonus": positional,
        "danger_penalty": danger,
        "captured_kind": None if captured is None else captured.kind,
        "threat_name": threat_name,
        "threat_value": threat_value,
        "exposed": danger > 0,
        "target": None if target is None else target.kind,
    }


def _best_capture_value(board: Board, rules, side: str) -> int:
    best = 0
    for move in allowed_moves(board, rules, side):
        target = board.piece_at(move.to_col, move.to_row)
        if target is None:
            continue
        best = max(best, piece_value(target))
    return best


def _threatened(board: Board, attacker: str) -> tuple[int, str | None]:
    best = 0
    name = None
    for piece in board.pieces:
        if piece.color == attacker or piece.col is None:
            continue
        if not _attacks(board, attacker, piece):
            continue
        value = piece_value(piece)
        if value > best:
            best = value
            name = piece.kind
    return best, name


def _attacks(board: Board, color: str, target: Piece) -> bool:
    square = (target.col, target.row)
    for piece in board.pieces:
        if piece.color != color or piece.col is None:
            continue
        if square in attacks_of(board, piece):
            return True
    return False


def _aligned(kind: str, col: int, row: int, target: Piece) -> bool:
    dc = abs(col - target.col)
    dr = abs(row - target.row)
    if dc == 0 and dr == 0:
        return False
    if kind in ("rook", "queen") and (dc == 0 or dr == 0):
        return True
    if kind in ("bishop", "queen") and dc == dr:
        return True
    if kind == "knight" and sorted((dc, dr)) == [1, 2]:
        return True
    if kind == "pawn" and dc == 1 and dr == 1:
        return True
    if kind == "king" and max(dc, dr) == 1:
        return True
    return False


def _distance(origin: tuple[int, int], dest: tuple[int, int]) -> int:
    return max(abs(origin[0] - dest[0]), abs(origin[1] - dest[1]))
