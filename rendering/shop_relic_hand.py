import math
from dataclasses import dataclass

import pygame

from config.settings import RELIC_PRICE, SHOP_BUY
from game.relics.relic_data import RelicDef, relic_by_id
from game.run_state import RunState
from rendering.asset_manager import AssetManager
from rendering.card_motion import (
    CARD_ANIMATION,
    Motion,
    anchored,
    drag_angle,
    past_drag_threshold,
    placed_rect,
    preview_order,
    step_motion,
)
from rendering.hud_renderer import _blit_text, draw_button, draw_relic_glow, get_font
from rendering.relic_card import CARD_RATIO, RelicCardRenderer
from rendering.relic_flip import shop_reveal
from rendering.relic_tooltip_renderer import draw_relic_tooltip
from rendering.shop_layout import ShopLayout


def relic_offer_slot(card: pygame.Rect) -> pygame.Rect:
    top = card.y + int(card.h * 0.04)
    bottom = card.y + int(card.h * SHOP_BUY[1]) - max(2, int(card.h * 0.02))
    height = max(1, bottom - top)
    width = max(1, int(round(height * CARD_RATIO)))
    limit = max(1, int(card.w * 0.92))
    if width > limit:
        width = limit
        height = max(1, int(round(width / CARD_RATIO)))
    rect = pygame.Rect(0, 0, width, height)
    rect.midtop = (card.centerx, top)
    return rect


@dataclass
class ShopSlot:
    relic_id: str
    definition: RelicDef
    rest: pygame.Rect
    drawn: pygame.Rect
    angle: float


