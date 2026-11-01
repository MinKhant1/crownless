import math
from dataclasses import dataclass

import pygame

from config.settings import RELIC_BAR_SLOTS, RELIC_CARD_HEIGHT, RELIC_CARD_WIDTH
from game.relics.events import RELIC_VISUAL_TRIGGER
from game.relics.relic_data import RelicDef, relic_by_id
from game.relics.relic_manager import OwnedRelic
from game.run_state import RunState
from game.traits import trait_name
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
from rendering.layout import Layout
from rendering.relic_card import RelicCardRenderer
from rendering.relic_tooltip_renderer import draw_relic_tooltip


FLASH_MS = 520


@dataclass
class RelicSlot:
    owned: OwnedRelic
    definition: RelicDef
    state: str
    rest: pygame.Rect
    drawn: pygame.Rect
    pulse: float
    angle: float = 0.0


@dataclass
class _Pose:
    owned: OwnedRelic
    definition: RelicDef
    state: str
    rest: pygame.Rect
    motion: Motion
    pulse: float


class RelicBar:
    def __init__(self) -> None:
        self.cards = RelicCardRenderer()
        self.scroll = 0
        self.hovered_card_id: str | None = None
        self.selected_card_id: str | None = None
        self.dragged_card_id: str | None = None
        self.drag_start_position: tuple[int, int] | None = None
        self.drag_offset = (0, 0)
        self.detail_id: str | None = None
        self.detail_piece: int | None = None
        self.notice = ""
        self.armed = False
        self.clicked: RelicSlot | None = None
        self.flashes: dict[str, int] = {}
        self.flash_note = ""
        self.flash_note_until = 0
        self._bound = None
        self._motion: dict[str, Motion] = {}
        self._preview_ids: list[str] | None = None
        self._pointer = (0, 0)
        self._vel_x = 0.0
        self._pressed_id: str | None = None
        self.dragging = False

    def bind(self, run: RunState) -> None:
        dispatcher = run.relics.dispatcher
        if dispatcher is self._bound:
            return
        self._bound = dispatcher
        dispatcher.subscribe(RELIC_VISUAL_TRIGGER, self._on_visual, priority=90)
        self.scroll = 0
        self.hovered_card_id = None
        self.selected_card_id = None
        self._cancel_gesture()
        self._motion.clear()
        self.close_detail()
        self.flashes.clear()

    def clear(self) -> None:
        self.cards.clear()

    def cancel_pointer(self) -> None:
        self._cancel_gesture()

    def close_detail(self) -> None:
        self.detail_id = None
        self.detail_piece = None
        self.notice = ""

    @property
    def hover_id(self) -> str | None:
        return self.hovered_card_id

    @hover_id.setter
    def hover_id(self, value: str | None) -> None:
        self.hovered_card_id = value

    @property
    def pointer_captured(self) -> bool:
        return self.armed or self.dragging or self.detail_id is not None

    def ordered(self, run: RunState) -> list[OwnedRelic]:
        return run.ordered_relics()

    def visible(self, run: RunState) -> list[OwnedRelic]:
        items = self._sequence(run)
        self.scroll = _clamp_scroll(self.scroll, len(items))
        return items[self.scroll : self.scroll + RELIC_BAR_SLOTS]

    def update(self, dt: float, run: RunState, layout: Layout) -> None:
        if self.dragging and dt > 0:
            self._vel_x *= math.exp(-12.0 * dt)
        window = layout.window
        live: set[str] = set()
        for pose in self._poses(run, layout, pygame.time.get_ticks()):
            live.add(pose.owned.instance_id)
            speed = CARD_ANIMATION["drag_speed"] if pose.owned.instance_id == self.dragged_card_id else CARD_ANIMATION["animation_speed"]
            moved = step_motion(self._motion.get(pose.owned.instance_id), pose.motion, dt, speed)
            self._motion[pose.owned.instance_id] = anchored(moved, pose.rest, window)
        for key in list(self._motion):
            if key not in live:
                self._motion.pop(key, None)

    def pulse(self, instance_id: str, now: int) -> float:
        start = self.flashes.get(instance_id)
        if start is None:
            return 0.0
        elapsed = now - start
        if elapsed >= FLASH_MS:
            self.flashes.pop(instance_id, None)
            return 0.0
        return math.sin(elapsed / FLASH_MS * math.pi)

    def placements(self, run: RunState, layout: Layout, now: int) -> list[RelicSlot]:
        slots: list[RelicSlot] = []
        for pose in self._poses(run, layout, now):
            motion = self._motion.get(pose.owned.instance_id, pose.motion)
            drawn = placed_rect(motion, pose.rest, layout.window)
            slots.append(RelicSlot(pose.owned, pose.definition, pose.state, pose.rest, drawn, pose.pulse, motion.angle))
        return slots

    def arrow_rects(self, layout: Layout, count: int) -> tuple[pygame.Rect | None, pygame.Rect | None]:
        if count <= RELIC_BAR_SLOTS:
            return None, None
        size = max(22, min(32, layout.relics.h // 3))
        left = pygame.Rect(0, 0, size, size)
        right = pygame.Rect(0, 0, size, size)
        left.midleft = (layout.relics.x + 4, layout.relics.centery)
        right.midright = (layout.relics.right - 4, layout.relics.centery)
        return left, right

    def hits(self, pos: tuple[int, int], run: RunState, layout: Layout, now: int | None = None) -> bool:
        if self.detail_id is not None:
            return True
        if self._arrow_at(pos, run, layout) is not None:
            return True
        return self._slot_at(pos, run, layout, now) is not None

    def on_motion(
        self,
        run: RunState,
        pos: tuple[int, int],
        layout: Layout,
        now: int | None = None,
        held: bool | None = None,
    ) -> None:
        previous = self._pointer
        button_held = self.armed if held is None else bool(held)
        if self.detail_id is not None or self._arrow_at(pos, run, layout) is not None and not self.dragging:
            self._pointer = pos
            self.hovered_card_id = None
            return
        if button_held and self.drag_start_position is not None and self.dragged_card_id is None:
            if past_drag_threshold(self.drag_start_position, pos):
                self.dragging = True
                self.dragged_card_id = self._pressed_id
        self._pointer = pos
        if self.dragging and self.dragged_card_id is not None:
            dx = pos[0] - previous[0]
            self._vel_x = self._vel_x * 0.35 + dx * 0.65
            self._preview_ids = self._drag_preview(run, layout, pos[0])
            self.hovered_card_id = None
            return
        slot = self._slot_at(pos, run, layout, now)
        self.hovered_card_id = None if slot is None else slot.owned.instance_id

    def on_wheel(self, run: RunState, layout: Layout, pos: tuple[int, int], delta: int) -> bool:
        if self.detail_id is not None or self.dragging or delta == 0:
            return False
        if not layout.relics.collidepoint(pos):
            return False
        if len(self.ordered(run)) <= RELIC_BAR_SLOTS:
            return False
        self.scroll += -1 if delta > 0 else 1
        self.scroll = _clamp_scroll(self.scroll, len(self.ordered(run)))
        return True

    def on_left_down(self, pos: tuple[int, int], run: RunState, layout: Layout, now: int | None = None) -> bool:
        if self.detail_id is not None:
            self.armed = True
            return True
        if not self.hits(pos, run, layout, now):
            return False
        self.armed = True
        self._pointer = pos
        self.drag_start_position = None
        self.dragged_card_id = None
        self.dragging = False
        self._pressed_id = None
        if self._arrow_at(pos, run, layout) is not None:
            return True
        slot = self._slot_at(pos, run, layout, now)
        if slot is None:
            return True
        self._pressed_id = slot.owned.instance_id
        self.drag_start_position = pos
        self.drag_offset = (pos[0] - slot.drawn.centerx, pos[1] - slot.drawn.centery)
        return True

    def on_left_up(self, run: RunState, pos: tuple[int, int], layout: Layout, window: tuple[int, int], now: int | None = None) -> bool:
        if self.detail_id is not None:
            self._click_detail(run, pos, window)
            self._cancel_gesture()
            return True
        if not self.armed and not self.dragging:
            return False
        if self.dragging:
            self._drop(run)
            return True
        pressed = self._pressed_id
        self._cancel_gesture()
        arrow = self._arrow_at(pos, run, layout)
        if arrow is not None:
            direction = -1 if arrow == "left" else 1
            self.scroll = _clamp_scroll(self.scroll + direction, len(self.ordered(run)))
            return True
        slot = self._slot_at(pos, run, layout, now)
        if pressed is not None and slot is not None and slot.owned.instance_id == pressed:
            if self.selected_card_id == pressed:
                self.selected_card_id = None
            else:
                self.selected_card_id = pressed
        return True

    def consume_click(self) -> RelicSlot | None:
        slot = self.clicked
        self.clicked = None
        return slot

    def on_right_click(self) -> bool:
        if self.detail_id is None:
            return False
        self.close_detail()
        return True

    def draw_cards(self, screen: pygame.Surface, assets: AssetManager, run: RunState, layout: Layout, now: int | None = None) -> None:
        moment = pygame.time.get_ticks() if now is None else now
        _draw_relic_well(screen, layout.relics)
        if not run.relics.owned:
            return
        slots = self.placements(run, layout, moment)
        ordered = sorted(enumerate(slots), key=lambda pair: (self._rank(pair[1].owned.instance_id), pair[0]))
        resting = [slot for _index, slot in ordered if slot.owned.instance_id != self.dragged_card_id]
        for slot in resting:
            self._paint_slot(screen, assets, slot)
        left, right = self.arrow_rects(layout, len(self.ordered(run)))
        if left is not None and right is not None:
            draw_button(screen, left, "<", enabled=self.scroll > 0, font_size=16)
            draw_button(screen, right, ">", enabled=self.scroll < len(self.ordered(run)) - RELIC_BAR_SLOTS, font_size=16)
        if self.flash_note and moment < self.flash_note_until:
            _blit_text(
                screen,
                self.flash_note,
                get_font(16, bold=True),
                (236, 210, 140),
                center=(layout.relics.centerx, max(18, layout.relics.top - 14)),
            )

    def draw_overlay(self, screen: pygame.Surface, assets: AssetManager, run: RunState, layout: Layout, now: int | None = None) -> None:
        if self.detail_id is not None:
            self._draw_detail(screen, assets, run, screen.get_size())
            return
        moment = pygame.time.get_ticks() if now is None else now
        if self.dragged_card_id is not None:
            for slot in self.placements(run, layout, moment):
                if slot.owned.instance_id == self.dragged_card_id:
                    self._paint_slot(screen, assets, slot)
                    return
            return
        if self.hovered_card_id is None:
            return
        for slot in self.placements(run, layout, moment):
            if slot.owned.instance_id != self.hovered_card_id:
                continue
            draw_relic_tooltip(screen, slot.definition, slot.drawn)
            return

    def _on_visual(self, event) -> None:
        instance_id = event.payload.get("relic_instance_id")
        if instance_id:
            self.flashes[instance_id] = pygame.time.get_ticks()
        message = event.payload.get("message") or ""
        if message:
            self.flash_note = message
            self.flash_note_until = pygame.time.get_ticks() + 900

    def _slot_at(self, pos: tuple[int, int], run: RunState, layout: Layout, now: int | None) -> RelicSlot | None:
        moment = pygame.time.get_ticks() if now is None else now
        ranked = sorted(
            enumerate(self.placements(run, layout, moment)),
            key=lambda pair: (self._rank(pair[1].owned.instance_id), pair[0]),
            reverse=True,
        )
        for _index, slot in ranked:
            if slot.drawn.collidepoint(pos):
                return slot
        return None

    def _sequence(self, run: RunState) -> list[OwnedRelic]:
        saved = run.ordered_relics()
        if not self._preview_ids:
            return saved
        by_id = {item.instance_id: item for item in saved}
        preview = [by_id[instance_id] for instance_id in self._preview_ids if instance_id in by_id]
        seen = {item.instance_id for item in preview}
        preview.extend(item for item in saved if item.instance_id not in seen)
        return preview

    def _poses(self, run: RunState, layout: Layout, now: int) -> list[_Pose]:
        shown = self.visible(run)
        scrolling = len(self.ordered(run)) > RELIC_BAR_SLOTS
        rests = rest_rects(layout.relics, len(shown), scrolling)
        poses: list[_Pose] = []
        for owned, rest in zip(shown, rests):
            definition = relic_by_id(owned.relic_id)
            if definition is None:
                continue
            amount = self.pulse(owned.instance_id, now)
            poses.append(_Pose(owned, definition, card_state(run, owned), rest, self._target(owned.instance_id, rest, amount), amount))
        return poses

    def _target(self, instance_id: str, rest: pygame.Rect, pulse: float) -> Motion:
        kind = "idle"
        if instance_id == self.dragged_card_id:
            kind = "drag"
        elif instance_id == self.selected_card_id:
            kind = "selected"
        elif instance_id == self.hovered_card_id:
            kind = "hover"
        if kind == "drag":
            scale = CARD_ANIMATION["drag_scale"]
            centerx = self._pointer[0] - self.drag_offset[0]
            centery = self._pointer[1] - self.drag_offset[1] + CARD_ANIMATION["drag_lift"]
            height = rest.h * scale
            bottom = centery + height / 2
            angle = drag_angle(self._vel_x)
        else:
            if kind == "selected":
                lift = CARD_ANIMATION["selected_lift"]
                scale = CARD_ANIMATION["selected_scale"]
            elif kind == "hover":
                lift = CARD_ANIMATION["hover_lift"]
                scale = CARD_ANIMATION["hover_scale"]
            else:
                lift = 0.0
                scale = 1.0
            lift += -8.0 * pulse
            scale *= 1.0 + 0.04 * pulse
            centerx = float(rest.centerx)
            bottom = rest.bottom + lift
            angle = 0.0
        return Motion(centerx, bottom, scale, angle)

    def _rank(self, instance_id: str) -> int:
        if instance_id == self.dragged_card_id:
            return 3
        if instance_id == self.hovered_card_id:
            return 2
        if instance_id == self.selected_card_id:
            return 1
        return 0

    def _drag_preview(self, run: RunState, layout: Layout, mouse_x: float) -> list[str]:
        full = [item.instance_id for item in run.ordered_relics()]
        start = self.scroll
        visible_ids = full[start : start + RELIC_BAR_SLOTS]
        if self.dragged_card_id not in visible_ids:
            return full
        scrolling = len(full) > RELIC_BAR_SLOTS
        rests = rest_rects(layout.relics, len(visible_ids), scrolling)
        preview = preview_order(visible_ids, self.dragged_card_id, mouse_x, [rect.centerx for rect in rests])
        return full[:start] + preview + full[start + len(visible_ids) :]

    def _drop(self, run: RunState) -> None:
        if self._preview_ids:
            run.set_relic_order(self._preview_ids)
        selected = self.selected_card_id
        self._cancel_gesture()
        self.selected_card_id = selected

    def _paint_slot(self, screen: pygame.Surface, assets: AssetManager, slot: RelicSlot) -> None:
        dragged = slot.owned.instance_id == self.dragged_card_id
        _blit_shadow(screen, slot.drawn, strong=dragged, angle=slot.angle)
        image = self.cards.mini_surface(assets, slot.definition, slot.rest.w, slot.rest.h, slot.state)
        if image.get_size() != slot.drawn.size:
            image = pygame.transform.smoothscale(image, slot.drawn.size)
        else:
            image = image.copy()
        if slot.owned.instance_id == self.selected_card_id:
            pygame.draw.rect(image, (214, 170, 90), image.get_rect().inflate(-2, -2), width=2, border_radius=8)
        _blit_rotated(screen, image, slot.drawn.center, slot.angle)
        if slot.owned.instance_id == self.hovered_card_id and self.detail_id is None and not dragged:
            draw_relic_glow(screen, slot.drawn)
        if slot.pulse > 0:
            _blit_gold(screen, slot.drawn, slot.pulse)

    def _cancel_gesture(self) -> None:
        self.dragging = False
        self.dragged_card_id = None
        self.drag_start_position = None
        self._pressed_id = None
        self._preview_ids = None
        self.armed = False
        self._vel_x = 0.0

    def _arrow_at(self, pos: tuple[int, int], run: RunState, layout: Layout) -> str | None:
        left, right = self.arrow_rects(layout, len(self.ordered(run)))
        if left is not None and left.collidepoint(pos):
            return "left"
        if right is not None and right.collidepoint(pos):
            return "right"
        return None

    def _click_detail(self, run: RunState, pos: tuple[int, int], window: tuple[int, int]) -> None:
        panel, _card, pieces, button, close = _detail_geometry(run, window)
        if close.collidepoint(pos) or not panel.collidepoint(pos):
            self.close_detail()
            return
        owned = _owned_by_instance(run, self.detail_id)
        definition = None if owned is None else relic_by_id(owned.relic_id)
        if owned is None or definition is None or definition.trigger != "on_activate":
            return
        allowed, _message = run.relics.can_activate(owned.instance_id)
        if not allowed:
            return
        for piece, rect in pieces:
            if rect.collidepoint(pos):
                self.detail_piece = piece.id
                return
        if button.collidepoint(pos) and self.detail_piece is not None:
            result = run.relics.activate(owned.instance_id, self.detail_piece)
            if result is not None and result.ok:
                self.close_detail()
                return
            self.notice = "" if result is None else result.message

    def _draw_detail(self, screen: pygame.Surface, assets: AssetManager, run: RunState, window: tuple[int, int]) -> None:
        owned = _owned_by_instance(run, self.detail_id)
        definition = None if owned is None else relic_by_id(owned.relic_id)
        if owned is None or definition is None:
            self.close_detail()
            return
        shade = pygame.Surface(window, pygame.SRCALPHA)
        shade.fill((12, 8, 6, 160))
        screen.blit(shade, (0, 0))
        panel, card, pieces, button, close = _detail_geometry(run, window)
        pygame.draw.rect(screen, (42, 28, 20), panel, border_radius=14)
        pygame.draw.rect(screen, (214, 170, 90), panel, width=3, border_radius=14)
        draw_button(screen, close, "Close", font_size=14)
        self.cards.draw(screen, assets, definition, card, owned=True)
        if definition.trigger == "on_activate":
            allowed, message = run.relics.can_activate(owned.instance_id)
            if allowed:
                for piece, rect in pieces:
                    draw_button(screen, rect, _piece_label(piece), font_size=14)
                    if piece.id == self.detail_piece:
                        pygame.draw.rect(screen, (232, 196, 96), rect, width=3, border_radius=10)
                draw_button(screen, button, "Activate", enabled=self.detail_piece is not None, font_size=16)
            elif message:
                _blit_text(screen, message, get_font(16), (214, 140, 110), center=(panel.centerx, card.bottom + 28))
        if self.notice:
            _blit_text(screen, self.notice, get_font(15), (214, 120, 96), center=(panel.centerx, panel.bottom - 18))


def card_state(run: RunState, owned: OwnedRelic) -> str:
    definition = relic_by_id(owned.relic_id)
    if definition is None:
        return "active"
    if definition.trigger == "on_activate":
        if owned.state.get("spent"):
            return "used"
        effect = run.relics.effect_for(definition.id)
        if effect is not None and hasattr(effect, "can_activate"):
            allowed, _message = effect.can_activate(run.relics.context)
            if not allowed:
                return "disabled"
        return "active"
    if owned.state.get("used_this_battle"):
        return "used"
    return "active"


def rest_rects(band: pygame.Rect, count: int, scrolling: bool) -> list[pygame.Rect]:
    count = max(0, min(RELIC_BAR_SLOTS, count))
    if count == 0:
        return []
    inset = 36 if scrolling else 8
    available = max(1, band.w - inset * 2)
    gap = -12 if count >= 5 else (8 if available > 420 else 4)
    card_h = max(48, min(RELIC_CARD_HEIGHT, band.h - 8))
    card_w = max(36, int(round(card_h * RELIC_CARD_WIDTH / RELIC_CARD_HEIGHT)))
    total = count * card_w + (count - 1) * gap
    if total > available:
        gap = 4
        card_w = max(36, (available - (count - 1) * gap) // count)
        card_h = max(48, int(round(card_w * RELIC_CARD_HEIGHT / RELIC_CARD_WIDTH)))
        if card_h > band.h - 8:
            card_h = max(48, band.h - 8)
            card_w = max(36, int(round(card_h * RELIC_CARD_WIDTH / RELIC_CARD_HEIGHT)))
        total = count * card_w + (count - 1) * gap
    left = band.x + inset + max(0, (available - total) // 2)
    top = band.bottom - card_h - 4
    return [pygame.Rect(left + index * (card_w + gap), top, card_w, card_h) for index in range(count)]


def detail_panel(window: tuple[int, int]) -> pygame.Rect:
    rect = pygame.Rect(0, 0, min(360, window[0] - 48), min(680, window[1] - 48))
    rect.center = (window[0] // 2, window[1] // 2)
    return rect


def _clamp_scroll(scroll: int, count: int) -> int:
    return max(0, min(scroll, max(0, count - RELIC_BAR_SLOTS)))


def _owned_by_instance(run: RunState, instance_id: str | None) -> OwnedRelic | None:
    if instance_id is None:
        return None
    for owned in run.relics.owned:
        if owned.instance_id == instance_id:
            return owned
    return None


def _piece_label(piece) -> str:
    label = piece.kind.capitalize()
    if piece.trait:
        return f"{label} {trait_name(piece.trait)}"
    return label


def _detail_geometry(run: RunState, window: tuple[int, int]):
    panel = detail_panel(window)
    pieces = [piece for piece in run.army.pieces if piece.kind != "king"]
    rows = max(1, (len(pieces) + 1) // 2)
    controls = rows * 36 + 64
    card_h = max(160, min(360, panel.h - 70 - controls))
    card = pygame.Rect(panel.x + 24, panel.y + 52, panel.w - 48, card_h)
    width = min(150, (panel.w - 58) // 2)
    buttons = []
    for index, piece in enumerate(pieces):
        column = index % 2
        row = index // 2
        rect = pygame.Rect(panel.x + 24 + column * (width + 10), card.bottom + 12 + row * 36, width, 30)
        buttons.append((piece, rect))
    close = pygame.Rect(panel.right - 92, panel.y + 12, 76, 30)
    return panel, card, buttons, _activate_rect(panel), close


def _activate_rect(panel: pygame.Rect) -> pygame.Rect:
    rect = pygame.Rect(0, 0, min(180, panel.w - 48), 36)
    rect.midbottom = (panel.centerx, panel.bottom - 36)
    return rect


def _draw_relic_well(screen: pygame.Surface, rect: pygame.Rect) -> None:
    plate = pygame.Surface((max(1, rect.w), max(1, rect.h)), pygame.SRCALPHA)
    pygame.draw.rect(plate, (236, 220, 196, 72), plate.get_rect(), border_radius=14)
    pygame.draw.rect(plate, (214, 170, 90, 190), plate.get_rect(), width=2, border_radius=14)
    screen.blit(plate, rect.topleft)


def _blit_shadow(screen: pygame.Surface, rect: pygame.Rect, strong: bool = False, angle: float = 0.0) -> None:
    alpha = 150 if strong else 80
    offset = 8 if strong else 4
    shadow = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (16, 10, 6, alpha), shadow.get_rect(), border_radius=max(6, rect.w // 16))
    _blit_rotated(screen, shadow, (rect.centerx + offset, rect.centery + offset), angle)


def _blit_rotated(screen: pygame.Surface, image: pygame.Surface, center: tuple[int, int], angle: float) -> None:
    if abs(angle) > 0.2:
        image = pygame.transform.rotate(image, angle)
    screen.blit(image, image.get_rect(center=center))


def _blit_gold(screen: pygame.Surface, rect: pygame.Rect, pulse: float) -> None:
    glow = pygame.Surface((rect.w + 8, rect.h + 8), pygame.SRCALPHA)
    color = (232, 196, 96, int(210 * pulse))
    pygame.draw.rect(glow, color, glow.get_rect(), width=3, border_radius=10)
    screen.blit(glow, (rect.x - 4, rect.y - 4))
