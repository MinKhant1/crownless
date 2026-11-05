from game.board import in_bounds
from game.piece import Piece
from game.relics.events import PIECE_REMOVED, PIECE_SPAWNED, RELIC_FLASH, GameEvent


NEIGHBORS = ((0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1))


def claim(event, relic_id: str) -> bool:
    """Stacked copies of a 'first X' relic take turns: the first copy to answer an event keeps it,
    and the other copies wait for the next one. Returns False if another copy already took this event."""
    claimed = event.payload.setdefault("_claimed_by", set())
    if relic_id in claimed:
        return False
    claimed.add(relic_id)
    return True


def copy_index(event, relic_id: str) -> int:
    """0 for the first copy of a relic to answer this event, 1 for the second, and so on."""
    counts = event.payload.setdefault("_copies", {})
    index = counts.get(relic_id, 0)
    counts[relic_id] = index + 1
    return index


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
    def game(self):
        battle = self.run.battle
        if battle is None:
            return None
        return battle.game

    def flash(self, col: int, row: int, color: tuple[int, int, int]) -> None:
        game = self.game
        if game is None:
            return
        game.relic_flashes.append((col, row, color))
        # the flash list is cleared when the turn ends in the same click, so say it out loud for the effects layer
        self.dispatcher.publish(GameEvent(RELIC_FLASH, {"square": (col, row), "color": tuple(color)}))

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
