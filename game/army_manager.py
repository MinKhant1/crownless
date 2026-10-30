from config.settings import STARTER_KINDS, STARTING_NON_KING_CAPACITY
from game.piece import Piece


class ArmyManager:
    def __init__(self) -> None:
        self.pieces: list[Piece] = []
        self.capacity = STARTING_NON_KING_CAPACITY
        self._next_id = 1

    def create(self, kind: str, color: str = "white") -> Piece:
        piece = Piece(self._next_id, kind, color)
        self._next_id += 1
        self.pieces.append(piece)
        return piece

    def add_starters(self) -> None:
        for kind in STARTER_KINDS:
            self.create(kind)

    def piece_by_id(self, piece_id: int) -> Piece | None:
        for piece in self.pieces:
            if piece.id == piece_id:
                return piece
        return None

    def king(self) -> Piece | None:
        for piece in self.pieces:
            if piece.color == "white" and piece.kind == "king":
                return piece
        return None

    def increase_capacity(self) -> None:
        self.capacity += 1

    def take_id(self) -> int:
        piece_id = self._next_id
        self._next_id += 1
        return piece_id

    def remove(self, piece_id: int) -> Piece | None:
        piece = self.piece_by_id(piece_id)
        if piece is None:
            return None
        self.pieces.remove(piece)
        return piece
