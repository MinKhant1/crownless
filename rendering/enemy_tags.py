from dataclasses import dataclass

import pygame

from ai.trait_assignment import current_enemy_trait
from ai.trait_definitions import trait_description, trait_title
from rendering.hud_renderer import _blit_text, get_font


_FACED: dict[tuple, int] = {}


@dataclass(frozen=True)
class TagRow:
    trait: str
    rect: pygame.Rect


@dataclass(frozen=True)
class PersonalityLayout:
    title: pygame.Rect
    rows: tuple[TagRow, ...]


def faced_enemy(run, game=None):
    board = _resolve_game(run, game)
    key = (id(run), getattr(run, "level", 0))
    current = _targeted_enemy(board)
    if current is not None:
        _FACED[key] = current.id
        return current
    remembered = _living_enemy(board, _FACED.get(key))
    if remembered is None:
        _FACED.pop(key, None)
    return remembered


SECTION_HEIGHTS = (90, 160, 105, 105)
IVORY = (245, 232, 210)
HEADING = (226, 204, 168)


def hud_scale(panel_w: int) -> float:
    return max(0.78, min(1.0, panel_w / 300))


def _fitted_font(text: str, size: int, max_width: int, bold: bool = True) -> pygame.font.Font:
    size = max(11, int(size))
    font = get_font(size, bold=bold)
    while size > 11 and font.size(text)[0] > max_width:
        size -= 1
        font = get_font(size, bold=bold)
    return font


def battle_font(panel_w: int) -> pygame.font.Font:
    return _fitted_font("BATTLE 12", int(round(30 * hud_scale(panel_w))), max(1, panel_w - 28))


def heading_font(panel_w: int) -> pygame.font.Font:
    return _fitted_font("ENEMY PERSONALITY", int(round(18 * hud_scale(panel_w))), max(1, panel_w - 40))


def heading_block(panel_w: int) -> int:
    return 14 + heading_font(panel_w).get_height() + 8


def _content_bottom(layout, run) -> int:
    limit = layout.menu.y - 8
    battle = getattr(run, "battle", None)
    active = getattr(run, "phase", "") == "battle" and battle is not None and getattr(battle, "outcome", None) is None
    if active:
        debug_top = layout.menu.y - 8 - (34 + 8) * 2
        limit = min(limit, debug_top - 6)
    return limit


def left_sections(layout, run) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect, pygame.Rect]:
    panel = layout.left
    available = max(len(SECTION_HEIGHTS), _content_bottom(layout, run) - panel.y)
    heights = list(SECTION_HEIGHTS)
    if sum(heights) > available:
        scale = available / sum(SECTION_HEIGHTS)
        heights = [max(1, int(height * scale)) for height in SECTION_HEIGHTS]
        heights[-1] += available - sum(heights)
    y = panel.y
    rects: list[pygame.Rect] = []
    for height in heights:
        rects.append(pygame.Rect(panel.x, y, panel.w, max(1, height)))
        y += height
    return rects[0], rects[1], rects[2], rects[3]


