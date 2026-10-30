from game.relics.events import CAPTURE_RESOLVED


def register(dispatcher, context) -> None:
    dispatcher.subscribe(CAPTURE_RESOLVED, lambda event: on_capture(event, context), priority=30)


def on_capture(event, context) -> None:
    rules = context.rules
    if rules is None:
        return
    rules.clear(event.payload["captured_piece_id"])
    if event.payload.get("captured_trait") != "wooden":
        return
    rules.lock(event.payload["capturing_piece_id"], 2)
