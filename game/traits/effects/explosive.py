from game.relics.events import CAPTURE_RESOLVED


def register(dispatcher, context) -> None:
    dispatcher.subscribe(CAPTURE_RESOLVED, lambda event: on_capture(event, context), priority=16)


def on_capture(event, context) -> None:
    if event.payload.get("captured_trait") != "explosive":
        return
    board = context.board
    capturer = None if board is None else board.piece_by_id(event.payload["capturing_piece_id"])
    if capturer is None:
        return
    col, row = capturer.col, capturer.row
    board.dismiss(capturer)
    if context.rules is not None:
        context.rules.clear(capturer.id)
    context.flash(col, row, (226, 90, 36))
