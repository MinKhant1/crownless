import pygame

from game.relics.relic_data import RelicDef
from rendering.hud_renderer import _blit_text, get_font
from rendering.relic_card import wrap_text


PARCHMENT = (236, 220, 196)


def tooltip_lines(relic: RelicDef) -> list[tuple[str, bool]]:
    return [
        (f"Name: {relic.name}", True),
        ("Saying:", True),
        (f"\"{relic.flavor_text}\"", False),
        ("Effect:", True),
        (relic.description, False),
    ]


def draw_relic_tooltip(
    screen: pygame.Surface,
    relic: RelicDef,
    anchor: pygame.Rect,
    band: pygame.Rect | None = None,
) -> pygame.Rect:
    window = screen.get_size()
    width = _tooltip_width(window, band or anchor)
    body = get_font(15, bold=False)
    title = get_font(16, bold=True)
    wrapped: list[tuple[str, bool]] = []
    for text, strong in tooltip_lines(relic):
        font = title if strong else body
        for line in wrap_text(font, text, width - 20) or [""]:
            wrapped.append((line, strong))
    height = 16 + sum((title.get_height() if strong else body.get_height()) + 2 for _line, strong in wrapped)
    panel = _place(anchor, width, height, window, band or anchor)
    shadow = pygame.Surface((panel.w, panel.h), pygame.SRCALPHA)
    shadow.fill((16, 10, 6, 90))
    screen.blit(shadow, (panel.x + 3, panel.y + 4))
    pygame.draw.rect(screen, (48, 32, 22), panel, border_radius=8)
    pygame.draw.rect(screen, (214, 170, 90), panel, width=2, border_radius=8)
    y = panel.y + 10
    for line, strong in wrapped:
        font = title if strong else body
        color = PARCHMENT if strong else (226, 210, 188)
        _blit_text(screen, line, font, color, midleft=(panel.x + 10, y + font.get_height() // 2))
        y += font.get_height() + 2
    return panel


def _tooltip_width(window: tuple[int, int], band: pygame.Rect) -> int:
    side = max(band.left - 16, window[0] - band.right - 16)
    return min(280, max(150, side))


def _place(
    anchor: pygame.Rect,
    width: int,
    height: int,
    window: tuple[int, int],
    band: pygame.Rect,
) -> pygame.Rect:
    gap = 10
    y = band.centery - height // 2
    left_x = band.left - gap - width
    right_x = band.right + gap
    if anchor.centerx <= band.centerx:
        order = (left_x, right_x)
    else:
        order = (right_x, left_x)
    bounds = pygame.Rect(8, 8, max(1, window[0] - 16), max(1, window[1] - 16))
    for x in order:
        panel = pygame.Rect(x, y, width, height)
        if panel.left >= bounds.left and panel.right <= bounds.right and not panel.colliderect(band):
            panel.clamp_ip(bounds)
            return panel
    below = pygame.Rect(anchor.left, band.bottom + gap, width, height)
    below.clamp_ip(bounds)
    return below
