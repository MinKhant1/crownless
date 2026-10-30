from game.board import in_bounds
from game.piece import Piece
from game.relics.events import PIECE_REMOVED, PIECE_SPAWNED, GameEvent


NEIGHBORS = ((0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1))


class RelicContext:
    def __init__(self, run) -> None:
        self.run = run
        self.rules = None

    @property
    def rng(self):
        return self.run.rng

    @property
    def board(self):
        battle = self.run.battle
        if battle is None:
            return None
        return battle.game.board

    @property
    def dispatcher(self):
        return self.run.relics.dispatcher

    def empty_neighbors(self, col: int, row: int) -> list[tuple[int, int]]:
        board = self.board
        if board is None:
            return []
        squares = []
        for delta_col, delta_row in NEIGHBORS:
            next_col = col + delta_col
            next_row = row + delta_row
            if not in_bounds(next_col, next_row):
                continue
            if board.piece_at(next_col, next_row) is None:
                squares.append((next_col, next_row))
        return squares

    def spawn_ally(self, kind: str, col: int, row: int, trait: str | None = None) -> Piece | None:
        board = self.board
        if board is None or not in_bounds(col, row):
            return None
        if board.piece_at(col, row) is not None:
            return None
        piece = Piece(self.run.army.take_id(), kind, "white", col, row)
        board.add_piece(piece)
        if trait:
            self.run.traits.assign_trait(piece.id, trait)
        self.dispatcher.publish(
            GameEvent(
                PIECE_SPAWNED,
                {
                    "piece_id": piece.id,
                    "kind": kind,
                    "color": "white",
                    "square": (col, row),
                    "trait": piece.trait,
                    "source": "effect",
                },
            )
        )
        return piece

    def remove_owned(self, piece_id: int) -> Piece | None:
        piece = self.run.army.remove(piece_id)
        if piece is None:
            return None
        self.run.deployment.remove(piece_id)
        if self.run.selected_piece_id == piece_id:
            self.run.selected_piece_id = None
        self.dispatcher.publish(
            GameEvent(
                PIECE_REMOVED,
                {
                    "piece_id": piece.id,
                    "kind": piece.kind,
                    "color": piece.color,
                    "trait": piece.trait,
                },
            )
        )
        return piece
