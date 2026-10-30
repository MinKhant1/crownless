from game.relics.events import CAPTURE_RESOLVED, PIECE_REMOVED, GameEvent, visual_trigger
from game.relics.relic_context import NEIGHBORS
from game.relics.relic_registry import register_effect


@register_effect("chain_fuse")
class ChainFuseEffect:
    def __init__(self, owned, definition) -> None:
        self.owned = owned
        self.definition = definition
        self.context = None
        self._seen: set[int] = set()
        self._busy = False

    def on_acquired(self, context) -> None:
        return None

    def register(self, dispatcher, context) -> None:
        self.context = context
        dispatcher.subscribe(CAPTURE_RESOLVED, self._on_capture, priority=18)
        dispatcher.subscribe(PIECE_REMOVED, self._on_removed, priority=18)

    def _on_capture(self, event) -> None:
        payload = event.payload
        if payload.get("captured_trait") != "explosive":
            return
        self._begin(payload.get("captured_piece_id"), payload.get("destination_square"))

    def _on_removed(self, event) -> None:
        payload = event.payload
        if payload.get("trait") != "explosive" or payload.get("source") == "chain_fuse":
            return
        self._begin(payload.get("piece_id"), payload.get("square"))

    def _begin(self, piece_id, square) -> None:
        if self._busy or self.context is None or square is None:
            return
        self._busy = True
        self._seen = set()
        if piece_id is not None:
            self._seen.add(piece_id)
        self._spread(square[0], square[1])
        self._busy = False
        visual_trigger(self.context.dispatcher, self.owned.instance_id, "Chain Fuse")

    def _spread(self, col: int, row: int) -> None:
        board = self.context.board
        if board is None:
            return
        pending = []
        for delta_col, delta_row in NEIGHBORS:
            next_col = col + delta_col
            next_row = row + delta_row
            piece = board.piece_at(next_col, next_row)
            if piece is None or piece.trait != "explosive" or piece.id in self._seen:
                continue
            self._seen.add(piece.id)
            pending.append(piece)
        for piece in pending:
            square = (piece.col, piece.row)
            board.dismiss(piece)
            self.context.flash(square[0], square[1], (226, 90, 36))
            self.context.dispatcher.publish(
                GameEvent(
                    PIECE_REMOVED,
                    {
                        "piece_id": piece.id,
                        "kind": piece.kind,
                        "color": piece.color,
                        "trait": "explosive",
                        "square": square,
                        "source": "chain_fuse",
                    },
                )
            )
            self._spread(square[0], square[1])
