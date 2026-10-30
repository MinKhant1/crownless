from config.settings import opposite
from game.board import Board
from game.move_validator import in_check, legal_moves


class TurnManager:
    def __init__(self, starting: str = "white", mode: str = "classic", move_source=None, on_turn_end=None) -> None:
        self.current = starting
        self.mode = mode
        self.move_source = move_source
        self.on_turn_end = on_turn_end
        self.move_count = 0
        self.battle_state = "ongoing"
        self.in_check = False
        self.finished = False
        self.winner: str | None = None

    def _moves(self, board: Board, side: str):
        if self.move_source is None:
            return legal_moves(board, side)
        return self.move_source(board, side)

    def refresh(self, board: Board) -> None:
        if self.mode == "crownless":
            self.in_check = False
            self.winner = None
            self.finished = False
            self.battle_state = "ongoing"
            self._skip_stuck_side(board)
            return
        side = self.current
        self.in_check = in_check(board, side)
        has_move = bool(legal_moves(board, side))
        self.winner = None
        self.finished = False
        if not has_move and self.in_check:
            self.battle_state = "checkmate"
            self.finished = True
            self.winner = opposite(side)
        elif not has_move:
            self.battle_state = "stalemate"
            self.finished = True
        elif self.in_check:
            self.battle_state = "check"
        else:
            self.battle_state = "ongoing"

    def _skip_stuck_side(self, board: Board) -> None:
        if self._moves(board, self.current):
            return
        other = opposite(self.current)
        if not self._moves(board, other):
            return
        if self.on_turn_end is not None:
            self.on_turn_end(self.current)
        self.current = other

    def complete_move(self, board: Board) -> None:
        if self.on_turn_end is not None:
            self.on_turn_end(self.current)
        self.move_count += 1
        self.current = opposite(self.current)
        self.refresh(board)
