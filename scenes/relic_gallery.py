import pygame

from game.relics.relic_data import RELICS, front_key, relic_by_id
from rendering.hud_renderer import _blit_text, draw_button, get_font
from rendering.relic_card import CARD_RATIO, RelicCardRenderer
from rendering.relic_flip import ShopReveal


class RelicGallery:
    def __init__(self) -> None:
        self.open = False
        self.cards = RelicCardRenderer()
        self.flips: dict[str, ShopReveal] = {}
        self.scroll = 0
        self.compare = False

    def toggle(self) -> None:
        self.open = not self.open

    def update(self, dt: float) -> None:
        for reveal in self.flips.values():
            reveal.update(dt, reveal.key)

    def on_click(self, pos: tuple[int, int], run, window: tuple[int, int]) -> bool:
        if not self.open:
            return False
        rects = _layout(window, self.scroll)
        if rects["close"].collidepoint(pos):
            self.open = False
            return True
        if rects["compare"].collidepoint(pos):
            self.compare = not self.compare
            return True
        if rects["up"].collidepoint(pos):
            self.scroll = max(0, self.scroll - 1)
            return True
        if rects["down"].collidepoint(pos):
            self.scroll = min(self.scroll + 1, max(0, len([relic for relic in RELICS if relic.in_shop]) - 8))
            return True
        for relic_id, rect, add, remove in rects["rows"]:
            if rect.collidepoint(pos):
                reveal = self.flips.setdefault(relic_id, ShopReveal())
                reveal.key = (relic_id, 0 if reveal.face_up else 1)
                reveal.progress = 0.0
                return True
            if add.collidepoint(pos):
                run.relics.acquire(relic_id)
                return True
            if remove.collidepoint(pos):
                _release(run, relic_id)
                return True
        return True

    def draw(self, screen: pygame.Surface, assets, run) -> None:
        if not self.open:
            return
        shade = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        shade.fill((16, 10, 8, 150))
        screen.blit(shade, (0, 0))
        rects = _layout(screen.get_size(), self.scroll)
        pygame.draw.rect(screen, (48, 30, 20), rects["panel"], border_radius=16)
        inner = rects["panel"].inflate(-8, -8)
        pygame.draw.rect(screen, (232, 214, 184), inner, border_radius=12)
        _blit_text(screen, "Relic Gallery", get_font(28, bold=True), (62, 40, 28), midleft=(inner.x + 16, inner.y + 24))
        draw_button(screen, rects["close"], "Close", font_size=16)
        draw_button(screen, rects["compare"], "Cards" if self.compare else "Source", font_size=16)
        draw_button(screen, rects["up"], "Up", font_size=16)
        draw_button(screen, rects["down"], "Down", font_size=16)
        for relic_id, rect, add, remove in rects["rows"]:
            definition = relic_by_id(relic_id)
            if self.compare:
                _draw_source(screen, assets, definition, rect)
            else:
                reveal = self.flips.setdefault(relic_id, ShopReveal())
                if reveal.key is None:
                    reveal.key = (relic_id, 1)
                    reveal.progress = 1.0
                plate = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                if reveal.face_up and definition is not None:
                    self.cards.draw(plate, assets, definition, plate.get_rect())
                else:
                    self.cards.draw(plate, assets, definition, plate.get_rect(), face_down=True)
                width = max(1, int(plate.get_width() * reveal.scale_x))
                if width != plate.get_width():
                    plate = pygame.transform.smoothscale(plate, (width, plate.get_height()))
                screen.blit(plate, plate.get_rect(center=rect.center))
            owned = run.relics.owns(relic_id)
            draw_button(screen, add, "Add", enabled=not owned, font_size=14)
            draw_button(screen, remove, "Remove", enabled=owned, font_size=14)


def _release(run, relic_id: str) -> None:
    owned = run.relics.find(relic_id)
    if owned is None:
        return
    run.relics.owned.remove(owned)
    run.relics._effects.pop(owned.instance_id, None)


def _draw_source(screen: pygame.Surface, assets, relic, rect: pygame.Rect) -> None:
    pygame.draw.rect(screen, (214, 196, 168), rect, border_radius=8)
    key = None if relic is None else front_key(relic)
    if key and assets.has(key):
        image = assets.fitted(key, rect.w - 8, rect.h - 8)
        screen.blit(image, image.get_rect(center=rect.center))
    _blit_text(screen, "source", get_font(14, bold=True), (62, 40, 28), midbottom=(rect.centerx, rect.bottom - 6))


def _layout(window: tuple[int, int], scroll: int) -> dict:
    panel = pygame.Rect(0, 0, min(1180, window[0] - 32), min(820, window[1] - 32))
    panel.center = (window[0] // 2, window[1] // 2)
    close = pygame.Rect(panel.right - 110, panel.y + 16, 86, 32)
    compare = pygame.Rect(close.x - 108, close.y, 100, 32)
    up = pygame.Rect(panel.x + 16, panel.bottom - 48, 80, 32)
    down = pygame.Rect(up.right + 8, up.y, 80, 32)
    ids = [relic.id for relic in RELICS if relic.in_shop]
    start = max(0, min(scroll, max(0, len(ids) - 8)))
    columns = 4
    gap_x = 18
    gap_y = 40
    usable_w = panel.w - 48 - gap_x * (columns - 1)
    usable_h = panel.h - 120 - gap_y
    cell_w = usable_w // columns
    cell_h = usable_h // 2
    card_h = max(120, min(int(cell_w / CARD_RATIO), cell_h - 32))
    card_w = max(80, int(round(card_h * CARD_RATIO)))
    rows = []
    x = panel.x + 24
    y = panel.y + 60
    shown = 0
    for relic_id in ids[start : start + 8]:
        rect = pygame.Rect(x, y, card_w, card_h)
        add = pygame.Rect(rect.x, rect.bottom + 4, 56, 26)
        remove = pygame.Rect(add.right + 6, add.y, 70, 26)
        rows.append((relic_id, rect, add, remove))
        shown += 1
        if shown % columns == 0:
            x = panel.x + 24
            y += card_h + gap_y
        else:
            x += card_w + gap_x
    return {"panel": panel, "close": close, "compare": compare, "up": up, "down": down, "rows": rows}
