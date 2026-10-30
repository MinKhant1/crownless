from pathlib import Path

import pygame

from game.relics.relic_data import RelicDef
from rendering.asset_manager import AssetManager
from rendering.relic_art import artwork


INK = (32, 20, 12)
CARD_RATIO = 2 / 3
TITLE_Y = 0.10
ART_TOP = 0.15
ART_BOTTOM = 0.73
FLAVOUR_Y = 0.79
EFFECT_Y = 0.88
TEXT_MARGIN = 0.09
ART_MARGIN_X = 0.09
READABLE_CARD_HEIGHT = 420

_KEYWORDS = (
    "SPECIAL PIECE",
    "NORMAL PIECE",
    "SHOP REROLL",
    "ARMY SIZE",
    "EXPLOSIVE",
    "BISHOP",
    "KNIGHT",
    "QUEEN",
    "ROOK",
    "KING",
    "PAWN",
    "GHOST",
    "GOLD",
)

_FONT_PATHS: dict[bool, str | None] = {}
_FONTS: dict[tuple[int, bool], pygame.font.Font] = {}


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


def _font_path(bold: bool) -> str | None:
    if bold in _FONT_PATHS:
        return _FONT_PATHS[bold]
    found = _bundled_font(bold)
    if found is None:
        for name in ("palatinolinotype", "palatino linotype", "palatino", "garamond", "georgia"):
            found = pygame.font.match_font(name, bold=bold)
            if found:
                break
    if found is None and bold:
        found = _font_path(False)
    _FONT_PATHS[bold] = found
    return found


def _bundled_font(bold: bool) -> str | None:
    folder = Path(__file__).resolve().parents[1] / "assets" / "fonts"
    names = ("card_bold.otf", "card_bold.ttf", "card.otf", "card.ttf") if bold else ("card.otf", "card.ttf")
    for name in names:
        path = folder / name
        if path.exists():
            return str(path)
    return _bundled_font(False) if bold else None


def _serif(size: int, bold: bool = False) -> pygame.font.Font:
    size = max(7, int(size))
    key = (size, bold)
    font = _FONTS.get(key)
    if font is None:
        path = _font_path(bold)
        font = pygame.font.Font(path, size) if path else pygame.font.SysFont("georgia", size, bold=bold)
        _FONTS[key] = font
    return font


class RelicCardRenderer:
    def __init__(self) -> None:
        self._faces: dict[tuple, pygame.Surface] = {}

    def clear(self) -> None:
        self._faces.clear()
        artwork.clear()

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
        cached = self._faces.get(key)
        if cached is not None:
            return cached
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self.draw(surface, assets, relic, surface.get_rect())
        if state == "disabled":
            _mute(surface)
        elif state == "used":
            _darken(surface)
            _draw_check(surface)
        self._faces[key] = surface
        return surface

    def draw(
        self,
        screen: pygame.Surface,
        assets: AssetManager,
        relic: RelicDef | None,
        rect: pygame.Rect,
        hovered: bool = False,
        owned: bool = False,
        face_down: bool = False,
        selected: bool = False,
        progress: float | None = None,
    ) -> None:
        del hovered, owned, selected
        card = _portrait_rect(rect)
        if face_down or relic is None:
            image = self._surface(assets, None, card.w, card.h, True)
        else:
            image = self._surface(assets, relic, card.w, card.h, False)
        if progress is not None:
            amount = max(0.04, min(1.0, abs(float(progress))))
            width = max(1, int(round(image.get_width() * amount)))
            if width != image.get_width():
                image = pygame.transform.smoothscale(image, (width, image.get_height()))
        screen.blit(image, image.get_rect(center=card.center))

    def _surface(
        self,
        assets: AssetManager,
        relic: RelicDef | None,
        width: int,
        height: int,
        face_down: bool,
    ) -> pygame.Surface:
        width = max(1, int(width))
        height = max(1, int(height))
        key = ("back" if face_down or relic is None else relic.id, width, height, face_down or relic is None)
        cached = self._faces.get(key)
        if cached is not None:
            return cached
        if face_down or relic is None:
            image = _compose_back(assets, width, height)
        else:
            image = _compose_face(assets, relic, width, height)
        self._faces[key] = image
        return image