class ShopRelicHand:
    def __init__(self) -> None:
        self.cards = RelicCardRenderer()
        self.hovered_card_id: str | None = None
        self.selected_card_id: str | None = None
        self.dragged_card_id: str | None = None
        self.drag_start_position: tuple[int, int] | None = None
        self.drag_offset = (0, 0)
        self.visual_order: list[str] = []
        self.dragging = False
        self._armed = False
        self._press_buy = False
        self._pressed_id: str | None = None
        self._preview: list[str] | None = None
        self._motion: dict[str, Motion] = {}
        self._pointer = (0, 0)
        self._vel_x = 0.0
        self._serial = -1
        self.flying: dict | None = None

    def clear(self) -> None:
        self.hovered_card_id = None
        self.selected_card_id = None
        self._finish_gesture(keep_selection=False)
        self.flying = None

    def update(self, dt: float, run: RunState, layout: ShopLayout, window: tuple[int, int]) -> None:
        self._sync(run)
        if self.dragging and dt > 0:
            self._vel_x *= math.exp(-12.0 * dt)
        if self.flying is not None:
            self.flying["age"] = self.flying.get("age", 0.0) + max(0.0, dt)
            if self.flying["age"] >= 0.36:
                self.flying = None
        live: set[str] = set()
        for relic_id, rest, motion in self._targets(run, layout, window):
            live.add(relic_id)
            speed = CARD_ANIMATION["drag_speed"] if relic_id == self.dragged_card_id else CARD_ANIMATION["animation_speed"]
            moved = step_motion(self._motion.get(relic_id), motion, dt, speed)
            self._motion[relic_id] = anchored(moved, rest, window)
        for key in list(self._motion):
            if key not in live:
                self._motion.pop(key, None)

    def slots(self, run: RunState, layout: ShopLayout, window: tuple[int, int]) -> list[ShopSlot]:
        self._sync(run)
        found: list[ShopSlot] = []
        for relic_id, rest, motion in self._targets(run, layout, window):
            visual = self._motion.get(relic_id, motion)
            definition = relic_by_id(relic_id)
            if definition is None:
                continue
            found.append(ShopSlot(relic_id, definition, rest, placed_rect(visual, rest, window), visual.angle))
        return found

    def buy_caption(self, run: RunState) -> tuple[str, bool]:
        if run.gold < RELIC_PRICE:
            return "Not enough Gold", False
        return "Buy", True

    def buy_rect(self, run: RunState, layout: ShopLayout, window: tuple[int, int]) -> pygame.Rect | None:
        if not self._ready() or self.dragging or self.selected_card_id is None:
            return None
        slot = next((item for item in self.slots(run, layout, window) if item.relic_id == self.selected_card_id), None)
        if slot is None:
            return None
        label, _enabled = self.buy_caption(run)
        price = f"{RELIC_PRICE} Gold"
        font = get_font(15, bold=True)
        width = max(slot.drawn.w, font.size(label)[0] + 28, font.size(price)[0] + 28)
        rect = pygame.Rect(0, 0, width, 34)
        rect.midtop = (slot.drawn.centerx, slot.drawn.bottom + 8)
        bounds = pygame.Rect(8, 8, max(1, window[0] - 16), max(1, window[1] - 16))
        rect.clamp_ip(bounds)
        return rect

    def wants_hand(self, run: RunState, layout: ShopLayout, window: tuple[int, int]) -> bool:
        if self.hovered_card_id is not None:
            return True
        rect = self.buy_rect(run, layout, window)
        return rect is not None and rect.collidepoint(self._pointer)

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
        if not self._ready():
            self.hovered_card_id = None
            return
        button_held = self._armed if held is None else bool(held)
        if button_held and self.drag_start_position is not None and self.dragged_card_id is None:
            if past_drag_threshold(self.drag_start_position, pos):
                self.dragging = True
                self.dragged_card_id = self._pressed_id
        if self.dragging and self.dragged_card_id is not None:
            dx = pos[0] - previous[0]
            self._vel_x = self._vel_x * 0.35 + dx * 0.65
            self._preview = self._drag_preview(run, layout, pos[0])
            self.hovered_card_id = None
            return
        slot = self._slot_at(pos, run, layout, window)
        self.hovered_card_id = None if slot is None else slot.relic_id

    def on_left_down(self, pos: tuple[int, int], run: RunState, layout: ShopLayout, window: tuple[int, int]) -> bool:
        self._pointer = pos
        if not self._ready():
            return False
        button = self.buy_rect(run, layout, window)
        if button is not None and button.collidepoint(pos):
            self._press_buy = True
            self._armed = True
            self._pressed_id = None
            self.drag_start_position = None
            return True
        slot = self._slot_at(pos, run, layout, window)
        if slot is None:
            return False
        self._press_buy = False
        self._armed = True
        self._pressed_id = slot.relic_id
        self.drag_start_position = pos
        self.drag_offset = (pos[0] - slot.drawn.centerx, pos[1] - slot.drawn.centery)
        self.dragged_card_id = None
        self.dragging = False
        return True

    def on_left_up(self, pos: tuple[int, int], run: RunState, layout: ShopLayout, window: tuple[int, int]) -> bool:
        if not self._armed and not self.dragging:
            return False
        if self.dragging:
            self._drop(run, pos, layout)
            return True
        pressed = self._pressed_id
        buying = self._press_buy
        self._finish_gesture(keep_selection=True)
        if buying:
            button = self.buy_rect(run, layout, window)
            if button is not None and button.collidepoint(pos):
                self._purchase(run, layout, window)
            return True
        slot = self._slot_at(pos, run, layout, window)
        if pressed is not None and slot is not None and slot.relic_id == pressed:
            if self.selected_card_id == pressed:
                self.selected_card_id = None
            else:
                self.selected_card_id = pressed
        return True

    def paint(
        self,
        screen: pygame.Surface,
        assets: AssetManager,
        run: RunState,
        layout: ShopLayout,
        dx: int,
        alpha: int,
    ) -> None:
        window = screen.get_size()
        self._sync(run)
        if self._ready():
            slots = self.slots(run, layout, window)
            ordered = sorted(slots, key=lambda slot: self._rank(slot.relic_id))
            button = self.buy_rect(run, layout, window)
            for slot in ordered:
                shift = 0 if slot.relic_id == self.dragged_card_id else dx
                self._paint_slot(screen, assets, slot, shift, alpha)
            if self.hovered_card_id is not None and not self.dragging:
                for slot in slots:
                    if slot.relic_id != self.hovered_card_id:
                        continue
                    anchor = slot.drawn.move(dx, 0)
                    draw_relic_tooltip(screen, slot.definition, anchor, price=RELIC_PRICE, avoid=button)
                    break
            if button is not None:
                label, enabled = self.buy_caption(run)
                moved = button.move(dx, 0)
                draw_button(screen, moved, label, enabled=enabled, font_size=15)
                _blit_text(
                    screen,
                    f"{RELIC_PRICE} Gold",
                    get_font(14, bold=True),
                    (236, 220, 196),
                    center=(moved.centerx, moved.bottom + 12),
                )
        self._paint_flying(screen, assets)

    def _purchase(self, run: RunState, layout: ShopLayout, window: tuple[int, int]) -> None:
        relic_id = self.selected_card_id
        if relic_id is None or run.gold < RELIC_PRICE:
            return
        slot = next((item for item in self.slots(run, layout, window) if item.relic_id == relic_id), None)
        before = run.gold
        notice = run.buy_relic()
        if notice is None and run.gold == before - RELIC_PRICE:
            if slot is not None:
                self.flying = {"relic_id": relic_id, "rect": slot.drawn.copy(), "age": 0.0}
            self.selected_card_id = None
            self.hovered_card_id = None

    def _drop(self, run: RunState, pos: tuple[int, int], layout: ShopLayout) -> None:
        if self._inside(pos, layout) and self._preview:
            offers = set(self._offers(run))
            self.visual_order = [relic_id for relic_id in self._preview if relic_id in offers]
        selected = self.selected_card_id
        self._finish_gesture(keep_selection=False)
        self.selected_card_id = selected

    def _finish_gesture(self, keep_selection: bool) -> None:
        selected = self.selected_card_id
        self.dragging = False
        self.dragged_card_id = None
        self.drag_start_position = None
        self._pressed_id = None
        self._press_buy = False
        self._preview = None
        self._armed = False
        self._vel_x = 0.0
        if keep_selection:
            self.selected_card_id = selected

    def _offers(self, run: RunState) -> list[str]:
        relic_id = run.shop.relic_id
        if relic_id and not run.shop.relic_sold:
            return [relic_id]
        return []

    def _sync(self, run: RunState) -> None:
        offers = self._offers(run)
        if self._serial != run.shop.offer_serial:
            self._serial = run.shop.offer_serial
            self.visual_order = list(offers)
            self.selected_card_id = None
            self.hovered_card_id = None
            self._finish_gesture(keep_selection=False)
            return
        kept = [relic_id for relic_id in self.visual_order if relic_id in offers]
        for relic_id in offers:
            if relic_id not in kept:
                kept.append(relic_id)
        self.visual_order = kept
        if self.selected_card_id not in self.visual_order:
            self.selected_card_id = None
        if self.hovered_card_id not in self.visual_order:
            self.hovered_card_id = None

    def _shown(self, run: RunState) -> list[str]:
        offers = set(self._offers(run))
        source = self._preview if self.dragging and self._preview else self.visual_order
        return [relic_id for relic_id in source if relic_id in offers]

    def _homes(self, run: RunState, layout: ShopLayout) -> list[tuple[str, pygame.Rect]]:
        ids = self._shown(run)
        if not ids or not layout.cards:
            return []
        base = relic_offer_slot(layout.cards[1])
        if len(ids) == 1:
            return [(ids[0], base)]
        gap = 10
        total = len(ids) * base.w + (len(ids) - 1) * gap
        left = base.centerx - total // 2
        homes = []
        for index, relic_id in enumerate(ids):
            rect = pygame.Rect(left + index * (base.w + gap), base.y, base.w, base.h)
            homes.append((relic_id, rect))
        return homes

    def _targets(self, run: RunState, layout: ShopLayout, window: tuple[int, int]) -> list[tuple[str, pygame.Rect, Motion]]:
        del window
        targets = []
        for relic_id, rest in self._homes(run, layout):
            targets.append((relic_id, rest, self._target(relic_id, rest)))
        return targets

    def _target(self, relic_id: str, rest: pygame.Rect) -> Motion:
        if relic_id == self.dragged_card_id:
            scale = CARD_ANIMATION["drag_scale"]
            centerx = self._pointer[0] - self.drag_offset[0]
            centery = self._pointer[1] - self.drag_offset[1] + CARD_ANIMATION["drag_lift"]
            bottom = centery + rest.h * scale / 2
            return Motion(centerx, bottom, scale, drag_angle(self._vel_x))
        if relic_id == self.selected_card_id:
            lift = CARD_ANIMATION["selected_lift"]
            scale = CARD_ANIMATION["selected_scale"]
        elif relic_id == self.hovered_card_id:
            lift = CARD_ANIMATION["hover_lift"]
            scale = CARD_ANIMATION["hover_scale"]
        else:
            lift = 0.0
            scale = 1.0
        return Motion(float(rest.centerx), rest.bottom + lift, scale, 0.0)

    def _drag_preview(self, run: RunState, layout: ShopLayout, mouse_x: float) -> list[str]:
        ids = list(self.visual_order)
        homes = self._homes(run, layout)
        if self.dragged_card_id not in ids:
            return ids
        return preview_order(ids, self.dragged_card_id, mouse_x, [rect.centerx for _relic_id, rect in homes])

    def _slot_at(self, pos: tuple[int, int], run: RunState, layout: ShopLayout, window: tuple[int, int]) -> ShopSlot | None:
        ranked = sorted(self.slots(run, layout, window), key=self._slot_key, reverse=True)
        for slot in ranked:
            if slot.drawn.collidepoint(pos):
                return slot
        return None

    def _slot_key(self, slot: ShopSlot) -> tuple[int, int]:
        return self._rank(slot.relic_id), self.visual_order.index(slot.relic_id) if slot.relic_id in self.visual_order else 0

    def _rank(self, relic_id: str) -> int:
        if relic_id == self.dragged_card_id:
            return 3
        if relic_id == self.hovered_card_id:
            return 2
        if relic_id == self.selected_card_id:
            return 1
        return 0

    def _inside(self, pos: tuple[int, int], layout: ShopLayout) -> bool:
        return layout.background.collidepoint(pos)

    def _ready(self) -> bool:
        return shop_reveal.face_up and shop_reveal.progress >= 1.0

    def _paint_slot(self, screen: pygame.Surface, assets: AssetManager, slot: ShopSlot, dx: int, alpha: int) -> None:
        rect = slot.drawn.move(dx, 0)
        dragged = slot.relic_id == self.dragged_card_id
        _shadow(screen, rect, dragged, slot.angle)
        image = self.cards.mini_surface(assets, slot.definition, slot.rest.w, slot.rest.h, "active")
        if image.get_size() != rect.size:
            image = pygame.transform.smoothscale(image, rect.size)
        else:
            image = image.copy()
        if slot.relic_id == self.selected_card_id:
            pygame.draw.rect(image, (214, 170, 90), image.get_rect().inflate(-2, -2), width=2, border_radius=8)
        if alpha < 255:
            image = image.copy()
            image.set_alpha(alpha)
        _rotated(screen, image, rect.center, slot.angle)
        if slot.relic_id == self.hovered_card_id and not dragged:
            draw_relic_glow(screen, rect)

    def _paint_flying(self, screen: pygame.Surface, assets: AssetManager) -> None:
        flying = self.flying
        if not flying:
            return
        definition = relic_by_id(flying["relic_id"])
        rect: pygame.Rect = flying["rect"]
        if definition is None:
            return
        age = flying.get("age", 0.0)
        blend = min(1.0, age / 0.36)
        scale = 1.0 + 0.12 * math.sin(blend * math.pi)
        size = (max(1, int(rect.w * scale)), max(1, int(rect.h * scale)))
        image = self.cards.mini_surface(assets, definition, rect.w, rect.h, "active")
        image = pygame.transform.smoothscale(image, size).copy()
        image.set_alpha(int(255 * (1.0 - blend)))
        screen.blit(image, image.get_rect(center=rect.center))


def _shadow(screen: pygame.Surface, rect: pygame.Rect, strong: bool, angle: float) -> None:
    alpha = 150 if strong else 80
    offset = 8 if strong else 4
    shadow = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (16, 10, 6, alpha), shadow.get_rect(), border_radius=max(6, rect.w // 16))
    _rotated(screen, shadow, (rect.centerx + offset, rect.centery + offset), angle)


def _rotated(screen: pygame.Surface, image: pygame.Surface, center: tuple[int, int], angle: float) -> None:
    if abs(angle) > 0.2:
        image = pygame.transform.rotate(image, angle)
    screen.blit(image, image.get_rect(center=center))


shop_hand = ShopRelicHand()
