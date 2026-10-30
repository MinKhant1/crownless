from config.settings import BOARD_SIZE, DEPLOY_ROWS
from game.army_manager import ArmyManager
from game.piece import Piece

KIND_HOMES: dict[str, tuple[tuple[int, int], ...]] = {
    "king": ((3, 1), (2, 1), (4, 1), (1, 1), (5, 1), (0, 1), (3, 2), (2, 2), (4, 2), (1, 2), (5, 2), (0, 2)),
    "queen": ((2, 1), (4, 1), (3, 2), (2, 2), (4, 2), (1, 1), (5, 1), (0, 1)),
    "rook": ((0, 1), (5, 1), (0, 2), (5, 2), (1, 1), (4, 1)),
    "bishop": ((1, 1), (4, 1), (2, 1), (3, 1), (1, 2), (4, 2)),
    "knight": ((1, 1), (4, 1), (0, 2), (5, 2), (2, 1), (3, 1)),
    "pawn": ((0, 2), (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (0, 1), (5, 1)),
}


class DeploymentManager:
    def __init__(self) -> None:
        self.placed: dict[int, tuple[int, int]] = {}

    def clear(self) -> None:
        self.placed.clear()

    def piece_id_at(self, col: int, row: int) -> int | None:
        for piece_id, position in self.placed.items():
            if position == (col, row):
                return piece_id
        return None

    def non_king_count(self, army: ArmyManager) -> int:
        total = 0
        for piece_id in self.placed:
            piece = army.piece_by_id(piece_id)
            if piece is not None and piece.kind != "king":
                total += 1
        return total

    def can_place(
        self,
        piece: Piece,
        col: int,
        row: int,
        blocked: set[tuple[int, int]],
        capacity: int,
        army: ArmyManager,
    ) -> bool:
        if col < 0 or col >= BOARD_SIZE or row not in DEPLOY_ROWS:
            return False
        if (col, row) in blocked:
            return False
        occupant = self.piece_id_at(col, row)
        if occupant is not None and occupant != piece.id:
            return False
        if piece.kind != "king" and piece.id not in self.placed:
            if self.non_king_count(army) >= capacity:
                return False
        return True

    def squares_for(
        self,
        piece: Piece,
        blocked: set[tuple[int, int]],
        capacity: int,
        army: ArmyManager,
    ) -> list[tuple[int, int]]:
        squares: list[tuple[int, int]] = []
        for row in DEPLOY_ROWS:
            for col in range(BOARD_SIZE):
                if self.can_place(piece, col, row, blocked, capacity, army):
                    squares.append((col, row))
        return squares

    def place(
        self,
        piece: Piece,
        col: int,
        row: int,
        blocked: set[tuple[int, int]],
        capacity: int,
        army: ArmyManager,
    ) -> bool:
        if not self.can_place(piece, col, row, blocked, capacity, army):
            return False
        self.placed[piece.id] = (col, row)
        return True

    def remove(self, piece_id: int) -> None:
        self.placed.pop(piece_id, None)

    def swap(self, piece_a_id: int, piece_b_id: int) -> bool:
        if piece_a_id == piece_b_id:
            return False
        if piece_a_id not in self.placed or piece_b_id not in self.placed:
            return False
        first = self.placed[piece_a_id]
        second = self.placed[piece_b_id]
        self.placed[piece_a_id] = second
        self.placed[piece_b_id] = first
        return True

    def ready(self, army: ArmyManager) -> bool:
        king = army.king()
        if king is None or king.id not in self.placed:
            return False
        return self.non_king_count(army) <= army.capacity
