from game.relics.events import BATTLE_END


def register(dispatcher, context) -> None:
    dispatcher.subscribe(BATTLE_END, lambda event: on_battle_end(event, context), priority=70)


def on_battle_end(event, context) -> None:
    board = context.board
    if board is None:
        return
    rules = context.rules
    for piece in list(board.pieces):
        if piece.trait != "ghost":
            continue
        board.dismiss(piece)
        if rules is not None:
            rules.clear(piece.id)
