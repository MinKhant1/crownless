from config.settings import GOLDEN_BONUS
from game.relics.events import BATTLE_END


def register(dispatcher, context) -> None:
    dispatcher.subscribe(BATTLE_END, lambda event: on_battle_end(event, context), priority=15)


def on_battle_end(event, context) -> None:
    if event.payload.get("outcome") != "victory":
        return
    board = context.board
    if board is None:
        return
    count = sum(1 for piece in board.pieces if piece.color == "white" and piece.trait == "golden")
    bonus = count * GOLDEN_BONUS
    context.run.golden_reward = bonus
    context.run.gold += bonus
