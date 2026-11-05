"""Turns what happens in a run into sound and light.

Board events (moves, captures, relic flashes, spawns) arrive through the run's dispatcher; screen changes
(a battle won or lost, gold spent, a piece set down while deploying) are noticed by watching the run each frame.
Sounds and effects for a move wait PIECE_TRAVEL_TIME so they land together with the piece.
"""

import pygame

from config.settings import PIECE_TRAVEL_TIME
from game.relics.events import (
    BATTLE_START,
    CAPTURE_RESOLVED,
    PIECE_MOVED,
    PIECE_REMOVED,
    PIECE_SPAWNED,
    RELIC_FLASH,
    RELIC_VISUAL_TRIGGER,
)
from rendering import audio as audio_module
from rendering.effects import board_effects

EXPLOSION_FLASH = (226, 90, 36)  # the colour explosive.py and chain_fuse.py flash with


class BattleFeedback:
    def __init__(self) -> None:
        self.run = None
        self.layout = None
        self.relic_bar = None
        self._dispatcher = None
        self._capture_square = None
        self._capture_color = "white"
        self._phase: str | None = None
        self._gold: int | None = None
        self._placed: dict | None = None
        self._relic_sound_at = -1.0

    def bind(self, run, layout, relic_bar=None) -> None:
        self.layout = layout
        self.relic_bar = relic_bar
        if run is not self.run:
            self.run = run
            self._phase = run.phase
            self._gold = run.gold
            self._placed = dict(run.deployment.placed)
            board_effects.clear()
        dispatcher = run.relics.dispatcher
        if dispatcher is not self._dispatcher:
            self._dispatcher = dispatcher
            dispatcher.subscribe(CAPTURE_RESOLVED, self._on_capture, priority=200)
            dispatcher.subscribe(PIECE_MOVED, self._on_moved, priority=200)
            dispatcher.subscribe(RELIC_FLASH, self._on_flash, priority=200)
            dispatcher.subscribe(RELIC_VISUAL_TRIGGER, self._on_relic_card, priority=200)
            dispatcher.subscribe(PIECE_SPAWNED, self._on_spawn, priority=200)
            dispatcher.subscribe(BATTLE_START, self._on_battle_start, priority=200)
            dispatcher.subscribe(PIECE_REMOVED, self._on_removed, priority=200)

    # ------------------------------------------------------------------ per frame
    def watch(self, run) -> None:
        if run is not self.run:
            return  # a fresh run this frame; bind() picks it up next frame without replaying its history
        sound = audio_module.audio
        phase = run.phase
        if phase != self._phase:
            if phase == "victory":
                sound.play("victory", 0.9, delay=0.25)
            elif phase == "defeat":
                sound.play("defeat", 0.9, delay=0.3)
            self._phase = phase
            self._placed = dict(run.deployment.placed)
        elif phase in ("preview", "deployment") and run.deployment.placed != self._placed:
            moved = [key for key, square in run.deployment.placed.items() if (self._placed or {}).get(key) != square]
            if moved:
                sound.play("move", 0.75)
            self._placed = dict(run.deployment.placed)
        if self._gold is not None and run.gold < self._gold and phase in ("shop", "starter"):
            sound.play("coin", 0.85)
        self._gold = run.gold

    # ------------------------------------------------------------------ events
    def _center(self, square):
        if self.layout is None:
            return None
        return self.layout.square_rect(*square).center

    def _on_capture(self, event) -> None:
        payload = event.payload
        square = payload["destination_square"]
        self._capture_square = square
        self._capture_color = payload.get("capturing_color", "white")
        pos = self._center(square)
        size = 0 if self.layout is None else self.layout.square
        if payload.get("captured_trait") == "explosive":
            audio_module.audio.play("explosion", 0.9, delay=PIECE_TRAVEL_TIME)
            if pos is not None:
                board_effects.later(PIECE_TRAVEL_TIME, lambda: board_effects.explosion(pos, size))
            return
        attacker = self._capture_color
        loud = 1.0 if payload.get("captured_piece_type") == "king" else 0.85
        name = "capture" if attacker == "white" else "capture_enemy"
        audio_module.audio.play(name, loud, delay=PIECE_TRAVEL_TIME)
        if pos is not None:
            board_effects.later(PIECE_TRAVEL_TIME, lambda: board_effects.capture(pos, size, attacker))

    def _on_moved(self, event) -> None:
        payload = event.payload
        square = payload["destination_square"]
        captured_here = square == self._capture_square
        self._capture_square = None
        if captured_here:
            return
        color = self._color_of(payload.get("piece_id"))
        audio_module.audio.play("move" if color == "white" else "move_enemy", 0.9, delay=PIECE_TRAVEL_TIME)
        pos = self._center(square)
        if pos is not None:
            size = self.layout.square
            board_effects.later(PIECE_TRAVEL_TIME, lambda: board_effects.landing(pos, size, color))

    def _on_flash(self, event) -> None:
        pos = self._center(event.payload["square"])
        if pos is None or tuple(event.payload.get("color", ())) == EXPLOSION_FLASH:
            return  # Explosive and Chain Fuse flash in fire colours; the explosion itself covers those
        color = tuple(min(255, c + 30) for c in event.payload.get("color", (230, 190, 70)))
        size = self.layout.square
        board_effects.later(PIECE_TRAVEL_TIME, lambda: board_effects.holy(pos, size, color))
        now = board_effects.time
        if now - self._relic_sound_at > 0.25:
            self._relic_sound_at = now
            audio_module.audio.play("relic", 0.8, delay=PIECE_TRAVEL_TIME)

    def _on_relic_card(self, event) -> None:
        if self.relic_bar is None or self.layout is None or self.run is None:
            return
        instance_id = event.payload.get("relic_instance_id")
        try:
            slots = self.relic_bar.placements(self.run, self.layout, pygame.time.get_ticks())
        except Exception:
            return
        for slot in slots:
            if slot.owned.instance_id == instance_id:
                center = slot.drawn.center
                size = self.layout.square
                board_effects.later(PIECE_TRAVEL_TIME, lambda: board_effects.holy(center, size, (255, 210, 120)))
                return

    def _on_removed(self, event) -> None:
        # Chain Fuse sets off neighbouring Explosive pieces without a capture
        payload = event.payload
        if payload.get("trait") != "explosive" or payload.get("square") is None:
            return
        pos = self._center(payload["square"])
        if pos is None:
            return
        size = self.layout.square
        board_effects.later(PIECE_TRAVEL_TIME + 0.12, lambda: board_effects.explosion(pos, size))
        audio_module.audio.play("explosion", 0.7, delay=PIECE_TRAVEL_TIME + 0.12)

    def _on_spawn(self, event) -> None:
        audio_module.audio.play("spawn", 0.7, delay=PIECE_TRAVEL_TIME)

    def _on_battle_start(self, _event) -> None:
        audio_module.audio.play("battle_start", 0.8)

    def _color_of(self, piece_id) -> str:
        battle = None if self.run is None else self.run.battle
        if battle is not None and piece_id is not None:
            piece = battle.game.board.piece_by_id(piece_id)
            if piece is not None:
                return piece.color
        return self._capture_color


battle_feedback = BattleFeedback()
