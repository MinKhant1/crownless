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
from rendering.hud_renderer import _blit_text, draw_button, get_font
from rendering.layout import Layout
from rendering.relic_card import RelicCardRenderer
from rendering.relic_tooltip_renderer import draw_relic_tooltip


FLASH_MS = 520
HOVER_LIFT = 10
HOVER_SCALE = 1.08


@dataclass
class RelicSlot:
    owned: OwnedRelic
    definition: RelicDef
    state: str
    rest: pygame.Rect
    drawn: pygame.Rect
    pulse: float


class RelicBar:
    def __init__(self) -> None:
        self.cards = RelicCardRenderer()
        self.scroll = 0
        self.hover_id: str | None = None
        self.detail_id: str | None = None
        self.detail_piece: int | None = None
        self.notice = ""
        self.armed = False
        self.flashes: dict[str, int] = {}
        self._bound = None

    def bind(self, run: RunState) -> None:
        dispatcher = run.relics.dispatcher
        if dispatcher is self._bound:
            return
        self._bound = dispatcher
        dispatcher.subscribe(RELIC_VISUAL_TRIGGER, self._on_visual, priority=90)
        self.scroll = 0
        self.hover_id = None
        self.close_detail()
        self.flashes.clear()

    def clear(self) -> None:
        self.cards.clear()

    def close_detail(self) -> None:
        self.detail_id = None
        self.detail_piece = None
        self.notice = ""

    def ordered(self, run: RunState) -> list[OwnedRelic]:
        return sorted(run.relics.owned, key=lambda item: item.acquisition_order)

    def visible(self, run: RunState) -> list[OwnedRelic]:
        items = self.ordered(run)
        self.scroll = _clamp_scroll(self.scroll, len(items))
        return items[self.scroll : self.scroll + RELIC_BAR_SLOTS]

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
        shown = self.visible(run)
        scrolling = len(self.ordered(run)) > RELIC_BAR_SLOTS
        rests = rest_rects(layout.relics, len(shown), scrolling)
        slots: list[RelicSlot] = []
        for owned, rest in zip(shown, rests):
            definition = relic_by_id(owned.relic_id)
            if definition is None:
                continue
            amount = self.pulse(owned.instance_id, now)
            hovered = self.hover_id == owned.instance_id and self.detail_id is None
            lift = int(round(8 * amount))
            scale = 1.0 + 0.06 * amount
            if hovered:
                lift += HOVER_LIFT
                scale *= HOVER_SCALE
            drawn = pygame.Rect(0, 0, max(1, int(rest.w * scale)), max(1, int(rest.h * scale)))
            drawn.midbottom = (rest.centerx, rest.bottom - lift)
            slots.append(RelicSlot(owned, definition, card_state(run, owned), rest, drawn, amount))
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

    def on_motion(self, run: RunState, pos: tuple[int, int], layout: Layout, now: int | None = None) -> None:
        if self.detail_id is not None:
            self.hover_id = None
            return
        slot = self._slot_at(pos, run, layout, now)
        self.hover_id = None if slot is None else slot.owned.instance_id

    def on_wheel(self, run: RunState, layout: Layout, pos: tuple[int, int], delta: int) -> bool:
        if self.detail_id is not None or delta == 0:
            return False
        if not layout.relics.collidepoint(pos):
            return False
        if len(self.ordered(run)) <= RELIC_BAR_SLOTS:
            return False
        self.scroll += -1 if delta > 0 else 1
        self.scroll = _clamp_scroll(self.scroll, len(self.ordered(run)))
        return True

    def on_left_down(self, pos: tuple[int, int], run: RunState, layout: Layout, now: int | None = None) -> bool:
        if not self.hits(pos, run, layout, now):
            return False
        self.armed = True
        return True

    def on_left_up(self, run: RunState, pos: tuple[int, int], layout: Layout, window: tuple[int, int], now: int | None = None) -> bool:
        if self.detail_id is not None:
            self._click_detail(run, pos, window)
            self.armed = False
            return True
        if not self.armed:
            return False
        self.armed = False
        arrow = self._arrow_at(pos, run, layout)
        if arrow is not None:
            direction = -1 if arrow == "left" else 1
            self.scroll = _clamp_scroll(self.scroll + direction, len(self.ordered(run)))
            return True
        slot = self._slot_at(pos, run, layout, now)
        if slot is not None:
            self.detail_id = slot.owned.instance_id
            self.detail_piece = None
            self.notice = ""
        return True

    def on_right_click(self) -> bool:
        if self.detail_id is None:
            return False
        self.close_detail()
        return True

    def draw_cards(self, screen: pygame.Surface, assets: AssetManager, run: RunState, layout: Layout, now: int | None = None) -> None:
        moment = pygame.time.get_ticks() if now is None else now
        if not run.relics.owned:
            _blit_text(
                screen,
                "No Relics",
                get_font(max(14, layout.relics.h // 6)),
                (168, 140, 110),
                center=layout.relics.center,
            )
            return
        for slot in self.placements(run, layout, moment):
            _blit_shadow(screen, slot.drawn)
            image = self.cards.mini_surface(assets, slot.definition, slot.rest.w, slot.rest.h, slot.state)
            if image.get_size() != slot.drawn.size:
                image = pygame.transform.smoothscale(image, slot.drawn.size)
            screen.blit(image, slot.drawn.topleft)
            if slot.pulse > 0:
                _blit_gold(screen, slot.drawn, slot.pulse)
        left, right = self.arrow_rects(layout, len(self.ordered(run)))
        if left is not None and right is not None:
            draw_button(screen, left, "<", enabled=self.scroll > 0, font_size=16)
            draw_button(screen, right, ">", enabled=self.scroll < len(self.ordered(run)) - RELIC_BAR_SLOTS, font_size=16)

    def draw_overlay(self, screen: pygame.Surface, assets: AssetManager, run: RunState, layout: Layout, now: int | None = None) -> None:
        moment = pygame.time.get_ticks() if now is None else now
        if self.detail_id is not None:
            self._draw_detail(screen, assets, run, screen.get_size())
            return
        if self.hover_id is None:
            return
        for slot in self.placements(run, layout, moment):
            if slot.owned.instance_id == self.hover_id:
                draw_relic_tooltip(screen, slot.definition, slot.drawn, layout.relics)
                return

    def _on_visual(self, event) -> None:
        instance_id = event.payload.get("relic_instance_id")
        if instance_id:
            self.flashes[instance_id] = pygame.time.get_ticks()

    def _slot_at(self, pos: tuple[int, int], run: RunState, layout: Layout, now: int | None) -> RelicSlot | None:
        moment = pygame.time.get_ticks() if now is None else now
        for slot in self.placements(run, layout, moment):
            if slot.drawn.collidepoint(pos):
                return slot
        return None

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
    gap = 8 if available > 420 else 4
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


def _blit_shadow(screen: pygame.Surface, rect: pygame.Rect) -> None:
    shadow = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (16, 10, 6, 80), shadow.get_rect(), border_radius=max(6, rect.w // 16))
    screen.blit(shadow, (rect.x + 3, rect.y + 4))


def _blit_gold(screen: pygame.Surface, rect: pygame.Rect, pulse: float) -> None:
    glow = pygame.Surface((rect.w + 8, rect.h + 8), pygame.SRCALPHA)
    color = (232, 196, 96, int(210 * pulse))
    pygame.draw.rect(glow, color, glow.get_rect(), width=3, border_radius=10)
    screen.blit(glow, (rect.x - 4, rect.y - 4))
