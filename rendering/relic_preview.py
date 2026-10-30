import pygame

from game.relics.relic_data import RelicDef, relic_by_id
from game.transitions.easing import ease_out_cubic
from rendering.asset_manager import AssetManager
from rendering.hud_renderer import _blit_text, draw_button, get_font
from rendering.relic_card import CARD_RATIO, RelicCardRenderer


PREVIEW_SECONDS = 0.22
OVERLAY_ALPHA = 166


def preview_card_rect(window: tuple[int, int]) -> pygame.Rect:
    width_limit = min(window[0] * 0.55, window[0] * 0.84)
    height_limit = min(window[1] * 0.82, window[1] * 0.84)
    if width_limit / max(1.0, height_limit) > CARD_RATIO:
        height = height_limit
        width = height * CARD_RATIO
    else:
        width = width_limit
        height = width / CARD_RATIO
    rect = pygame.Rect(0, 0, max(1, int(width)), max(1, int(height)))
    bounds = pygame.Rect(
        int(window[0] * 0.08),
        int(window[1] * 0.08),
        max(1, int(window[0] * 0.84)),
        max(1, int(window[1] * 0.84)),
    )
    if rect.w > bounds.w:
        rect.w = bounds.w
        rect.h = max(1, int(rect.w / CARD_RATIO))
    if rect.h > bounds.h:
        rect.h = bounds.h
        rect.w = max(1, int(rect.h * CARD_RATIO))
    rect.center = bounds.center
    return rect


