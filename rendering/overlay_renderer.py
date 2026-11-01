import math

import pygame

from game.piece import Piece
from game.traits import trait_by_id
from rendering.trait_style import trait_style


TRAIT_COLORS = {
    "golden": (232, 176, 42),
    "wanted": (214, 42, 48),
    "explosive": (226, 78, 28),
    "ghost": (92, 196, 220),
    "wooden": (122, 74, 32),
}


def trait_tooltip_lines(piece: Piece) -> tuple[str, str] | None:
    trait = trait_by_id(piece.trait)
    if trait is None:
        return None
    return f"{trait.name} {piece.kind.capitalize()}", trait.description


def draw_crosshair(screen: pygame.Surface, square: pygame.Rect) -> None:
    center_x, center_y = square.center
    limit = max(8, min(square.w, square.h) // 2 - 2)
    radius = max(8, min(int(min(square.w, square.h) * (0.42 if trait_style.strong else 0.34)), limit - 6))
    tick = max(5, min(square.w // 7, limit - radius)) if trait_style.strong else max(3, min(square.w // 11, limit - radius))
    color = (214, 36, 42) if trait_style.strong else (150, 32, 36)
    width = max(3, square.w // 14) if trait_style.strong else max(1, square.w // 28)
    pygame.draw.circle(screen, (92, 12, 16), (center_x, center_y), radius, width + 2)
    pygame.draw.circle(screen, color, (center_x, center_y), radius, width)
    gap = max(2, square.w // 18)
    for step_x, step_y in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        inner = radius + gap
        outer = min(limit, inner + tick)
        start = (center_x + step_x * inner, center_y + step_y * inner)
        end = (center_x + step_x * outer, center_y + step_y * outer)
        pygame.draw.line(screen, (92, 12, 16), start, end, width + 1)
        pygame.draw.line(screen, color, start, end, width)


def draw_explosive_marks(screen: pygame.Surface, square: pygame.Rect) -> None:
    center_x = square.centerx
    base = square.centery + square.h // 6
    span = max(8, square.w // 5) if trait_style.strong else max(6, square.w // 7)
    color = (255, 138, 42) if trait_style.strong else (214, 96, 40)
    width = max(2, square.w // 16) if trait_style.strong else max(1, square.w // 28)
    cracks = (
        ((center_x - span, base + 6), (center_x - span // 5, base - span // 2)),
        ((center_x + span, base + 5), (center_x + span // 5, base - span // 2)),
        ((center_x - 2, base + 8), (center_x + span // 2, base - 2)),
        ((center_x - span // 2, base + 2), (center_x + 2, base - span // 3)),
    )
    for start, end in cracks:
        pygame.draw.line(screen, (72, 24, 12), start, end, width + 1)
        pygame.draw.line(screen, color, start, end, width)


def draw_trait_ring(screen: pygame.Surface, center: tuple[float, float], square: int, trait: str) -> None:
    if trait not in TRAIT_COLORS:
        return
    surface = _RINGS.surface(trait, square, trait_style.strong)
    screen.blit(surface, surface.get_rect(center=(int(center[0]), int(center[1]))))


def draw_trait_badge(screen: pygame.Surface, rect: pygame.Rect, trait: str) -> None:
    if trait not in TRAIT_COLORS:
        return
    strong = trait_style.strong
    size = max(16, rect.w // 4) if strong else max(12, rect.w // 5)
    box = pygame.Rect(0, 0, size, size)
    box.topright = (rect.right - max(1, rect.w // 28), rect.top + max(1, rect.w // 28))
    color = TRAIT_COLORS[trait]
    center = box.center
    radius = box.w // 2
    pygame.draw.circle(screen, (24, 14, 10), center, radius)
    pygame.draw.circle(screen, color, center, max(2, radius - 2))
    ink = (255, 246, 226)
    if trait == "golden":
        _star(screen, center, max(3, radius - 4), ink)
    elif trait == "wanted":
        pygame.draw.circle(screen, ink, center, max(2, radius // 2), max(1, radius // 8))
        reach = max(3, radius - 3)
        pygame.draw.line(screen, ink, (center[0] - reach, center[1]), (center[0] + reach, center[1]), max(1, radius // 7))
        pygame.draw.line(screen, ink, (center[0], center[1] - reach), (center[0], center[1] + reach), max(1, radius // 7))
    elif trait == "explosive":
        bomb = max(3, radius // 2)
        pygame.draw.circle(screen, (48, 22, 14), center, bomb)
        pygame.draw.line(screen, ink, (center[0] + 1, center[1] - 2), (center[0] + bomb + 2, center[1] - bomb - 1), max(1, radius // 8))
    elif trait == "ghost":
        pygame.draw.circle(screen, (232, 252, 255), center, max(2, radius // 2))
    else:
        log = pygame.Rect(0, 0, max(6, box.w - 8), max(4, box.h // 3))
        log.center = center
        pygame.draw.ellipse(screen, (78, 46, 24), log)
        pygame.draw.line(screen, (214, 168, 104), (log.left + 2, log.centery), (log.right - 2, log.centery), 1)


class _RingCache:
    def __init__(self) -> None:
        self._cache: dict[tuple, pygame.Surface] = {}

    def clear(self) -> None:
        self._cache.clear()

    def surface(self, trait: str, square: int, strong: bool) -> pygame.Surface:
        key = (trait, square, strong)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        color = TRAIT_COLORS[trait]
        stroke = max(4, square // 11) if strong else max(2, square // 16)
        radius_x = max(10, int(square * (0.38 if strong else 0.30)))
        radius_y = max(5, int(square * (0.15 if strong else 0.11)))
        pad = stroke + 6
        canvas = pygame.Surface((radius_x * 2 + pad * 2, radius_y * 2 + pad * 2), pygame.SRCALPHA)
        ring = canvas.get_rect().inflate(-pad, -pad)
        glow = (*color, 110 if strong else 48)
        pygame.draw.ellipse(canvas, glow, ring.inflate(stroke, max(2, stroke // 2)), max(2, stroke))
        pygame.draw.ellipse(canvas, (*color, 235 if strong else 170), ring, stroke)
        self._cache[key] = canvas
        return canvas


def _star(screen: pygame.Surface, center: tuple[int, int], radius: int, color: tuple[int, int, int]) -> None:
    points = []
    for index in range(8):
        angle = math.radians(-90 + index * 45)
        distance = radius if index % 2 == 0 else max(2, int(radius * 0.42))
        points.append((center[0] + math.cos(angle) * distance, center[1] + math.sin(angle) * distance))
    pygame.draw.polygon(screen, color, points)


_RINGS = _RingCache()


def draw_lock(screen: pygame.Surface, square: pygame.Rect) -> None:
    size = max(10, square.w // 5)
    x = square.right - size - max(3, square.w // 18)
    y = square.top + max(3, square.w // 18)
    body = pygame.Rect(x, y + size // 3, size, size * 2 // 3)
    pygame.draw.rect(screen, (232, 210, 170), body.inflate(2, 2), border_radius=2)
    pygame.draw.rect(screen, (48, 36, 24), body, border_radius=2)
    shackle = pygame.Rect(x + 2, y, size - 4, size // 2)
    pygame.draw.arc(screen, (232, 210, 170), shackle.inflate(2, 2), 0.15, 3.0, 3)
    pygame.draw.arc(screen, (48, 36, 24), shackle, 0.15, 3.0, 2)


def draw_trait_tooltip(screen: pygame.Surface, game, layout, assets=None) -> None:
    from rendering.hud_renderer import _blit_text, get_font

    hover = game.hover
    if hover is None:
        return
    piece = game.board.piece_at(*hover)
    if piece is None:
        return
    if piece.color == "black" and piece.ai_trait:
        _draw_personality_tooltip(screen, piece, layout, assets)
        return
    lines = trait_tooltip_lines(piece)
    if lines is None:
        return
    title, body = lines
    title_font = get_font(18, bold=True)
    body_font = get_font(15, bold=False)
    width = 250
    wrapped = _wrap(body_font, body, width - 20)
    height = 18 + 24 + len(wrapped) * 20
    square = layout.square_rect(piece.col, piece.row)
    panel = _place(square, width, height, screen.get_size())
    accent = TRAIT_COLORS.get(piece.trait or "", (214, 170, 90))
    pygame.draw.rect(screen, (42, 28, 20), panel, border_radius=8)
    pygame.draw.rect(screen, accent, panel, width=2, border_radius=8)
    pygame.draw.rect(screen, accent, pygame.Rect(panel.x, panel.y + 6, 5, panel.h - 12), border_radius=2)
    title_color = tuple(min(255, channel + 48) for channel in accent)
    _blit_text(screen, title, title_font, title_color, midleft=(panel.x + 14, panel.y + 16))
    y = panel.y + 40
    for line in wrapped:
        _blit_text(screen, line, body_font, (226, 210, 188), midleft=(panel.x + 10, y))
        y += 20


def _draw_personality_tooltip(screen: pygame.Surface, piece, layout, assets) -> None:
    from ai.trait_definitions import trait_description, trait_title
    from rendering.hud_renderer import _blit_text, get_font

    title_font = get_font(18, bold=True)
    body_font = get_font(15, bold=False)
    title = f"Enemy {piece.kind.capitalize()}"
    body = trait_description(piece.ai_trait)
    width = 250
    wrapped = _wrap(body_font, body, width - 20)
    tag_h = 52
    height = 18 + 24 + tag_h + 8 + len(wrapped) * 20
    square = layout.square_rect(piece.col, piece.row)
    panel = _place(square, width, height, screen.get_size())
    pygame.draw.rect(screen, (236, 220, 186), panel, border_radius=8)
    pygame.draw.rect(screen, (92, 58, 32), panel, width=2, border_radius=8)
    _blit_text(screen, title, title_font, (62, 36, 22), midleft=(panel.x + 12, panel.y + 16))
    _blit_text(screen, trait_title(piece.ai_trait), get_font(13, bold=True), (122, 78, 24), midleft=(panel.x + 12, panel.y + 36))
    tag = pygame.Rect(panel.x + 12, panel.y + 48, width - 24, tag_h)
    image = None
    if assets is not None and assets.has(f"tag_{piece.ai_trait}"):
        image = assets.fitted(f"tag_{piece.ai_trait}", tag.w, tag.h)
        screen.blit(image, image.get_rect(midtop=(panel.centerx, tag.y)))
    y = tag.bottom + 8
    for line in wrapped:
        _blit_text(screen, line, body_font, (92, 58, 32), midleft=(panel.x + 12, y))
        y += 20


def _wrap(font: pygame.font.Font, text: str, width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        trial = word if not current else f"{current} {word}"
        if font.size(trial)[0] <= width:
            current = trial
            continue
        if current:
            lines.append(current)
        current = word
    if current:
        lines.append(current)
    return lines


def _place(square: pygame.Rect, width: int, height: int, window: tuple[int, int]) -> pygame.Rect:
    gap = 8
    candidates = (
        (square.right + gap, square.top),
        (square.left - gap - width, square.top),
        (square.left, square.bottom + gap),
        (square.left, square.top - gap - height),
    )
    bounds = pygame.Rect(8, 8, max(1, window[0] - 16), max(1, window[1] - 16))
    for x, y in candidates:
        panel = pygame.Rect(x, y, width, height)
        if panel.left >= bounds.left and panel.top >= bounds.top and panel.right <= bounds.right and panel.bottom <= bounds.bottom:
            if not panel.colliderect(square):
                return panel
    panel = pygame.Rect(square.right + gap, square.top, width, height)
    panel.clamp_ip(bounds)
    return panel
