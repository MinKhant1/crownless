"""Personality scores for one legal enemy move.

Castle Wall blocks and Wooden locks are read from the live rules. Chain Fuse,
recruitment, conversion, and squire are not replayed, because those effects
write into the running battle. Capturing a Wooden piece is treated as hanging
the mover, since the lock is applied on the live capture and is not on the copy.
"""

from game.move_generator import attacks_of
from ai.trait_definitions import HUNTER, VENGEFUL, HUNT_VALUES, WIN_CAPTURE, weights_for
from ai.move_evaluator import allowed_moves


def evaluate_move(board, rules, move, previous=None, trait=None) -> dict:
    mover = board.piece_at(move.from_col, move.from_row)
    captured = board.piece_at(move.to_col, move.to_row)
    revenge = _revenge_target(board)
    if trait is None:
        trait = None if mover is None else mover.ai_trait
    weights = weights_for(trait, revenge is not None and trait == VENGEFUL)
    focus = revenge if trait == VENGEFUL and revenge is not None else _priority_piece(board)
    before = _threatened_value(board, "black")
    clone = board.copy()
    clone.apply_move(move)
    after = _threatened_value(clone, "black")
    attacked = _attacked_pieces(clone, "black")
    hanging = _best_capture_value(clone, rules, "white")
    gain = 0 if captured is None else _value(captured)
    if captured is not None and captured.trait == "wooden" and mover is not None:
        hanging = max(hanging, _value(mover))
    risk = min(1.0, max(0, hanging - gain) / 12.0)
    if after > before:
        risk = max(risk, min(1.0, (after - before) / 12.0))
    defense = 0.0 if after >= before else min(1.0, (before - after) / 9.0)
    capture = 0.0 if captured is None else (1.0 if captured.kind == "king" else min(1.0, gain / 9.0))
    threat = _threat_component(attacked)
    target = _target_component(board, clone, mover, move, captured, focus, trait)
    position = -1.0 if _reversed(move, previous) else 0.0
    raw = (
        capture * weights.capture
        + threat * weights.threat
        + defense * weights.defense
        + target * weights.target
        + position * weights.position
        - risk * weights.risk
    )
    win = WIN_CAPTURE if captured is not None and captured.kind == "king" else 0
    score = int(round(100.0 * raw / weights.scale() + win))
    return {
        "score": score,
        "capture_value": int(round(100.0 * capture * weights.capture / weights.scale())),
        "target_pressure": int(round(100.0 * (threat * weights.threat + target * weights.target) / weights.scale())),
        "positional_bonus": int(round(100.0 * position * weights.position / weights.scale())),
        "danger_penalty": int(round(100.0 * risk * weights.risk / weights.scale())),
        "captured_kind": None if captured is None else captured.kind,
        "threat_name": None if not attacked else max(attacked, key=_value).kind,
        "threat_value": 0 if not attacked else max(_value(piece) for piece in attacked),
        "exposed": risk > 0,
        "target": None if focus is None else focus.kind,
        "personality": trait or HUNTER,
    }


def _value(piece) -> int:
    if piece is None:
        return 0
    return HUNT_VALUES.get(piece.kind, 0)


def _priority_piece(board):
    found = None
    best = -1
    for piece in board.pieces:
        if piece.color != "white" or piece.col is None:
            continue
        value = _value(piece)
        if value > best:
            best = value
            found = piece
    return found


def _revenge_target(board):
    log = getattr(board, "capture_log", ())
    for record in reversed(log):
        victim = record.piece
        if victim.color != "black":
            continue
        capturer = board.piece_by_id(record.capturer_id)
        if capturer is not None and capturer.color == "white" and capturer.col is not None:
            return capturer
    return None


def _threatened_value(board, side: str) -> int:
    opponent = "white" if side == "black" else "black"
    best = 0
    for piece in board.pieces:
        if piece.color != side or piece.col is None:
            continue
        if _attacked_by(board, opponent, piece):
            best = max(best, _value(piece))
    return best


def _attacked_pieces(board, attacker: str) -> list:
    found = []
    for piece in board.pieces:
        if piece.color == attacker or piece.col is None:
            continue
        if _attacked_by(board, attacker, piece):
            found.append(piece)
    return found


def _attacked_by(board, color: str, target) -> bool:
    square = (target.col, target.row)
    for piece in board.pieces:
        if piece.color != color or piece.col is None:
            continue
        if square in attacks_of(board, piece):
            return True
    return False


def _threat_component(attacked: list) -> float:
    if not attacked:
        return 0.0
    best = max(_value(piece) for piece in attacked)
    extra = min(3, len(attacked) - 1)
    return min(1.0, 0.35 * best / 9.0 + 0.22 * extra)


def _target_component(board, clone, mover, move, captured, focus, trait) -> float:
    if focus is None or mover is None:
        return 0.0
    if captured is not None and captured.id == focus.id:
        return 1.0
    survivor = clone.piece_by_id(focus.id)
    if survivor is not None and _attacked_by(clone, "black", survivor):
        return 1.0
    if survivor is not None and _aligned(mover.kind, move.to_col, move.to_row, survivor):
        return 0.45
    if trait in (HUNTER, VENGEFUL) and survivor is not None:
        before = _distance((mover.col, mover.row), (focus.col, focus.row))
        after = _distance((move.to_col, move.to_row), (survivor.col, survivor.row))
        if after < before:
            return 0.2
    return 0.0


def _aligned(kind: str, col: int, row: int, target) -> bool:
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


def _best_capture_value(board, rules, side: str) -> int:
    best = 0
    for move in allowed_moves(board, rules, side):
        target = board.piece_at(move.to_col, move.to_row)
        if target is None:
            continue
        best = max(best, _value(target))
    return best


def _reversed(move, previous) -> bool:
    if previous is None:
        return False
    return (move.from_col, move.from_row) == (previous.to_col, previous.to_row) and (move.to_col, move.to_row) == (previous.from_col, previous.from_row)


def _distance(origin: tuple[int, int], dest: tuple[int, int]) -> int:
    return max(abs(origin[0] - dest[0]), abs(origin[1] - dest[1]))
