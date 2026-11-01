import pygame

from config.settings import LIGHT_TEXT
from rendering.enemy_tags import (
    HEADING,
    IVORY,
    battle_font,
    draw_personalities,
    heading_block,
    heading_font,
    hud_scale,
    left_sections,
)
from rendering.hud_renderer import _blit_text, get_font
from rendering.shop_preview import draw_panel_preview

GOLD_VALUE = (236, 206, 130)
_GOLD_TRIMMED: pygame.Surface | None = None
_GOLD_RAW_ID: int | None = None
_GOLD_SCALED: dict[int, pygame.Surface] = {}


def draw_left_sidebar(screen: pygame.Surface, run, layout, assets=None, game=None) -> None:
    rect = layout.left
    battle, personality, resources, army = left_sections(layout, run)
    _draw_wood(screen, rect)
    for section in (battle, personality, resources, army):
        _divider(screen, rect, section.bottom)
    _blit_text(screen, f"BATTLE {run.level}", battle_font(rect.w), IVORY, center=battle.center)
    _draw_heading(screen, "ENEMY PERSONALITY", personality)
    _draw_heading(screen, "RESOURCES", resources)
    _draw_gold(screen, assets, run, resources)
    _draw_heading(screen, "ARMY STATUS", army)
    _draw_army(screen, run, army)
    if run.phase == "shop":
        _draw_coming_board(screen, assets, run, layout, army)
    if run.notice:
        _blit_text(screen, run.notice, get_font(16, bold=False), (214, 120, 96), center=(rect.centerx, layout.menu.y - 18))
    _menu_button(screen, layout.menu, "Main Menu")
    _menu_button(screen, layout.options, "Options")
    draw_personalities(screen, assets, run, layout, game)


def _draw_wood(screen: pygame.Surface, rect: pygame.Rect) -> None:
    shadow = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (12, 6, 3, 88), shadow.get_rect(), border_radius=16)
    screen.blit(shadow, (rect.x + 3, rect.y + 5))
    plate = pygame.Surface((max(1, rect.w), max(1, rect.h)), pygame.SRCALPHA)
    body = plate.get_rect()
    pygame.draw.rect(plate, (46, 27, 16, 236), body, border_radius=16)
    pygame.draw.rect(plate, (214, 170, 90), body, width=2, border_radius=16)
    inner = body.inflate(-8, -8)
    pygame.draw.rect(plate, (156, 116, 62), inner, width=1, border_radius=12)
    screen.blit(plate, rect.topleft)


def _divider(screen: pygame.Surface, panel: pygame.Rect, y: int) -> None:
    pygame.draw.line(screen, (132, 96, 54), (panel.x + 18, y), (panel.right - 18, y), 2)


def _draw_heading(screen: pygame.Surface, text: str, section: pygame.Rect) -> None:
    font = heading_font(section.w)
    _blit_text(screen, text, font, HEADING, center=(section.centerx, section.y + 14 + font.get_height() // 2))


def _content_area(section: pygame.Rect) -> pygame.Rect:
    block = heading_block(section.w)
    return pygame.Rect(section.x, section.y + block, section.w, max(1, section.h - block))


def _draw_gold(screen: pygame.Surface, assets, run, section: pygame.Rect) -> None:
    area = _content_area(section)
    scale = hud_scale(section.w)
    font = get_font(max(18, int(round(26 * scale))), bold=True)
    label = str(run.gold)
    text_w = font.size(label)[0]
    icon_h = max(26, int(round(34 * scale)))
    icon = _gold_icon(assets, icon_h)
    gap = 10
    icon_w = icon.get_width() if icon is not None else icon_h
    group_w = icon_w + gap + text_w
    x = area.centerx - group_w // 2
    if icon is not None:
        screen.blit(icon, icon.get_rect(midleft=(x, area.centery)))
    else:
        coin = (x + icon_h // 2, area.centery)
        pygame.draw.circle(screen, (120, 84, 32), coin, icon_h // 2)
        pygame.draw.circle(screen, (232, 190, 78), coin, max(4, icon_h // 2 - 3))
    _blit_text(screen, label, font, GOLD_VALUE, midleft=(x + icon_w + gap, area.centery))


def _draw_army(screen: pygame.Surface, run, section: pygame.Rect) -> None:
    area = _content_area(section)
    count = run.deployment.non_king_count(run.army)
    label = f"Army {count} / {run.army.capacity}"
    font = get_font(max(16, int(round(21 * hud_scale(section.w)))), bold=True)
    _blit_text(screen, label, font, IVORY, center=area.center)


def _draw_coming_board(screen: pygame.Surface, assets, run, layout, army: pygame.Rect) -> None:
    top = army.bottom + 12
    bottom = layout.menu.y - (28 if run.notice else 10)
    if bottom - top < 36:
        return
    bounds = pygame.Rect(layout.left.x + 16, top, max(1, layout.left.w - 32), bottom - top)
    draw_panel_preview(screen, assets, run, bounds)


def _menu_button(screen: pygame.Surface, rect: pygame.Rect, label: str) -> None:
    pointer = pygame.mouse.get_pos() if pygame.display.get_surface() is not None else (-1, -1)
    hovered = rect.collidepoint(pointer)
    fill = (98, 60, 36) if hovered else (72, 42, 28)
    border = (232, 196, 120) if hovered else (214, 170, 90)
    pygame.draw.rect(screen, fill, rect, border_radius=10)
    pygame.draw.rect(screen, border, rect, width=2, border_radius=10)
    _blit_text(screen, label, get_font(18, bold=True), LIGHT_TEXT, center=rect.center)


def _gold_icon(assets, height: int) -> pygame.Surface | None:
    global _GOLD_TRIMMED, _GOLD_RAW_ID
    if assets is None or not assets.has("gold"):
        return None
    raw = assets.get("gold")
    if _GOLD_RAW_ID != id(raw):
        _GOLD_TRIMMED = _crop_alpha(raw)
        _GOLD_RAW_ID = id(raw)
        _GOLD_SCALED.clear()
    height = max(1, int(height))
    icon = _GOLD_SCALED.get(height)
    if icon is None and _GOLD_TRIMMED is not None:
        width = max(1, int(round(_GOLD_TRIMMED.get_width() * height / _GOLD_TRIMMED.get_height())))
        icon = pygame.transform.smoothscale(_GOLD_TRIMMED, (width, height))
        _GOLD_SCALED[height] = icon
    return icon


def _crop_alpha(surface: pygame.Surface, threshold: int = 20) -> pygame.Surface:
    width, height = surface.get_size()
    min_x, min_y, max_x, max_y = width, height, 0, 0
    found = False
    step = 4
    for y in range(0, height, step):
        for x in range(0, width, step):
            if surface.get_at((x, y)).a > threshold:
                found = True
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
    if not found:
        return surface
    min_x = max(0, min_x - step)
    min_y = max(0, min_y - step)
    max_x = min(width - 1, max_x + step)
    max_y = min(height - 1, max_y + step)
    rect = pygame.Rect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
    return surface.subsurface(rect).copy()
