from dataclasses import dataclass

from config.settings import BOARD_SIZE, INITIAL_SETUP, parse_square
from game.move import Move
from game.piece import Piece


def in_bounds(col: int, row: int) -> bool:
    return 0 <= col < BOARD_SIZE and 1 <= row <= BOARD_SIZE


@dataclass
class CaptureRecord:
    piece: Piece
    capturer_id: int
    col: int
    row: int


class Board:
    def __init__(
        self,
        pieces: list[Piece] | None = None,
        capture_kings: bool = False,
        enforce_check: bool = True,
    ) -> None:
        self.capture_kings = capture_kings
        self.enforce_check = enforce_check
        self.pieces: list[Piece] = []
        self.capture_log: list[CaptureRecord] = []
        self._grid: dict[tuple[int, int], Piece] = {}
        for piece in pieces or []:
            self.add_piece(piece)

    def add_piece(self, piece: Piece) -> None:
        key = (piece.col, piece.row)
        if key in self._grid:
            raise ValueError(f"square occupied: {key}")
        self._grid[key] = piece
        self.pieces.append(piece)

    def piece_at(self, col: int, row: int) -> Piece | None:
        return self._grid.get((col, row))

    def piece_by_id(self, piece_id: int) -> Piece | None:
        for piece in self.pieces:
            if piece.id == piece_id:
                return piece
        return None

    def king(self, color: str) -> Piece | None:
        for piece in self.pieces:
            if piece.color == color and piece.kind == "king":
                return piece
        return None

    def dismiss(self, piece: Piece) -> None:
        if piece.col is not None and piece.row is not None:
            self._grid.pop((piece.col, piece.row), None)
        if piece in self.pieces:
            self.pieces.remove(piece)
        piece.col = None
        piece.row = None

    def capture(self, piece: Piece, capturer: Piece) -> CaptureRecord:
        record = CaptureRecord(piece, capturer.id, piece.col, piece.row)
        self.capture_log.append(record)
        self._grid.pop((piece.col, piece.row), None)
        self.pieces.remove(piece)
        return record

    def apply_move(self, move: Move) -> Piece | None:
        piece = self.piece_at(move.from_col, move.from_row)
        if piece is None:
            raise ValueError("no piece on the source square")
        target = self.piece_at(move.to_col, move.to_row)
        captured = None
        if target is not None:
            if target.kind == "king" and not self.capture_kings:
                raise ValueError("king cannot be captured")
            captured = self.capture(target, piece)
        self._grid.pop((piece.col, piece.row), None)
        piece.col = move.to_col
        piece.row = move.to_row
        piece.has_moved = True
        if move.promotion:
            piece.kind = move.promotion
        self._grid[(piece.col, piece.row)] = piece
        return captured

    def copy(self) -> "Board":
        return Board(
            [piece.copy() for piece in self.pieces],
            capture_kings=self.capture_kings,
            enforce_check=self.enforce_check,
        )


def create_initial_board() -> Board:
    pieces: list[Piece] = []
    for index, (kind, color, square) in enumerate(INITIAL_SETUP, start=1):
        col, row = parse_square(square)
        pieces.append(Piece(index, kind, color, col, row))
    return Board(pieces)
