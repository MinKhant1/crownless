import pygame

from ai.trait_definitions import AI_TRAITS, trait_description, trait_title
from game.piece import Piece
from game.relics.relic_data import RELICS
from game.traits import TRAITS
from game.transitions.easing import ease_out_cubic
from rendering import style
from rendering.hud_renderer import draw_background, draw_button, draw_relic_glow
from rendering.piece_renderer import draw_trait_sprite
from rendering.relic_card import CARD_RATIO, RelicCardRenderer
from rendering.relic_flip import ShopReveal


TABS = (
    ("relics", "Relics"),
    ("pieces", "Special Pieces"),
    ("enemies", "Enemy Personalities"),
)

# the card's rules text is set at 2.7% of its height, so 410px and up keeps it at 11px or larger
CARD_MIN_HEIGHT = 410
CARD_MAX_HEIGHT = 500
CARD_GAP = 26
SCROLL_STEP = 60


class CollectionScreen:
    """Every relic, special piece and enemy personality. Read-only: nothing here touches a run."""

    TABS = TABS

    def __init__(self) -> None:
        self.tab = "relics"
        self.scroll = 0
        self.tab_age = 1.0
        self.cards = RelicCardRenderer()
        self.flips: dict[str, ShopReveal] = {}
        self._hits: list[tuple[str, pygame.Rect]] = []
        self._pointer = (0, 0)
        self._pressed: str | None = None

    def open(self) -> None:
        self.tab = "relics"
        self.scroll = 0
        self.tab_age = 1.0
        self.flips.clear()
        self._pressed = None

    def update(self, dt: float, window: tuple[int, int]) -> None:
        self.tab_age = min(1.0, self.tab_age + max(0.0, dt) / 0.22)
        for reveal in self.flips.values():
            reveal.update(dt, reveal.key)
        self.scroll = _clamp(self.scroll, self.content_height(window), _frame(window)["content"].h)

    def on_event(self, event: pygame.event.Event, window: tuple[int, int]) -> str | None:
        frame = _frame(window)
        if event.type == pygame.MOUSEMOTION:
            self._pointer = event.pos
            return None
        if event.type == pygame.MOUSEWHEEL:
            if frame["content"].collidepoint(self._pointer):
                self._scroll_by(-event.y * SCROLL_STEP, window)
            return None
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "back"
            steps = {pygame.K_DOWN: SCROLL_STEP, pygame.K_UP: -SCROLL_STEP, pygame.K_PAGEDOWN: frame["content"].h, pygame.K_PAGEUP: -frame["content"].h}
            if event.key in steps:
                self._scroll_by(steps[event.key], window)
            return None
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._pointer = event.pos
            self._pressed = self._hit(event.pos, window)
            return None
        if event.type != pygame.MOUSEBUTTONUP or event.button != 1:
            return None
        pressed, self._pressed = self._pressed, None
        name = self._hit(event.pos, window)
        if name is None or name != pressed:
            return None
        if name == "back":
            return "back"
        if name.startswith("tab:"):
            chosen = name.split(":", 1)[1]
            if chosen != self.tab:
                self.tab = chosen
                self.scroll = 0
                self.tab_age = 0.0
            return None
        if name.startswith("relic:"):
            relic_id = name.split(":", 1)[1]
            reveal = self.flips.setdefault(relic_id, ShopReveal())
            reveal.key = (relic_id, 0 if reveal.face_up else 1)
            reveal.progress = 0.0
        return None

    def wants_hand(self) -> bool:
        return any(rect.collidepoint(self._pointer) for _name, rect in self._hits)

    def content_height(self, window: tuple[int, int]) -> int:
        content = _frame(window)["content"]
        if self.tab == "relics":
            rects = relic_rects(content, 0)
            return 0 if not rects else max(rect.bottom for _id, rect in rects) - content.y + 12
        return content.h

    def draw(self, screen: pygame.Surface, assets) -> None:
        draw_background(screen, assets)
        window = screen.get_size()
        frame = _frame(window)
        panel = frame["panel"]
        style.drop_shadow(screen, panel, offset=12, spread=22, alpha=150)
        screen.blit(style.framed_parchment(assets, panel.size, seed=21), panel.topleft)
        style.text(screen, "Collection", style.title_font(34, bold=True), style.INK, shadow=(255, 246, 222, 150), center=(panel.centerx, panel.y + 42))
        style.ornament_rule(screen, (panel.centerx, panel.y + 70), min(420, panel.w - 120), style.GOLD_DIM)
        self._hits = [("back", frame["back"])]
        self._draw_tabs(screen, frame["tabs"])
        content = frame["content"]
        self.scroll = _clamp(self.scroll, self.content_height(window), content.h)
        previous = screen.get_clip()
        screen.set_clip(content)
        shift = int((1.0 - ease_out_cubic(self.tab_age)) * 16)
        if self.tab == "relics":
            self._draw_relics(screen, assets, content, shift)
        elif self.tab == "pieces":
            self._draw_pieces(screen, assets, content.move(0, shift))
        else:
            self._draw_enemies(screen, assets, content.move(0, shift))
        screen.set_clip(previous)
        if self.tab == "relics":
            _draw_scrollbar(screen, content, self.scroll, self.content_height(window))
        draw_button(screen, frame["back"], "Back", font_size=20)

    def _hit(self, pos: tuple[int, int], window: tuple[int, int]) -> str | None:
        content = _frame(window)["content"]
        for name, rect in self._hits:
            if not rect.collidepoint(pos):
                continue
            if name.startswith("relic:") and not content.collidepoint(pos):
                continue
            return name
        return None

    def _scroll_by(self, amount: int, window: tuple[int, int]) -> None:
        self.scroll = _clamp(self.scroll + amount, self.content_height(window), _frame(window)["content"].h)

    def _draw_tabs(self, screen: pygame.Surface, area: pygame.Rect) -> None:
        for (key, label), rect in zip(TABS, tab_rects(area)):
            draw_button(screen, rect, label, font_size=18, selected=key == self.tab)
            self._hits.append((f"tab:{key}", rect))

    def _draw_relics(self, screen: pygame.Surface, assets, content: pygame.Rect, shift: int) -> None:
        for relic_id, rect in relic_rects(content, self.scroll):
            rect = rect.move(0, shift)
            if rect.bottom < content.top or rect.top > content.bottom:
                continue
            relic = next(item for item in RELICS if item.id == relic_id)
            hovered = rect.collidepoint(self._pointer) and content.collidepoint(self._pointer)
            drawn = rect.move(0, -6) if hovered else rect
            reveal = self.flips.setdefault(relic_id, ShopReveal())
            if reveal.key is None:
                reveal.key = (relic_id, 1)
                reveal.progress = 1.0
            style.drop_shadow(screen, drawn, offset=10 if hovered else 6, spread=12, alpha=130, radius=12)
            plate = pygame.Surface(drawn.size, pygame.SRCALPHA)
            self.cards.draw(plate, assets, relic, plate.get_rect(), face_down=not reveal.face_up)
            width = max(1, int(plate.get_width() * reveal.scale_x))
            if width != plate.get_width():
                plate = pygame.transform.smoothscale(plate, (width, plate.get_height()))
            screen.blit(plate, plate.get_rect(center=drawn.center))
            if hovered:
                draw_relic_glow(screen, drawn)
            self._hits.append((f"relic:{relic_id}", rect))

    def _draw_pieces(self, screen: pygame.Surface, assets, content: pygame.Rect) -> None:
        for trait, rect in zip(TRAITS, tile_rects(content, len(TRAITS))):
            piece = Piece(93000, "pawn", "white", trait=trait.id)
            _draw_tile(screen, assets, rect, trait.name, trait.description, figure=piece)

    def _draw_enemies(self, screen: pygame.Surface, assets, content: pygame.Rect) -> None:
        for trait, rect in zip(AI_TRAITS, tile_rects(content, len(AI_TRAITS))):
            _draw_tile(screen, assets, rect, trait_title(trait).title(), trait_description(trait), tag=trait)


