from config.settings import ARMY_CAPACITY, ARMY_SIZE, CURRENT_LEVEL
from game.board import Board, create_initial_board
from game.move import Move
from game.move_validator import legal_moves
from game.piece import Piece
from game.relics.events import BEFORE_CAPTURE, CAPTURE_RESOLVED, PIECE_MOVED, GameEvent
from game.turn_manager import TurnManager


class Game:
    def __init__(
        self,
        board: Board | None = None,
        starting: str = "white",
        mode: str = "classic",
        dispatcher=None,
        move_filter=None,
        on_turn_end=None,
    ) -> None:
        self.mode = mode
        self.board = create_initial_board() if board is None else board
        self.dispatcher = dispatcher
        self.move_filter = move_filter
        self.pending_turn = False
        source = None
        if move_filter is not None:
            def source(board_state, side, _filter=move_filter):
                return _filter(board_state, legal_moves(board_state, side))
        self.turns = TurnManager(starting, mode, move_source=source, on_turn_end=on_turn_end)
        self.turns.refresh(self.board)
        self.selected_id: int | None = None
        self.legal: list[Move] = []
        self.last_move: Move | None = None
        self.last_capture_id: int | None = None
        self.hover: tuple[int, int] | None = None
        self.statuses: dict = {}
        self.debug = False
        self.hold_turn = False
        self.bonus_piece_id: int | None = None
        self.relic_flashes: list = []
        self.current_level = CURRENT_LEVEL
        self.army_size = ARMY_SIZE
        self.army_capacity = ARMY_CAPACITY

    def selected_piece(self) -> Piece | None:
        if self.selected_id is None:
            return None
        return self.board.piece_by_id(self.selected_id)

    def clear_selection(self) -> None:
        self.selected_id = None
        self.legal = []

    def toggle_debug(self) -> None:
        self.debug = not self.debug

    def _moves_from(self, piece: Piece) -> list[Move]:
        moves = [
            move
            for move in legal_moves(self.board, piece.color)
            if move.from_col == piece.col and move.from_row == piece.row
        ]
        if self.move_filter is not None:
            moves = self.move_filter(self.board, moves)
        return moves

    def _select(self, piece: Piece) -> None:
        self.selected_id = piece.id
        self.legal = self._moves_from(piece)

    def _legal_to(self, col: int, row: int) -> Move | None:
        for move in self.legal:
            if move.to_col == col and move.to_row == row:
                return move
        return None

    def on_board_click(self, col: int, row: int) -> None:
        if self.turns.finished:
            return
        applied = self._apply_click(col, row)
        if not applied:
            return
        if self.mode == "crownless":
            self.pending_turn = True
            return
        self.turns.complete_move(self.board)

    def _apply_click(self, col: int, row: int) -> bool:
        piece = self.board.piece_at(col, row)
        selected = self.selected_piece()
        if selected is None:
            if piece is not None and piece.color == self.turns.current and self._moves_from(piece):
                self._select(piece)
            return False
        if piece is not None and piece.id == selected.id:
            self.clear_selection()
            return False
        if piece is not None and piece.color == self.turns.current:
            if self._moves_from(piece):
                self._select(piece)
            return False
        move = self._legal_to(col, row)
        if move is None:
            return False
        mover = self.board.piece_at(move.from_col, move.from_row)
        target = self.board.piece_at(move.to_col, move.to_row)
        if target is not None and self.dispatcher is not None and mover is not None:
            self.dispatcher.publish(GameEvent(BEFORE_CAPTURE, _capture_payload(mover, target, move)))
        captured = self.board.apply_move(move)
        self.last_move = move
        self.last_capture_id = captured.piece.id if captured is not None else None
        self.clear_selection()
        if self.dispatcher is not None and mover is not None:
            if captured is not None:
                self.dispatcher.publish(GameEvent(CAPTURE_RESOLVED, _capture_payload(mover, captured.piece, move)))
            self.dispatcher.publish(
                GameEvent(
                    PIECE_MOVED,
                    {
                        "piece_id": mover.id,
                        "origin_square": (move.from_col, move.from_row),
                        "destination_square": (move.to_col, move.to_row),
                    },
                )
            )
        return True


def _capture_payload(mover: Piece, target: Piece, move: Move) -> dict:
    return {
        "capturing_piece_id": mover.id,
        "capturing_kind": mover.kind,
        "capturing_color": mover.color,
        "captured_piece_id": target.id,
        "captured_piece_type": target.kind,
        "captured_piece_color": target.color,
        "captured_trait": target.trait,
        "origin_square": (move.from_col, move.from_row),
        "destination_square": (move.to_col, move.to_row),
    }