class RelicPreviewModal:
    def __init__(self) -> None:
        self.cards = RelicCardRenderer()
        self.relic_id: str | None = None
        self.instance_id: str | None = None
        self.origin = pygame.Rect(0, 0, 1, 1)
        self.open = False
        self.closing = False
        self.shown = 0.0
        self.pending_activate: str | None = None
        self._pressed = False
        self._frames: dict[tuple, pygame.Surface] = {}
        self.card_rect = pygame.Rect(0, 0, 1, 1)
        self.close_rect = pygame.Rect(0, 0, 1, 1)
        self.activate_rect: pygame.Rect | None = None

    @property
    def blocks(self) -> bool:
        return self.open or self.shown > 0.0

    @property
    def blend(self) -> float:
        if self.closing:
            return 1.0 - ease_out_cubic(1.0 - self.shown)
        return ease_out_cubic(self.shown)

    def clear(self) -> None:
        self._frames.clear()
        self.cards.clear()

    def show(self, relic_id: str, origin: pygame.Rect, instance_id: str | None = None) -> None:
        if self.open and not self.closing and self.relic_id == relic_id and self.instance_id == instance_id:
            self.request_close()
            return
        self.relic_id = relic_id
        self.instance_id = instance_id
        self.origin = origin.copy()
        self.open = True
        self.closing = False
        self.shown = 0.0
        self.pending_activate = None

    def request_close(self) -> None:
        if self.open:
            self.closing = True

    def dismiss(self) -> None:
        self.open = False
        self.closing = False
        self.shown = 0.0
        self.relic_id = None
        self.instance_id = None
        self._pressed = False

    def update(self, dt: float) -> None:
        if not self.blocks:
            return
        step = max(0.0, dt) / PREVIEW_SECONDS
        if self.closing or not self.open:
            self.shown = max(0.0, self.shown - step)
            if self.shown <= 0.0:
                self.dismiss()
        else:
            self.shown = min(1.0, self.shown + step)

    def on_escape(self) -> bool:
        if not self.blocks:
            return False
        if not self.closing:
            self.request_close()
        return True

    def on_event(self, event: pygame.event.Event, window: tuple[int, int]) -> bool:
        if not self.blocks:
            return False
        if event.type not in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEWHEEL):
            return False
        self._place(window)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._pressed = True
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._pressed and not self.closing:
                if self.close_rect.collidepoint(event.pos):
                    self.request_close()
                elif self.activate_rect is not None and self.activate_rect.collidepoint(event.pos):
                    self.pending_activate = self.instance_id
                    self.dismiss()
                elif not self.card_rect.collidepoint(event.pos):
                    self.request_close()
            self._pressed = False
            return True
        return True

    def draw(self, screen: pygame.Surface, assets: AssetManager) -> None:
        if not self.blocks or self.relic_id is None:
            return
        relic = relic_by_id(self.relic_id)
        if relic is None:
            self.dismiss()
            return
        window = screen.get_size()
        self._place(window, relic)
        amount = self.blend
        shade = pygame.Surface(window, pygame.SRCALPHA)
        shade.fill((0, 0, 0, int(OVERLAY_ALPHA * amount)))
        screen.blit(shade, (0, 0))
        shadow = pygame.Surface((self.card_rect.w, self.card_rect.h), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, int(120 * amount)), shadow.get_rect(), border_radius=18)
        screen.blit(shadow, (self.card_rect.x + 10, self.card_rect.y + 14))
        image = self._card(assets, relic, self._target(window).size)
        frame = image
        if frame.get_size() != self.card_rect.size:
            frame = pygame.transform.smoothscale(image, self.card_rect.size)
        alpha = int(255 * amount)
        if alpha < 255:
            frame = frame.copy()
            frame.set_alpha(alpha)
        screen.blit(frame, self.card_rect.topleft)
        if amount > 0.45:
            self._draw_close(screen, alpha)
            if self.activate_rect is not None:
                draw_button(screen, self.activate_rect, "Activate", font_size=16)

    def _target(self, window: tuple[int, int]) -> pygame.Rect:
        return preview_card_rect(window)

    def _place(self, window: tuple[int, int], relic: RelicDef | None = None) -> None:
        target = self._target(window)
        amount = self.blend
        self.card_rect = _lerp_rect(self.origin, target, amount)
        self.close_rect = pygame.Rect(0, 0, 36, 36)
        self.close_rect.center = (self.card_rect.right - 4, self.card_rect.top + 4)
        margin = 8
        self.close_rect.clamp_ip(pygame.Rect(margin, margin, max(1, window[0] - margin * 2), max(1, window[1] - margin * 2)))
        definition = relic if relic is not None else relic_by_id(self.relic_id or "")
        self.activate_rect = None
        if definition is not None and definition.trigger == "on_activate" and self.instance_id and amount > 0.45:
            button = pygame.Rect(0, 0, min(160, self.card_rect.w), 36)
            button.midtop = (self.card_rect.centerx, self.card_rect.bottom + 12)
            limit = window[1] - margin - button.h
            if button.y > limit:
                button.y = limit
            self.activate_rect = button

    def _card(self, assets: AssetManager, relic: RelicDef, size: tuple[int, int]) -> pygame.Surface:
        key = (relic.id, size[0], size[1])
        cached = self._frames.get(key)
        if cached is not None:
            return cached
        surface = pygame.Surface(size, pygame.SRCALPHA)
        self.cards.draw(surface, assets, relic, surface.get_rect())
        self._frames[key] = surface
        return surface

    def _draw_close(self, screen: pygame.Surface, alpha: int) -> None:
        plate = pygame.Surface(self.close_rect.size, pygame.SRCALPHA)
        pygame.draw.circle(plate, (42, 28, 20, alpha), plate.get_rect().center, 16)
        pygame.draw.circle(plate, (214, 170, 90, alpha), plate.get_rect().center, 16, width=2)
        screen.blit(plate, self.close_rect.topleft)
        _blit_text(screen, "X", get_font(16, bold=True), (245, 232, 210), center=self.close_rect.center)


def _lerp_rect(start: pygame.Rect, end: pygame.Rect, amount: float) -> pygame.Rect:
    amount = max(0.0, min(1.0, amount))

    def mix(a: int, b: int) -> int:
        return int(round(a + (b - a) * amount))

    rect = pygame.Rect(mix(start.x, end.x), mix(start.y, end.y), mix(start.w, end.w), mix(start.h, end.h))
    rect.w = max(1, rect.w)
    rect.h = max(1, rect.h)
    return rect