def personality_layout(layout, run, aspects: dict[str, tuple[int, int]], game=None) -> PersonalityLayout:
    panel = layout.left
    battle, personality, _resources, _army = left_sections(layout, run)
    label = f"BATTLE {run.level}"
    title_w, title_h = battle_font(panel.w).size(label)
    title = pygame.Rect(0, 0, title_w, title_h)
    title.center = battle.center
    del game
    trait = current_enemy_trait(run)
    if trait is None:
        return PersonalityLayout(title, ())
    image_w, image_h = aspects.get(trait, (4, 1))
    top = personality.y + heading_block(panel.w)
    area_h = max(1, personality.bottom - top - 8)
    area_w = max(1, min(260, panel.w - 36))
    draw_w, draw_h = _fit_size(image_w, image_h, area_w, area_h)
    rect = pygame.Rect(0, 0, draw_w, draw_h)
    rect.center = (panel.centerx, top + area_h // 2)
    rect.centerx = panel.centerx
    return PersonalityLayout(title, (TagRow(trait, rect),))


def draw_personalities(screen: pygame.Surface, assets, run, layout, game=None) -> PersonalityLayout:
    trait = current_enemy_trait(run)
    aspects = {}
    if trait is not None:
        key = f"tag_{trait}"
        if assets is not None and assets.has(key):
            aspects[trait] = assets.get(key).get_size()
        else:
            aspects[trait] = (4, 1)
    placed = personality_layout(layout, run, aspects, game)
    pointer = pygame.mouse.get_pos() if pygame.display.get_surface() is not None else (-1, -1)
    hovered = None
    if not placed.rows:
        _battle, personality, _resources, _army = left_sections(layout, run)
        block = heading_block(layout.left.w)
        area = pygame.Rect(personality.x, personality.y + block, personality.w, max(1, personality.h - block))
        _blit_text(screen, "—", heading_font(layout.left.w), (176, 146, 104), center=area.center)
    for row in placed.rows:
        image = _tag_image(assets, row.trait, row.rect.size)
        if image is not None:
            screen.blit(image, image.get_rect(center=row.rect.center))
        else:
            pygame.draw.rect(screen, (92, 58, 32), row.rect, border_radius=6)
            _blit_text(screen, trait_title(row.trait), get_font(14, bold=True), IVORY, center=row.rect.center)
        if row.rect.collidepoint(pointer):
            hovered = row
    if hovered is not None:
        _draw_tag_tooltip(screen, hovered, layout)
    return placed


def sidebar_anchors(run, layout) -> tuple[int, int]:
    _battle, personality, resources, _army = left_sections(layout, run)
    return personality.bottom, resources.centery


def _resolve_game(run, game):
    if game is not None:
        return game
    battle = getattr(run, "battle", None)
    if battle is not None:
        return battle.game
    return None


def _targeted_enemy(game):
    if game is None:
        return None
    hover = game.hover
    if hover is not None:
        piece = game.board.piece_at(*hover)
        if _is_enemy(piece):
            return piece
    selected = game.selected_piece()
    if _is_enemy(selected):
        return selected
    return None


def _living_enemy(game, piece_id: int | None):
    if game is None or piece_id is None:
        return None
    piece = game.board.piece_by_id(piece_id)
    if not _is_enemy(piece):
        return None
    return piece


def _is_enemy(piece) -> bool:
    return piece is not None and piece.color == "black" and piece.col is not None and bool(piece.ai_trait)


def _fit_size(image_w: int, image_h: int, max_w: int, max_h: int) -> tuple[int, int]:
    scale = min(max_w / max(1, image_w), max_h / max(1, image_h))
    return max(1, int(round(image_w * scale))), max(1, int(round(image_h * scale)))


def _tag_image(assets, trait: str, size: tuple[int, int]):
    if assets is None or not assets.has(f"tag_{trait}"):
        return None
    return assets.fitted(f"tag_{trait}", size[0], size[1])


def _draw_tag_tooltip(screen: pygame.Surface, row: TagRow, layout) -> None:
    title_font = get_font(16, bold=True)
    body_font = get_font(15, bold=False)
    title = trait_title(row.trait)
    body = trait_description(row.trait)
    width = min(240, max(140, layout.left.w - 24))
    lines = _wrap(body_font, body, width - 20)
    height = 16 + title_font.get_height() + 8 + len(lines) * (body_font.get_height() + 2)
    panel = _place_tooltip(row.rect, width, height, screen.get_size(), layout.left, layout.board)
    pygame.draw.rect(screen, (236, 220, 186), panel, border_radius=8)
    pygame.draw.rect(screen, (92, 58, 32), panel, width=2, border_radius=8)
    _blit_text(screen, title, title_font, (62, 36, 22), midleft=(panel.x + 10, panel.y + 8 + title_font.get_height() // 2))
    y = panel.y + 16 + title_font.get_height()
    for line in lines:
        _blit_text(screen, line, body_font, (92, 58, 32), midleft=(panel.x + 10, y + body_font.get_height() // 2))
        y += body_font.get_height() + 2


def _place_tooltip(anchor: pygame.Rect, width: int, height: int, window: tuple[int, int], panel: pygame.Rect, board: pygame.Rect) -> pygame.Rect:
    bounds = pygame.Rect(8, 8, max(1, window[0] - 16), max(1, window[1] - 16))
    candidates = (
        pygame.Rect(anchor.x, anchor.y - height - 8, width, height),
        pygame.Rect(anchor.x, anchor.bottom + 8, width, height),
        pygame.Rect(panel.x + 8, anchor.y, width, height),
    )
    for rect in candidates:
        rect.clamp_ip(bounds)
        if rect.colliderect(board):
            continue
        return rect
    fallback = pygame.Rect(panel.x + 8, panel.y + 8, width, height)
    fallback.clamp_ip(bounds)
    return fallback


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
    return lines or [""]
