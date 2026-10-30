from game.relics.events import BATTLE_START


def register(dispatcher, context) -> None:
    dispatcher.subscribe(BATTLE_START, lambda event: on_battle_start(event, context), priority=90)


def on_battle_start(event, context) -> None:
    return None