def _compose_back(assets: AssetManager, width: int, height: int) -> pygame.Surface:
    card = pygame.Surface((width, height), pygame.SRCALPHA)
    if assets.has("relic_back"):
        image = assets.fitted("relic_back", width, height)
        card.blit(image, image.get_rect(center=(width // 2, height // 2)))
        return card
    pygame.draw.rect(card, (92, 48, 36), card.get_rect(), border_radius=max(6, width // 18))
    return card


def _compose_face(assets: AssetManager, relic: RelicDef, width: int, height: int) -> pygame.Surface:
    card = pygame.Surface((width, height), pygame.SRCALPHA)
    if assets.has("relic_card"):
        card.blit(assets.scaled("relic_card", (width, height)), (0, 0))
    else:
        pygame.draw.rect(card, (236, 226, 206), card.get_rect(), border_radius=max(6, width // 18))
    text_width = max(1, int(width * (1 - TEXT_MARGIN * 2)))
    title_font, title_lines = _fit_block(relic.name.upper(), text_width, int(height * 0.055), 2, True, single=True)
    flavour = f"\u201c{_protect(relic.flavor_text.upper())}\u201d"
    effect = _protect(relic.description.upper())
    flavour_font, flavour_lines = _fit_block(flavour, text_width, int(height * 0.034), 2, True, single=True)
    effect_font, effect_lines = _fit_block(effect, text_width, int(height * 0.027), 3, False)
    title_rect = _band(width, height, title_font, title_lines, TITLE_Y)
    flavour_rect = _band(width, height, flavour_font, flavour_lines, FLAVOUR_Y)
    effect_rect = _band(width, height, effect_font, effect_lines, EFFECT_Y)
    gap = max(2, int(height * 0.012))
    floor = int(height * 0.955)
    if effect_rect.bottom > floor:
        effect_rect.bottom = floor
    if flavour_rect.bottom + gap > effect_rect.top:
        flavour_rect.bottom = effect_rect.top - gap
    if title_rect.top < int(height * 0.035):
        title_rect.top = int(height * 0.035)
    art = pygame.Rect(
        int(width * ART_MARGIN_X),
        int(height * ART_TOP),
        max(1, int(width * (1 - ART_MARGIN_X * 2))),
        max(1, int(height * (ART_BOTTOM - ART_TOP))),
    )
    if title_rect.bottom + gap > art.top:
        art.top = title_rect.bottom + gap
    if art.bottom > flavour_rect.top - gap:
        art.height = max(1, flavour_rect.top - gap - art.top)
    _blit_art(card, assets, relic, art)
    _draw_title(card, title_lines, title_font, title_rect)
    _draw_lines(card, flavour_lines, flavour_font, flavour_font, flavour_rect)
    _draw_lines(card, effect_lines, effect_font, _serif(max(7, effect_font.get_point_size()), True), effect_rect)
    return card


def _band(width: int, height: int, font: pygame.font.Font, lines: list[str], anchor: float) -> pygame.Rect:
    band_h = max(1, font.get_height() * max(1, len(lines)))
    rect = pygame.Rect(int(width * TEXT_MARGIN), 0, max(1, int(width * (1 - TEXT_MARGIN * 2))), band_h)
    rect.centery = int(height * anchor)
    return rect


def _fit_block(
    text: str,
    width: int,
    start: int,
    max_lines: int,
    bold: bool,
    single: bool = False,
) -> tuple[pygame.font.Font, list[str]]:
    plain = text.replace("\u00a0", " ")
    size = max(7, int(start))
    floor = max(7, int(start * 0.7)) if single else 7
    while size > floor:
        font = _serif(size, bold)
        if font.size(plain)[0] <= width:
            return font, [text]
        if not single:
            lines = wrap_text(font, text, width)
            if 0 < len(lines) <= max_lines:
                return font, lines
        size -= 1
    font = _serif(max(7, floor if single else size), bold)
    if font.size(plain)[0] <= width:
        return font, [text]
    lines = wrap_text(font, text, max(1, width)) or [text]
    return font, lines[: max(1, max_lines)]


def _protect(text: str) -> str:
    protected = text
    for word in _KEYWORDS:
        protected = protected.replace(word, word.replace(" ", "\u00a0"))
    return protected


def _blit_art(card: pygame.Surface, assets: AssetManager, relic: RelicDef, rect: pygame.Rect) -> None:
    if rect.w < 2 or rect.h < 2:
        return
    image = artwork.image(assets, relic)
    if image is None:
        return
    fitted = _fit(image, rect.w, rect.h)
    card.blit(fitted, fitted.get_rect(center=rect.center))


def _fit(source: pygame.Surface, max_width: int, max_height: int) -> pygame.Surface:
    width, height = source.get_size()
    scale = min(max_width / max(1, width), max_height / max(1, height))
    size = (max(1, int(round(width * scale))), max(1, int(round(height * scale))))
    if size == (width, height):
        return source
    return pygame.transform.smoothscale(source, size)


def _draw_title(screen: pygame.Surface, lines: list[str], font: pygame.font.Font, rect: pygame.Rect) -> None:
    if len(lines) == 1:
        _draw_tracked(screen, lines[0].replace("\u00a0", " "), font, rect)
        return
    _draw_lines(screen, lines, font, font, rect)


def _draw_lines(
    screen: pygame.Surface,
    lines: list[str],
    font: pygame.font.Font,
    bold: pygame.font.Font,
    rect: pygame.Rect,
) -> None:
    total = font.get_height() * len(lines)
    y = rect.y + max(0, (rect.h - total) // 2)
    step = font.get_height()
    for line in lines:
        _draw_rich(screen, line, font, bold, (rect.centerx, y + step // 2))
        y += step


def _draw_rich(
    screen: pygame.Surface,
    line: str,
    font: pygame.font.Font,
    bold: pygame.font.Font,
    center: tuple[int, int],
) -> None:
    glyphs = []
    for text, strong in _runs(line):
        glyphs.append((bold if strong else font).render(text, True, INK))
    if not glyphs:
        return
    total = sum(glyph.get_width() for glyph in glyphs)
    x = center[0] - total // 2
    for glyph in glyphs:
        screen.blit(glyph, (x, center[1] - glyph.get_height() // 2))
        x += glyph.get_width()


def _runs(line: str) -> list[tuple[str, bool]]:
    upper = line.upper()
    cursor = 0
    runs: list[tuple[str, bool]] = []
    while cursor < len(line):
        found = ""
        for word in _KEYWORDS:
            token = word.replace(" ", "\u00a0")
            for candidate in (token, word):
                if not upper.startswith(candidate, cursor):
                    continue
                end = cursor + len(candidate)
                before = cursor == 0 or not line[cursor - 1].isalnum()
                after = end >= len(line) or not line[end].isalnum()
                if before and after and len(candidate) > len(found):
                    found = candidate
        if found:
            runs.append((line[cursor : cursor + len(found)].replace("\u00a0", " "), True))
            cursor += len(found)
            continue
        nxt = len(line)
        for word in _KEYWORDS:
            token = word.replace(" ", "\u00a0")
            for candidate in (token, word):
                at = upper.find(candidate, cursor + 1)
                if at != -1:
                    nxt = min(nxt, at)
        runs.append((line[cursor:nxt].replace("\u00a0", " "), False))
        cursor = nxt
    return [(text, strong) for text, strong in runs if text]


def _draw_tracked(screen: pygame.Surface, text: str, font: pygame.font.Font, rect: pygame.Rect) -> None:
    gap = max(0, min(4, rect.w // 48))
    glyphs = [font.render(character, True, INK) for character in text]
    total = sum(glyph.get_width() for glyph in glyphs) + gap * max(0, len(glyphs) - 1)
    if total > rect.w:
        gap = 0
        total = sum(glyph.get_width() for glyph in glyphs)
    x = rect.centerx - total // 2
    for glyph in glyphs:
        screen.blit(glyph, (x, rect.centery - glyph.get_height() // 2))
        x += glyph.get_width() + gap


def _portrait_rect(bounds: pygame.Rect) -> pygame.Rect:
    if bounds.w < 2 or bounds.h < 2:
        return bounds
    if abs(bounds.w / bounds.h - CARD_RATIO) <= 0.02:
        return bounds
    if bounds.w / bounds.h > CARD_RATIO:
        width = max(1, int(round(bounds.h * CARD_RATIO)))
        rect = pygame.Rect(0, 0, min(bounds.w, width), bounds.h)
    else:
        height = max(1, int(round(bounds.w / CARD_RATIO)))
        rect = pygame.Rect(0, 0, bounds.w, min(bounds.h, height))
    rect.center = bounds.center
    return rect


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
