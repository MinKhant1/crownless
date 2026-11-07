"""Click and hover sounds for every button, without wiring each screen.

Every plaque button registers itself while it is drawn onto the window. At the end of the frame the tracker
knows what was clickable: pressing inside one plays a click, and the pointer arriving on a new one plays a
soft hover tick. Cards, offers and other clickable things that turn the cursor into a hand count too.
A modal panel calls modal() so buttons hidden underneath it stay quiet.
"""

import pygame

from rendering import audio as audio_module

HOVER_GAP = 0.06  # sweeping across a row of buttons should patter, not buzz


class UISounds:
    def __init__(self) -> None:
        self._frame: list[tuple[str, pygame.Rect]] = []
        self._live: list[tuple[str, pygame.Rect]] = []
        self._hovered = None
        self._hand = False
        self._quiet = 0.0

    def register(self, screen: pygame.Surface, rect: pygame.Rect, label: str) -> None:
        if screen is not pygame.display.get_surface():
            return  # drawn into an off-screen layer: its coordinates are not the window's
        self._frame.append((label, pygame.Rect(rect)))

    def modal(self) -> None:
        self._frame.clear()

    def target(self, pos) -> tuple | None:
        for label, rect in reversed(self._live):
            if rect.collidepoint(pos):
                return (label, rect.center)
        return None

    def on_event(self, event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.target(event.pos) is not None or self._hand:
                audio_module.audio.play("click", 0.8)

    def end_frame(self, pointer, hand: bool, dt: float) -> None:
        self._live = self._frame
        self._frame = []
        self._quiet = max(0.0, self._quiet - dt)
        over = self.target(pointer)
        key = over if over is not None else ("hand" if hand else None)
        if key is not None and key != self._hovered and self._quiet <= 0:
            audio_module.audio.play("hover", 0.55)
            self._quiet = HOVER_GAP
        self._hovered = key
        self._hand = hand


ui_sounds = UISounds()
