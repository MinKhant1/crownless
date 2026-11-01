import pygame

from game.relics.relic_data import relic_by_id
from game.traits import trait_name
from game.run_state import RunState
from game.transitions.easing import ease_out_cubic
from rendering.asset_manager import AssetManager
from rendering.hud_renderer import _blit_text, draw_button, draw_relic_glow, get_font
from rendering.relic_card import RelicCardRenderer
from rendering.special_piece_renderer import special_pieces
from rendering.relic_tooltip_renderer import draw_relic_tooltip


class CollectionOverlay:
    def __init__(self) -> None:
        self.cards = RelicCardRenderer()
        self.age = 0.0
        self.hover = -1
        self._open: str | None = None
        self._armed = False

    def blocks(self, run: RunState) -> bool:
        return run.shop.collection_open in ("relic", "piece")

    def update(self, dt: float, run: RunState) -> None:
        kind = run.shop.collection_open if run.shop.collection_open in ("relic", "piece") else None
        if kind != self._open:
            self._open = kind
            self.age = 0.0
            self.hover = -1
            self._armed = False
        if kind is not None:
            self.age += max(0.0, dt)

    def on_motion(self, pos: tuple[int, int], run: RunState, window: tuple[int, int]) -> None:
        self.hover = -1
        if not self.blocks(run):
            return
        for index, rect in enumerate(self._card_rects(run, window)):
            if self._shown(index) and rect.collidepoint(pos):
                self.hover = index

    def on_left_down(self, pos: tuple[int, int], run: RunState, window: tuple[int, int]) -> bool:
        if not self.blocks(run):
            return False
        self._armed = True
        return True

    def on_left_up(self, pos: tuple[int, int], run: RunState, window: tuple[int, int]) -> bool:
        if not self._armed and not self.blocks(run):
            return False
        self._armed = False
        if not self.blocks(run):
            return False
        button = self._confirm_rect(window)
        if button.collidepoint(pos):
            if run.shop.collection_pick is not None:
                run.confirm_collection()
            return True
        for index, rect in enumerate(self._card_rects(run, window)):
            if self._shown(index) and rect.collidepoint(pos):
                run.shop.collection_pick = index
                return True
        run.shop.collection_open = None
        return True

    def paint(self, screen: pygame.Surface, assets: AssetManager, run: RunState) -> None:
        if not self.blocks(run):
            return
        window = screen.get_size()
        title = "Choose a Relic" if run.shop.collection_open == "relic" else "Choose a Piece"
        _blit_text(screen, title, get_font(32, bold=True), (245, 232, 210), center=(window[0] // 2, int(window[1] * 0.18)))
        choices = self._choices(run)
        rects = self._card_rects(run, window)
        for index, rect in enumerate(rects):
            if index >= len(choices) or not self._shown(index):
                continue
            shown = rect.move(0, -12 if run.shop.collection_pick == index else 0)
            progress = self._progress(index)
            self._paint_card(screen, assets, run, choices[index], shown, progress, index)
        if self.age > 0.45:
            button = self._confirm_rect(window)
            draw_button(screen, button, "Confirm Choice", enabled=run.shop.collection_pick is not None, font_size=18)
        if run.shop.collection_open == "relic" and 0 <= self.hover < len(choices):
            definition = relic_by_id(choices[self.hover])
            if definition is not None:
                anchor = rects[self.hover]
                draw_relic_tooltip(screen, definition, anchor)

    def _choices(self, run: RunState) -> list[str]:
        if run.shop.collection_open == "relic":
            return list(run.shop.relic_choices or ())
        return list(run.shop.piece_choices or ())

    def _card_rects(self, run: RunState, window: tuple[int, int]) -> list[pygame.Rect]:
        count = max(1, len(self._choices(run)))
        relic = run.shop.collection_open == "relic"
        height = int(window[1] * (0.56 if relic else 0.42))
        if not relic:
            height = min(280, height)
        width = int(height * (2 / 3 if relic else 0.78))
        gap = max(18, int(window[0] * 0.03))
        total = count * width + (count - 1) * gap
        limit = max(1, window[0] - 48)
        if total > limit:
            scale = limit / total
            width = max(1, int(width * scale))
            height = max(1, int(height * scale))
            total = count * width + (count - 1) * gap
        left = window[0] // 2 - total // 2
        top = int(window[1] * (0.20 if relic else 0.28))
        return [pygame.Rect(left + index * (width + gap), top, width, height) for index in range(count)]

    def _confirm_rect(self, window: tuple[int, int]) -> pygame.Rect:
        rect = pygame.Rect(0, 0, 220, 48)
        rect.center = (window[0] // 2, int(window[1] * 0.82))
        return rect

    def _progress(self, index: int) -> float:
        local = (self.age - index * 0.16) / 0.28
        return ease_out_cubic(max(0.0, min(1.0, local)))

    def _shown(self, index: int) -> bool:
        return self.age >= index * 0.16

    def _paint_card(
        self,
        screen: pygame.Surface,
        assets: AssetManager,
        run: RunState,
        choice: str,
        rect: pygame.Rect,
        progress: float,
        index: int,
    ) -> None:
        scale = 0.92 + 0.08 * progress
        drawn = pygame.Rect(0, 0, max(1, int(rect.w * scale)), max(1, int(rect.h * scale)))
        drawn.center = (rect.centerx, rect.centery + int((1.0 - progress) * 24))
        if run.shop.collection_open == "relic":
            definition = relic_by_id(choice)
            if definition is None:
                return
            image = self.cards.mini_surface(assets, definition, rect.w, rect.h, "active")
            image = pygame.transform.smoothscale(image, drawn.size).copy()
        else:
            traits = run.shop.piece_choice_traits or ()
            trait = traits[index] if index < len(traits) else None
            image, piece_rect = _piece_card(assets, choice, drawn.size, trait)
            piece_rect = piece_rect.move(drawn.topleft)
        if run.shop.collection_open == "relic" and run.shop.collection_pick == index:
            pygame.draw.rect(image, (232, 196, 96), image.get_rect().inflate(-6, -6), width=3, border_radius=10)
        image.set_alpha(int(255 * progress))
        screen.blit(image, drawn.topleft)
        if run.shop.collection_open != "relic" and run.shop.collection_pick == index:
            pygame.draw.rect(screen, (232, 196, 96), piece_rect.inflate(10, 10), width=3, border_radius=8)
        if self.hover == index:
            draw_relic_glow(screen, drawn)


def _piece_card(
    assets: AssetManager,
    kind: str,
    size: tuple[int, int],
    trait: str | None = None,
) -> tuple[pygame.Surface, pygame.Rect]:
    surface = pygame.Surface(size, pygame.SRCALPHA)
    image = special_pieces.image(assets, "white", kind, trait, int(size[0] * 0.78))
    piece_rect = image.get_rect(center=(size[0] // 2, int(size[1] * 0.40)))
    surface.blit(image, piece_rect)
    font = get_font(max(16, size[1] // 12), bold=True)
    name = trait_name(trait)
    title = f"{name} {kind.capitalize()}" if name else kind.capitalize()
    text = font.render(title, True, (245, 232, 210))
    surface.blit(text, text.get_rect(center=(size[0] // 2, int(size[1] * 0.82))))
    return surface, piece_rect


collection_overlay = CollectionOverlay()
