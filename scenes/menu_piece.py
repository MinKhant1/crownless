import math

import pygame

from game.piece import Piece
from game.traits import trait_by_id
from rendering.card_motion import (
    CARD_ANIMATION,
    Motion,
    anchored,
    drag_angle,
    past_drag_threshold,
    placed_rect,
    step_motion,
)
from rendering.hud_renderer import _blit_text, draw_relic_glow, get_font
from rendering.piece_visual_effects import draw_contact_shadow, figurines, present, shadow_center


class MenuPiece:
    """A decorative piece that uses the board figurine and the shared drag motion."""

    def __init__(self, kind: str, trait: str, piece_id: int = 90001) -> None:
        self.kind = kind
        self.trait = trait
        self.piece_id = piece_id
        self.hovered = False
        self.dragging = False
        self._armed = False
        self._motion: Motion | None = None
        self._pointer = (0, 0)
        self._vel_x = 0.0
        self._offset = (0, 0)
        self._start: tuple[int, int] | None = None

    def piece(self) -> Piece:
        return Piece(self.piece_id, self.kind, "white", trait=self.trait)

    def drawn(self, rest: pygame.Rect, window: tuple[int, int]) -> pygame.Rect:
        motion = self._motion if self._motion is not None else Motion(rest.centerx, rest.bottom, 1.0, 0.0)
        return placed_rect(motion, rest, window)

    def update(self, dt: float, rest: pygame.Rect, window: tuple[int, int]) -> None:
        if self.dragging and dt > 0:
            self._vel_x *= math.exp(-12.0 * dt)
        if self.dragging:
            scale = CARD_ANIMATION["drag_scale"]
            centerx = self._pointer[0] - self._offset[0]
            centery = self._pointer[1] - self._offset[1] + CARD_ANIMATION["drag_lift"]
            bottom = centery + rest.h * scale / 2
            target = Motion(centerx, bottom, scale, drag_angle(self._vel_x))
            speed = CARD_ANIMATION["drag_speed"]
        elif self.hovered:
            target = Motion(float(rest.centerx), rest.bottom + CARD_ANIMATION["hover_lift"], CARD_ANIMATION["hover_scale"], 0.0)
            speed = CARD_ANIMATION["animation_speed"]
        else:
            target = Motion(float(rest.centerx), float(rest.bottom), 1.0, 0.0)
            speed = CARD_ANIMATION["animation_speed"]
        self._motion = anchored(step_motion(self._motion, target, dt, speed), rest, window)

    def on_motion(self, pos: tuple[int, int], rest: pygame.Rect, window: tuple[int, int], held: bool) -> None:
        previous = self._pointer
        self._pointer = pos
        if held and self._armed and not self.dragging and past_drag_threshold(self._start, pos):
            self.dragging = True
        if self.dragging:
            self._vel_x = self._vel_x * 0.35 + (pos[0] - previous[0]) * 0.65
            self.hovered = False
            return
        self.hovered = self.drawn(rest, window).collidepoint(pos)

    def on_press(self, pos: tuple[int, int], rest: pygame.Rect, window: tuple[int, int]) -> bool:
        self._pointer = pos
        rect = self.drawn(rest, window)
        if not rect.collidepoint(pos):
            return False
        self._armed = True
        self._start = pos
        self._offset = (pos[0] - rect.centerx, pos[1] - rect.centery)
        self.dragging = False
        return True

    def on_release(self) -> None:
        self._armed = False
        self._start = None
        self.dragging = False

    def paint(self, screen: pygame.Surface, assets, rest: pygame.Rect, window: tuple[int, int]) -> pygame.Rect:
        rect = self.drawn(rest, window)
        motion = self._motion if self._motion is not None else Motion(rest.centerx, rest.bottom, 1.0, 0.0)
        image = figurines.image(assets, self.piece(), max(1, rest.w))
        lift = 0.85 if self.dragging else 0.4 if self.hovered else 0.0
        draw_contact_shadow(screen, shadow_center(rect.center, rest.w), rest.w, lift)
        face = present(image, motion.scale, motion.angle)
        screen.blit(face, face.get_rect(center=rect.center))
        if self.hovered or self.dragging:
            draw_relic_glow(screen, rect)
        return rect


def draw_trait_note(screen: pygame.Surface, piece: MenuPiece, anchor: pygame.Rect) -> None:
    trait = trait_by_id(piece.trait)
    if trait is None or not piece.hovered or piece.dragging:
        return
    title = f"{trait.name} {piece.kind.capitalize()}"
    font = get_font(16, bold=True)
    body = get_font(14, bold=False)
    title_w, title_h = font.size(title)
    body_w, body_h = body.size(trait.description)
    width = max(title_w, min(body_w, 280)) + 28
    lines = wrap_text(trait.description, body, width - 28)
    height = 16 + title_h + 8 + len(lines) * (body_h + 2) + 10
    plate = pygame.Rect(0, 0, width, height)
    plate.midtop = (anchor.centerx, anchor.bottom + 8)
    bounds = screen.get_rect().inflate(-12, -12)
    plate.clamp_ip(bounds)
    pygame.draw.rect(screen, (236, 220, 196), plate, border_radius=10)
    pygame.draw.rect(screen, (120, 84, 48), plate, width=2, border_radius=10)
    _blit_text(screen, title, font, (68, 40, 26), midleft=(plate.x + 14, plate.y + 12 + title_h // 2))
    y = plate.y + 18 + title_h
    for line in lines:
        _blit_text(screen, line, body, (92, 64, 42), midleft=(plate.x + 14, y + body_h // 2))
        y += body_h + 2


def wrap_text(text: str, font: pygame.font.Font, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else f"{current} {word}"
        if font.size(trial)[0] <= width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]
