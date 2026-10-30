from dataclasses import dataclass


@dataclass
class StatusEffect:
    status_id: str
    remaining_owner_turns: int
    source_trait: str


class BattleRules:
    def __init__(self) -> None:
        self.locks: dict[int, int] = {}
        self.fresh: set[int] = set()
        self.statuses: dict[int, StatusEffect] = {}
        self.capture_blocks: list = []
        self._board = lambda: None

    def bind(self, board_getter) -> None:
        self._board = board_getter

    def lock(self, piece_id: int, turns: int = 2) -> None:
        self.locks[piece_id] = max(self.locks.get(piece_id, 0), turns)
        self.fresh.add(piece_id)
        self.statuses[piece_id] = StatusEffect("immobilized", self.locks[piece_id], "wooden")

    def clear(self, piece_id: int) -> None:
        self.locks.pop(piece_id, None)
        self.fresh.discard(piece_id)
        self.statuses.pop(piece_id, None)

    def filter_moves(self, board, moves):
        self._drop_missing(board)
        allowed = []
        for move in moves:
            piece = board.piece_at(move.from_col, move.from_row)
            if piece is None:
                continue
            if self.locks.get(piece.id, 0) > 0:
                continue
            if any(block(board, move) for block in self.capture_blocks):
                continue
            allowed.append(move)
        return allowed

    def spend(self, side: str) -> None:
        board = self._board()
        if board is None:
            return
        self._drop_missing(board)
        for piece in list(board.pieces):
            if piece.color != side:
                continue
            if piece.id in self.fresh:
                self.fresh.discard(piece.id)
                continue
            remaining = self.locks.get(piece.id, 0)
            if remaining <= 0:
                continue
            remaining -= 1
            self.locks[piece.id] = remaining
            if remaining <= 0:
                self.statuses.pop(piece.id, None)
                continue
            status = self.statuses.get(piece.id)
            if status is not None:
                status.remaining_owner_turns = remaining

    def _drop_missing(self, board) -> None:
        if board is None:
            return
        live = {piece.id for piece in board.pieces}
        for piece_id in list(self.statuses):
            if piece_id not in live:
                self.clear(piece_id)
