import pygame

from game.relics.relic_data import RelicDef
from rendering.asset_manager import AssetManager
from rendering.hud_renderer import _blit_text, get_font


PARCHMENT = (236, 220, 196)
PARCHMENT_EDGE = (92, 64, 42)
INK = (48, 32, 24)
FLAVOR = (96, 58, 42)
RULE = (120, 84, 58)

_SMALL_FONTS: dict[tuple[int, bool], pygame.font.Font] = {}


def wrap_text(font: pygame.font.Font, text: str, width: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if font.size(trial)[0] <= width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _card_font(size: int, bold: bool) -> pygame.font.Font:
    size = max(8, int(size))
    if size >= 10:
        return get_font(size, bold=bold)
    key = (size, bold)
    font = _SMALL_FONTS.get(key)
    if font is None:
        font = pygame.font.SysFont("georgia", size, bold=bold)
        _SMALL_FONTS[key] = font
    return font


def _fit_lines(text: str, width: int, height: int, size: int, bold: bool) -> tuple[pygame.font.Font, list[str]]:
    styles = (bold, False) if bold else (False,)
    for style in styles:
        for current in range(max(8, size), 7, -1):
            font = _card_font(current, style)
            lines = wrap_text(font, text, width)
            widest = max((font.size(line)[0] for line in lines), default=0)
            if widest <= width and font.get_height() * max(1, len(lines)) <= height:
                return font, lines
    font = _card_font(8, False)
    lines = wrap_text(font, text, width)
    fitted: list[str] = []
    for line in lines:
        trimmed = line
        while trimmed and font.size(trimmed + "...")[0] > width:
            trimmed = trimmed[:-1]
        fitted.append(trimmed + "..." if trimmed != line else line)
    max_lines = max(1, height // max(1, font.get_height()))
    return font, fitted[:max_lines]


class RelicCardRenderer:
    def __init__(self) -> None:
        self._mini: dict[tuple, pygame.Surface] = {}

    def clear(self) -> None:
        self._mini.clear()

    def mini_surface(
        self,
        assets: AssetManager,
        relic: RelicDef,
        width: int,
        height: int,
        state: str,
    ) -> pygame.Surface:
        width = max(1, int(width))
        height = max(1, int(height))
        key = (relic.id, width, height, state)
        cached = self._mini.get(key)
        if cached is not None:
            return cached
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.draw(surface, assets, relic, surface.get_rect())
        if state == "disabled":
            _mute(surface)
        elif state == "used":
            _darken(surface)
            _draw_check(surface)
        self._mini[key] = surface
        return surface

    def draw(
        self,
        screen: pygame.Surface,
        assets: AssetManager,
        relic: RelicDef,
        rect: pygame.Rect,
        hovered: bool = False,
        owned: bool = False,
    ) -> None:
        if assets.has("relic_card"):
            screen.blit(assets.scaled("relic_card", (rect.w, rect.h)), rect.topleft)
        else:
            pygame.draw.rect(screen, PARCHMENT, rect, border_radius=max(8, rect.w // 18))
        border = (214, 170, 90) if hovered or owned else PARCHMENT_EDGE
        width = 3 if hovered else 2
        pygame.draw.rect(screen, border, rect, width=width, border_radius=max(8, rect.w // 18))
        if rect.h >= 200:
            pygame.draw.rect(screen, (28, 18, 12), rect.inflate(6, 6), width=2, border_radius=16)
        if rect.h < 200:
            self._draw_compact(screen, assets, relic, rect)
            return
        pad = max(8, rect.w // 14)
        inner = rect.inflate(-pad * 2, -pad * 2)
        name_h = max(22, int(rect.h * 0.12))
        body_h = max(28, int(rect.h * 0.22))
        flavor_h = max(18, int(rect.h * 0.12))
        name_rect = pygame.Rect(inner.x, inner.y, inner.w, name_h)
        art_rect = pygame.Rect(inner.x, name_rect.bottom + 4, inner.w, max(12, inner.h - name_h - flavor_h - body_h - 16))
        flavor_rect = pygame.Rect(inner.x, art_rect.bottom + 4, inner.w, flavor_h)
        body_rect = pygame.Rect(inner.x, flavor_rect.bottom + 2, inner.w, body_h)
        self._draw_art(screen, assets, relic, art_rect)
        name_font, name_lines = _fit_lines(relic.name.upper(), name_rect.w, name_rect.h, max(13, rect.h // 16), True)
        self._draw_lines(screen, name_lines, name_font, INK, name_rect)
        quote = f"\"{relic.flavor_text}\""
        flavor_font, flavor_lines = _fit_lines(quote, flavor_rect.w, flavor_rect.h, max(11, rect.h // 24), False)
        self._draw_lines(screen, flavor_lines, flavor_font, FLAVOR, flavor_rect)
        body_font, body_lines = _fit_lines(relic.description, body_rect.w, body_rect.h, max(11, rect.h // 26), False)
        self._draw_lines(screen, body_lines, body_font, INK, body_rect)
        if owned:
            tag = pygame.Rect(rect.right - 74, rect.y + 8, 66, 20)
            pygame.draw.rect(screen, (120, 84, 36), tag, border_radius=6)
            _blit_text(screen, "Owned", get_font(12, bold=True), PARCHMENT, center=tag.center)

    def _draw_compact(self, screen: pygame.Surface, assets: AssetManager, relic: RelicDef, rect: pygame.Rect) -> None:
        pad = max(4, rect.w // 18)
        name_h = max(22, min(40, rect.h // 3))
        name_rect = pygame.Rect(rect.x + pad, rect.y + 4, rect.w - pad * 2, name_h)
        art_rect = pygame.Rect(rect.x + pad, name_rect.bottom + 2, rect.w - pad * 2, max(8, rect.bottom - name_rect.bottom - pad))
        font, lines = _fit_lines(relic.name.upper(), name_rect.w, name_rect.h, max(11, rect.w // 11), True)
        self._draw_lines(screen, lines[:2], font, INK, name_rect)
        self._draw_art(screen, assets, relic, art_rect)

    def _draw_art(self, screen: pygame.Surface, assets: AssetManager, relic: RelicDef, rect: pygame.Rect) -> None:
        pygame.draw.rect(screen, (214, 196, 170), rect, border_radius=8)
        pygame.draw.rect(screen, RULE, rect, width=1, border_radius=8)
        key = f"relic_art_{relic.id}"
        if assets.has(key):
            image = assets.fitted(key, max(1, rect.w - 8), max(1, rect.h - 8))
            screen.blit(image, image.get_rect(center=rect.center))
            return
        self._draw_placeholder(screen, relic.id, rect)

    def _draw_placeholder(self, screen: pygame.Surface, relic_id: str, rect: pygame.Rect) -> None:
        center = rect.center
        roll = pygame.Rect(0, 0, max(16, rect.w // 3), max(12, rect.h // 4))
        roll.center = center
        tint = (148, 92, 48)
        if relic_id == "blood_contract":
            splash = roll.inflate(rect.w // 3, rect.h // 5)
            pygame.draw.ellipse(screen, (150, 42, 36), splash)
            tint = (176, 132, 64)
        elif relic_id == "conversion":
            tint = (168, 168, 176)
        elif relic_id == "gold_charm":
            tint = (196, 156, 64)
        pygame.draw.ellipse(screen, tint, roll)
        pygame.draw.ellipse(screen, (92, 58, 32), roll, width=2)
        band = pygame.Rect(roll.x, roll.centery - 3, roll.w, 6)
        pygame.draw.rect(screen, (120, 36, 32), band)

    def _draw_lines(
        self,
        screen: pygame.Surface,
        lines: list[str],
        font: pygame.font.Font,
        color: tuple[int, int, int],
        rect: pygame.Rect,
    ) -> None:
        total = font.get_height() * len(lines)
        y = rect.y + max(0, (rect.h - total) // 2)
        for line in lines:
            _blit_text(screen, line, font, color, center=(rect.centerx, y + font.get_height() // 2))
            y += font.get_height()


def _mute(surface: pygame.Surface) -> None:
    wash = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    wash.fill((158, 148, 132, 255))
    surface.blit(wash, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    dim.fill((28, 22, 16, 40))
    surface.blit(dim, (0, 0))


def _darken(surface: pygame.Surface) -> None:
    shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    shade.fill((24, 14, 8, 78))
    surface.blit(shade, (0, 0))


def _draw_check(surface: pygame.Surface) -> None:
    radius = max(6, surface.get_width() // 9)
    center = (surface.get_width() - radius - 4, radius + 4)
    pygame.draw.circle(surface, (214, 186, 110), center, radius + 1)
    pygame.draw.circle(surface, (46, 92, 52), center, radius)
    left = (center[0] - radius // 2, center[1])
    mid = (center[0] - radius // 6, center[1] + radius // 3)
    right = (center[0] + radius // 2, center[1] - radius // 3)
    pygame.draw.line(surface, (236, 224, 186), left, mid, 2)
    pygame.draw.line(surface, (236, 224, 186), mid, right, 2)