def _frame(window: tuple[int, int]) -> dict[str, pygame.Rect]:
    panel = pygame.Rect(0, 0, min(1180, window[0] - 36), window[1] - 24)
    panel.center = (window[0] // 2, window[1] // 2)
    tabs = pygame.Rect(panel.x + 40, panel.y + 86, panel.w - 80, 44)
    back = pygame.Rect(0, 0, 180, 46)
    back.midbottom = (panel.centerx, panel.bottom - 22)
    content = pygame.Rect(panel.x + 30, tabs.bottom + 14, panel.w - 60, back.y - tabs.bottom - 28)
    return {"panel": panel, "tabs": tabs, "content": content, "back": back}


def tab_rects(area: pygame.Rect) -> list[pygame.Rect]:
    gap = 14
    width = min(300, (area.w - gap * (len(TABS) - 1)) // len(TABS))
    total = width * len(TABS) + gap * (len(TABS) - 1)
    left = area.centerx - total // 2
    return [pygame.Rect(left + index * (width + gap), area.y, width, area.h) for index in range(len(TABS))]


def relic_card_size(content: pygame.Rect) -> tuple[int, int]:
    height = max(CARD_MIN_HEIGHT, min(CARD_MAX_HEIGHT, content.h - 24))
    return int(round(height * CARD_RATIO)), height


def relic_rects(content: pygame.Rect, scroll: int) -> list[tuple[str, pygame.Rect]]:
    """All shop relics in a grid, as wide as the page allows, scrolled by `scroll` pixels."""
    ids = [relic.id for relic in RELICS if relic.in_shop]
    card_w, card_h = relic_card_size(content)
    columns = max(1, (content.w - 24 + CARD_GAP) // (card_w + CARD_GAP))
    row_w = columns * card_w + (columns - 1) * CARD_GAP
    left = content.centerx - row_w // 2
    top = content.y + 14 - scroll
    rects = []
    for index, relic_id in enumerate(ids):
        row, column = divmod(index, columns)
        in_row = min(columns, len(ids) - row * columns)
        row_left = left + (row_w - (in_row * card_w + (in_row - 1) * CARD_GAP)) // 2
        rects.append((relic_id, pygame.Rect(row_left + column * (card_w + CARD_GAP), top + row * (card_h + CARD_GAP), card_w, card_h)))
    return rects


def tile_rects(content: pygame.Rect, count: int) -> list[pygame.Rect]:
    """Three framed tiles per row, the last row centered."""
    columns = 3
    rows = (count + columns - 1) // columns
    gap = 22
    width = (content.w - gap * (columns - 1)) // columns
    height = min(300, (content.h - 16 - gap * (rows - 1)) // rows)
    total_h = rows * height + (rows - 1) * gap
    top = content.y + max(8, (content.h - total_h) // 2)
    rects = []
    for index in range(count):
        row, column = divmod(index, columns)
        in_row = min(columns, count - row * columns)
        row_left = content.centerx - (in_row * width + (in_row - 1) * gap) // 2
        rects.append(pygame.Rect(row_left + column * (width + gap), top + row * (height + gap), width, height))
    return rects


def _draw_tile(screen: pygame.Surface, assets, rect: pygame.Rect, name: str, body: str, figure: Piece | None = None, tag: str | None = None) -> None:
    style.drop_shadow(screen, rect, offset=6, spread=10, alpha=120, radius=10)
    screen.blit(style.framed_parchment(assets, rect.size, seed=rect.w + rect.h, border=11), rect.topleft)
    body_font = style.body_font(17)
    lines = style.wrap(body_font, body, rect.w - 48)
    text_h = len(lines) * (body_font.get_height() + 2)
    # an enemy tag is painted with its own name, so it needs no name plate
    name_h = 40 if tag is None else 0
    art = pygame.Rect(rect.x + 20, rect.y + 20, rect.w - 40, max(40, rect.h - 40 - name_h - 10 - text_h - 12))
    if figure is not None:
        # the same marks the board draws, so the Wanted crosshair and the trait badges show here too
        box = min(art.h, 150)
        spot = pygame.Rect(0, 0, box, box)
        spot.midbottom = (art.centerx, art.bottom)
        draw_trait_sprite(screen, assets, figure, spot, int(box * 0.84))
    elif tag is not None and assets is not None and assets.has(f"tag_{tag}"):
        image = assets.fitted(f"tag_{tag}", min(art.w, 300), min(art.h, 96))
        screen.blit(image, image.get_rect(center=art.center))
    plate = pygame.Rect(0, 0, min(rect.w - 60, max(180, style.title_font(21).size(name)[0] + 60)), name_h)
    plate.midtop = (rect.centerx, art.bottom + 8)
    if tag is None:
        screen.blit(style.plaque(plate.size, "idle"), plate.topleft)
        style.text(screen, name, style.fitted_title(name, 21, plate.w - 24), style.IVORY, shadow=(8, 4, 2, 220), center=plate.center)
    y = plate.bottom + 10
    for line in lines:
        style.text(screen, line, body_font, style.INK, midtop=(rect.centerx, y))
        y += body_font.get_height() + 2


def _draw_scrollbar(screen: pygame.Surface, content: pygame.Rect, scroll: int, total: int) -> None:
    if total <= content.h:
        return
    track = pygame.Rect(content.right + 6, content.y + 4, 6, content.h - 8)
    pygame.draw.rect(screen, (150, 120, 82), track, border_radius=3)
    pygame.draw.rect(screen, (96, 66, 38), track, width=1, border_radius=3)
    thumb_h = max(36, int(track.h * content.h / total))
    travel = track.h - thumb_h
    thumb = pygame.Rect(track.x - 1, track.y + int(travel * scroll / max(1, total - content.h)), track.w + 2, thumb_h)
    pygame.draw.rect(screen, style.WALNUT, thumb, border_radius=3)
    pygame.draw.rect(screen, style.GOLD, thumb, width=1, border_radius=3)


def _clamp(scroll: int, content_h: int, view_h: int) -> int:
    return max(0, min(int(scroll), max(0, content_h - view_h)))
