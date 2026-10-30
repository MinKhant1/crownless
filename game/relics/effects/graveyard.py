from game.relics.events import BATTLE_START, CAPTURE_RESOLVED, PIECE_REMOVED, visual_trigger
from game.relics.relic_registry import register_effect


@register_effect("graveyard")
class GraveyardEffect:
    def __init__(self, owned, definition) -> None:
        self.owned = owned
        self.definition = definition
        self.context = None
        self._busy = False

    def on_acquired(self, context) -> None:
        self.owned.state.setdefault("used_this_battle", False)

    def register(self, dispatcher, context) -> None:
        self.context = context
        dispatcher.subscribe(BATTLE_START, self._reset, priority=12)
        dispatcher.subscribe(CAPTURE_RESOLVED, self._on_capture, priority=12)
        dispatcher.subscribe(PIECE_REMOVED, self._on_removed, priority=12)

    def _reset(self, _event) -> None:
        self.owned.state["used_this_battle"] = False

    def _on_capture(self, event) -> None:
        payload = event.payload
        if payload.get("captured_piece_color") != "white" or not payload.get("captured_trait"):
            return
        self._restore(payload.get("captured_piece_type"), payload.get("destination_square"))

    def _on_removed(self, event) -> None:
        payload = event.payload
        if payload.get("color") != "white" or not payload.get("trait"):
            return
        if payload.get("source") == "graveyard":
            return
        self._restore(payload.get("kind"), payload.get("square"))

    def _restore(self, kind, square) -> None:
        if self._busy or self.owned.state.get("used_this_battle") or self.context is None:
            return
        if not kind or square is None:
            return
        self._busy = True
        self.owned.state["used_this_battle"] = True
        board = self.context.board
        target = None
        if board is not None and board.piece_at(square[0], square[1]) is None:
            target = square
        elif board is not None:
            options = self.context.empty_neighbors(square[0], square[1])
            if options:
                target = self.context.rng.choice(options)
        if target is not None:
            self.context.spawn_ally(kind, target[0], target[1], None)
            self.context.flash(target[0], target[1], (150, 186, 120))
        visual_trigger(self.context.dispatcher, self.owned.instance_id, "Graveyard")
        self._busy = False
