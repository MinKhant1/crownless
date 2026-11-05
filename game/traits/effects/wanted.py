"""Wanted.

On your piece: enemies make it their main target (the AI reads the trait; see ai/trait_evaluator.py).
On an enemy piece: it carries a bounty. Each enemy Wanted piece you capture pays WANTED_BOUNTY gold when the
battle is won; losing the battle pays nothing.
"""

from config.settings import WANTED_BOUNTY
from game.relics.events import BATTLE_END, BATTLE_START, CAPTURE_RESOLVED


def register(dispatcher, context) -> None:
    dispatcher.subscribe(BATTLE_START, lambda event: on_battle_start(event, context), priority=90)
    dispatcher.subscribe(CAPTURE_RESOLVED, lambda event: on_capture(event, context), priority=40)
    dispatcher.subscribe(BATTLE_END, lambda event: on_battle_end(event, context), priority=15)


def on_battle_start(event, context) -> None:
    context.run.wanted_captured = 0


def on_capture(event, context) -> None:
    payload = event.payload
    if payload.get("captured_trait") != "wanted":
        return
    if payload.get("captured_piece_color") != "black" or payload.get("capturing_color") != "white":
        return
    context.run.wanted_captured = getattr(context.run, "wanted_captured", 0) + 1
    square = payload.get("destination_square")
    if square is not None:
        context.flash(square[0], square[1], (236, 196, 90))


def on_battle_end(event, context) -> None:
    if event.payload.get("outcome") != "victory":
        return
    bonus = getattr(context.run, "wanted_captured", 0) * WANTED_BOUNTY
    context.run.bounty_reward = bonus
    context.run.gold += bonus
