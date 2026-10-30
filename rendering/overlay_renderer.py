import pygame

from game.piece import Piece
from game.traits import trait_by_id


def trait_tooltip_lines(piece: Piece) -> tuple[str, str] | None:
    trait = trait_by_id(piece.trait)
    if trait is None:
        return None
    return f"{trait.name} {piece.kind.capitalize()}", trait.description


def draw_crosshair(screen: pygame.Surface, square: pygame.Rect) -> None:
    center_x, center_y = square.center
    limit = max(8, min(square.w, square.h) // 2 - 3)
    radius = max(6, min(int(min(square.w, square.h) * 0.34), limit - 4))
    tick = max(3, min(square.w // 11, limit - radius))
    color = (112, 24, 28)
    width = max(1, square.w // 36)
    pygame.draw.circle(screen, color, (center_x, center_y), radius, width)
    gap = max(2, square.w // 22)
    for step_x, step_y in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        inner = radius + gap
        outer = min(limit, inner + tick)
        pygame.draw.line(
            screen,
            color,
            (center_x + step_x * inner, center_y + step_y * inner),
            (center_x + step_x * outer, center_y + step_y * outer),
            width,
        )


def draw_explosive_marks(screen: pygame.Surface, square: pygame.Rect) -> None:
    center_x = square.centerx
    base = square.centery + square.h // 5
    span = max(6, square.w // 7)
    color = (214, 96, 40)
    width = max(1, square.w // 36)
    pygame.draw.line(screen, color, (center_x - span, base + 4), (center_x - span // 3, base - span // 2), width)
    pygame.draw.line(screen, color, (center_x + span, base + 3), (center_x + span // 3, base - span // 2), width)
    pygame.draw.line(screen, color, (center_x - 1, base + 6), (center_x + span // 2, base), width)
    radius = max(4, square.w // 12)
    bomb_x = square.right - radius - 5
    bomb_y = square.top + radius + 5
    pygame.draw.circle(screen, (48, 28, 18), (bomb_x, bomb_y), radius + 1)
    pygame.draw.circle(screen, (206, 84, 32), (bomb_x, bomb_y), radius)
    pygame.draw.circle(screen, (255, 206, 120), (bomb_x - 1, bomb_y - 1), max(1, radius // 3))
    pygame.draw.line(
        screen,
        (92, 58, 28),
        (bomb_x + radius - 1, bomb_y - radius + 1),
        (bomb_x + radius + 4, bomb_y - radius - 4),
        width,
    )


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


def draw_trait_tooltip(screen: pygame.Surface, game, layout) -> None:
    from rendering.hud_renderer import _blit_text, get_font

    hover = game.hover
    if hover is None:
        return
    piece = game.board.piece_at(*hover)
    if piece is None:
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
    pygame.draw.rect(screen, (42, 28, 20), panel, border_radius=8)
    pygame.draw.rect(screen, (214, 170, 90), panel, width=2, border_radius=8)
    _blit_text(screen, title, title_font, (244, 226, 196), midleft=(panel.x + 10, panel.y + 16))
    y = panel.y + 40
    for line in wrapped:
        _blit_text(screen, line, body_font, (226, 210, 188), midleft=(panel.x + 10, y))
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
