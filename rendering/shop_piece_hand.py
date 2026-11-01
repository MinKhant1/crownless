import math

import pygame

from config.settings import PIECE_PRICE
from game.run_state import RunState
from rendering.asset_manager import AssetManager
from rendering.card_motion import (
    CARD_ANIMATION,
    Motion,
    anchored,
    drag_angle,
    past_drag_threshold,
    placed_rect,
    step_motion,
)
from rendering.hud_renderer import draw_button, draw_relic_glow, get_font, overlay_buy_rect
from rendering.shop_layout import ShopLayout
from rendering.special_piece_renderer import special_pieces


class ShopPieceHand:
    def __init__(self) -> None:
        self.hovered = False
        self.selected = False
        self.dragging = False
        self.armed = False
        self.drag_start_position: tuple[int, int] | None = None
        self.drag_offset = (0, 0)
        self._press_buy = False
        self._motion: Motion | None = None
        self._pointer = (0, 0)
        self._vel_x = 0.0
        self._serial = -1
        self._sprite_size: tuple[int, int] | None = None
        self._sprite: pygame.Surface | None = None

    def clear(self) -> None:
        self.hovered = False
        self.selected = False
        self._finish()

    def prepare(self, assets: AssetManager, run: RunState, layout: ShopLayout) -> None:
        if not self.live(run) or not layout.cards:
            self._sprite = None
            self._sprite_size = None
            return
        box = piece_box(layout.cards[0], run.shop.piece_kind.capitalize())
        image = special_pieces.image(assets, "white", run.shop.piece_kind, run.shop.piece_trait, min(box.w, box.h))
        self._sprite = image
        self._sprite_size = image.get_size()

    def update(self, dt: float, run: RunState, layout: ShopLayout, window: tuple[int, int]) -> None:
        self._sync(run)
        if not self.live(run):
            self._motion = None
            return
        if self.dragging and dt > 0:
            self._vel_x *= math.exp(-12.0 * dt)
        rest = self.rest_rect(run, layout)
        target = self._target(rest)
        speed = CARD_ANIMATION["drag_speed"] if self.dragging else CARD_ANIMATION["animation_speed"]
        self._motion = anchored(step_motion(self._motion, target, dt, speed), rest, window)

    def live(self, run: RunState) -> bool:
        return not run.shop.piece_sold

    def rest_rect(self, run: RunState, layout: ShopLayout) -> pygame.Rect:
        box = piece_box(layout.cards[0], run.shop.piece_kind.capitalize())
        if self._sprite_size is None:
            return box
        rect = pygame.Rect(0, 0, self._sprite_size[0], self._sprite_size[1])
        rect.center = box.center
        return rect

    def drawn_rect(self, run: RunState, layout: ShopLayout, window: tuple[int, int]) -> pygame.Rect | None:
        self._sync(run)
        if not self.live(run) or not layout.cards:
            return None
        rest = self.rest_rect(run, layout)
        motion = self._motion if self._motion is not None else self._target(rest)
        return placed_rect(motion, rest, window)

    def buy_caption(self, run: RunState) -> tuple[str, bool]:
        if run.gold < PIECE_PRICE:
            return "Not enough Gold", False
        return "Buy", True

    def buy_rect(self, run: RunState, layout: ShopLayout, window: tuple[int, int]) -> pygame.Rect | None:
        if not self.live(run) or self.dragging or not self.selected:
            return None
        item = self.drawn_rect(run, layout, window)
        if item is None:
            return None
        return overlay_buy_rect(item, self.buy_caption(run)[0], "top")

    def claims(self, pos: tuple[int, int], run: RunState, layout: ShopLayout, window: tuple[int, int]) -> bool:
        if not self.live(run):
            return False
        if self.dragging or self.armed:
            return True
        rect = self.drawn_rect(run, layout, window)
        if rect is not None and rect.collidepoint(pos):
            return True
        button = self.buy_rect(run, layout, window)
        return button is not None and button.collidepoint(pos)

    def wants(self, run: RunState, layout: ShopLayout, window: tuple[int, int]) -> bool:
        return self.hovered or self.dragging or self.claims(self._pointer, run, layout, window)

    def on_motion(
        self,
        run: RunState,
        pos: tuple[int, int],
        layout: ShopLayout,
        window: tuple[int, int],
        held: bool | None = None,
    ) -> None:
        previous = self._pointer
        self._pointer = pos
        if not self.live(run):
            self.hovered = False
            return
        button_held = self.armed if held is None else bool(held)
        if button_held and self.drag_start_position is not None and not self.dragging:
            if past_drag_threshold(self.drag_start_position, pos):
                self.dragging = True
        if self.dragging:
            dx = pos[0] - previous[0]
            self._vel_x = self._vel_x * 0.35 + dx * 0.65
            self.hovered = False
            return
        rect = self.drawn_rect(run, layout, window)
        self.hovered = rect is not None and rect.collidepoint(pos)

    def on_left_down(self, pos: tuple[int, int], run: RunState, layout: ShopLayout, window: tuple[int, int]) -> bool:
        self._pointer = pos
        button = self.buy_rect(run, layout, window)
        if button is not None and button.collidepoint(pos):
            self.armed = True
            self._press_buy = True
            self.drag_start_position = None
            self.dragging = False
            return True
        rect = self.drawn_rect(run, layout, window)
        if rect is None or not rect.collidepoint(pos):
            return False
        self.armed = True
        self._press_buy = False
        self.drag_start_position = pos
        self.drag_offset = (pos[0] - rect.centerx, pos[1] - rect.centery)
        self.dragging = False
        return True

    def on_left_up(self, pos: tuple[int, int], run: RunState, layout: ShopLayout, window: tuple[int, int]) -> bool:
        if not self.armed and not self.dragging:
            return False
        if self.dragging:
            selected = self.selected
            self._finish()
            self.selected = selected
            return True
        buying = self._press_buy
        self._finish()
        if buying:
            button = self.buy_rect(run, layout, window)
            if button is not None and button.collidepoint(pos) and self.buy_caption(run)[1]:
                before = len(run.army.pieces)
                run.buy_piece()
                if len(run.army.pieces) > before:
                    self.selected = False
                    self.hovered = False
            return True
        rect = self.drawn_rect(run, layout, window)
        if rect is not None and rect.collidepoint(pos):
            self.selected = not self.selected
        return True

    def paint(
        self,
        screen: pygame.Surface,
        dx: int,
        alpha: int,
        run: RunState,
        layout: ShopLayout,
    ) -> None:
        image = self._sprite
        if image is None or not self.live(run):
            return
        window = screen.get_size()
        rect = self.drawn_rect(run, layout, window)
        if rect is None:
            return
        if not self.dragging:
            rect = rect.move(dx, 0)
        angle = 0.0 if self._motion is None else self._motion.angle
        _shadow(screen, rect, self.dragging, angle)
        face = image if image.get_size() == rect.size else pygame.transform.smoothscale(image, rect.size)
        if alpha < 255:
            face = face.copy()
            face.set_alpha(alpha)
        _rotated(screen, face, rect.center, angle)
        if (self.hovered or self.selected) and not self.dragging:
            draw_relic_glow(screen, rect)
        button = self.buy_rect(run, layout, window)
        if button is not None:
            label, enabled = self.buy_caption(run)
            draw_button(screen, button.move(dx, 0), label, enabled=enabled, font_size=12)

    def _target(self, rest: pygame.Rect) -> Motion:
        if self.dragging:
            scale = CARD_ANIMATION["drag_scale"]
            centerx = self._pointer[0] - self.drag_offset[0]
            centery = self._pointer[1] - self.drag_offset[1] + CARD_ANIMATION["drag_lift"]
            bottom = centery + rest.h * scale / 2
            return Motion(centerx, bottom, scale, drag_angle(self._vel_x))
        if self.selected:
            lift = CARD_ANIMATION["selected_lift"]
            scale = CARD_ANIMATION["selected_scale"]
        elif self.hovered:
            lift = CARD_ANIMATION["hover_lift"]
            scale = CARD_ANIMATION["hover_scale"]
        else:
            lift = 0.0
            scale = 1.0
        return Motion(float(rest.centerx), rest.bottom + lift, scale, 0.0)

    def _sync(self, run: RunState) -> None:
        serial = run.shop.offer_serial
        if serial != self._serial:
            self._serial = serial
            self.selected = False
            self.hovered = False
            self._finish()
        if run.shop.piece_sold:
            self.selected = False
            self.hovered = False
            if self.dragging or self.armed:
                self._finish()

    def _finish(self) -> None:
        self.dragging = False
        self.armed = False
        self.drag_start_position = None
        self._press_buy = False
        self._vel_x = 0.0


def piece_box(card: pygame.Rect, label: str) -> pygame.Rect:
    del label
    margin_x = max(4, int(card.w * 0.06))
    margin_y = max(4, int(card.h * 0.08))
    box = card.inflate(-margin_x * 2, -margin_y * 2)
    box.w = max(1, box.w)
    box.h = max(1, box.h)
    return box


def _shadow(screen: pygame.Surface, rect: pygame.Rect, strong: bool, angle: float) -> None:
    alpha = 110 if strong else 60
    offset = 6 if strong else 3
    shadow = pygame.Surface((rect.w, max(1, rect.h // 3)), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (16, 10, 6, alpha), shadow.get_rect())
    _rotated(screen, shadow, (rect.centerx + offset, rect.bottom - shadow.get_height() // 2 + offset), angle)


def _rotated(screen: pygame.Surface, image: pygame.Surface, center: tuple[int, int], angle: float) -> None:
    if abs(angle) > 0.2:
        image = pygame.transform.rotate(image, angle)
    screen.blit(image, image.get_rect(center=center))


shop_piece = ShopPieceHand()
