import random

import pygame

from game.traits import TRAIT_IDS
from rendering.card_motion import approach
from rendering import style
from rendering.hud_renderer import draw_background
from scenes.menu_piece import MenuPiece, draw_trait_note


MENU_BUTTONS = (("start", "Start"), ("guide", "How to Play"), ("collection", "Collection"), ("exit", "Exit"))


class MainMenuScreen:
    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self.king = MenuPiece("king", self.rng.choice(TRAIT_IDS))
        self.buttons = MENU_BUTTONS
        self._hover = ""
        self._pressed = ""
        self._hot = {key: 0.0 for key, _label in self.buttons}
        self._down = {key: 0.0 for key, _label in self.buttons}
        self._held = False
        self._pointer = (0, 0)
        self.age = 0.0
        self._flight = self._new_flight()

    def _new_flight(self) -> tuple[tuple[float, float], ...]:
        side = self.rng.choice((0.0, 1.0))
        return ((side, 0.0), (side, 0.45), (0.5, 0.45))

    def _king_rest(self, window: tuple[int, int]) -> pygame.Rect:
        home = _layout(window)["king"]
        if self.age >= 3.2:
            return home
        t = min(1.0, self.age / 3.2)
        t = t * t * (3.0 - 2.0 * t)
        inset = home.w / 2 + 12
        points = [(inset + x * (window[0] - 2 * inset),
                   inset + y * (window[1] - 2 * inset)) for x, y in self._flight]
        points.append(home.center)
        u = 1.0 - t
        home.center = tuple(round(u ** 3 * points[0][axis] + 3 * u * u * t * points[1][axis]
                                  + 3 * u * t * t * points[2][axis] + t ** 3 * points[3][axis])
                            for axis in (0, 1))
        return home

    def enter(self) -> None:
        self.age = 0.0
        self._flight = self._new_flight()
        self.king._motion = None
        self.king.trait = self.rng.choice(TRAIT_IDS)
        self.king.on_release()
        self.king.hovered = False
        self._pressed = ""

    def update(self, dt: float, window: tuple[int, int]) -> None:
        self.age += max(0.0, dt)
        home = self._king_rest(window)
        self.king.update(dt, home, window)
        for key, _label in self.buttons:
            rect = _layout(window)[key]
            hot = rect.collidepoint(self._pointer)
            self._hot[key] = approach(self._hot[key], 1.0 if hot else 0.0, dt, 12.0)
            self._down[key] = approach(self._down[key], 1.0 if hot and self._held else 0.0, dt, 16.0)

    def on_event(self, event: pygame.event.Event, window: tuple[int, int]) -> str | None:
        places = _layout(window)
        places["king"] = self._king_rest(window)
        if event.type == pygame.MOUSEMOTION:
            self._pointer = event.pos
            self.king.on_motion(event.pos, places["king"], window, self._held)
            return None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._pointer = event.pos
            self._held = True
            for key, _label in self.buttons:
                if places[key].collidepoint(event.pos):
                    self._pressed = key
                    return None
            if self.king.on_press(event.pos, places["king"], window):
                self._pressed = ""
                return None
            self._pressed = ""
            return None
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._held = False
            self.king.on_release()
            pressed = self._pressed
            self._pressed = ""
            if pressed and places[pressed].collidepoint(event.pos):
                return pressed
        return None

    def wants_hand(self, window: tuple[int, int]) -> bool:
        places = _layout(window)
        if self.king.hovered or self.king.dragging:
            return True
        return any(places[key].collidepoint(self._pointer) for key, _label in self.buttons)

    def draw(self, screen: pygame.Surface, assets) -> None:
        draw_background(screen, assets)
        window = screen.get_size()
        places = _layout(window)
        _draw_logo(screen, assets, places["logo"])
        places["king"] = self._king_rest(window)
        for key, label in self.buttons:
            _draw_menu_button(screen, places[key], label, self._hot[key], self._down[key])
        self.king.paint(screen, assets, places["king"], window)
        draw_trait_note(screen, self.king, self.king.drawn(places["king"], window), side="left")


def _layout(window: tuple[int, int]) -> dict[str, pygame.Rect]:
    width, height = window
    logo = pygame.Rect(0, 0, min(560, int(width * 0.46)), min(180, int(height * 0.2)))
    logo.midtop = (width // 2, max(18, int(height * 0.045)))
    king_side = max(96, min(210, int(height * 0.24)))
    king = pygame.Rect(0, 0, king_side, king_side)
    king.midtop = (width // 2, logo.bottom + max(8, int(height * 0.02)))
    button_w = min(320, width - 80)
    button_h = max(46, min(58, int(height * 0.065)))
    gap = max(12, int(height * 0.018))
    top = king.bottom + max(18, int(height * 0.03))
    buttons = {}
    for index, (key, _label) in enumerate(MENU_BUTTONS):
        rect = pygame.Rect(0, 0, button_w, button_h)
        rect.midtop = (width // 2, top + index * (button_h + gap))
        buttons[key] = rect
    return {"logo": logo, "king": king, **buttons}


def _draw_logo(screen: pygame.Surface, assets, bounds: pygame.Rect) -> None:
    if assets is None or not assets.has("crownless_logo"):
        return
    image = assets.fitted("crownless_logo", bounds.w, bounds.h)
    screen.blit(image, image.get_rect(center=bounds.center))


def _draw_menu_button(screen: pygame.Surface, rect: pygame.Rect, label: str, hover: float, pressed: float) -> None:
    scale = 1.0 + 0.04 * hover - 0.03 * pressed
    drawn = pygame.Rect(0, 0, max(1, int(rect.w * scale)), max(1, int(rect.h * scale)))
    drawn.center = rect.center
    state = "pressed" if pressed > 0.5 else "hover" if hover > 0.5 else "idle"
    style.draw_plaque_button(screen, drawn, label, state, font_size=max(18, int(drawn.h * 0.46)))
