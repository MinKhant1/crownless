"""The oil-painting look every screen shares: palette, Cinzel titles, parchment, carved wood and plaque buttons.

Taken from the Techies_GA1 reference card: muted umber and sepia, aged parchment, burgundy cloth,
antique gold for titles and prices, and a warm candle glow. Textures are drawn in code and cached by size.
"""

import math
import random
from pathlib import Path

import pygame

UMBER_DEEP = (22, 13, 8)
UMBER = (40, 25, 16)
WALNUT = (62, 39, 24)
OAK = (98, 64, 38)
INK = (50, 31, 19)
INK_SOFT = (92, 62, 38)
PARCHMENT = (229, 210, 171)
PARCHMENT_SHADE = (196, 168, 122)
BURGUNDY = (112, 32, 30)
BURGUNDY_DEEP = (66, 18, 17)
GOLD = (200, 158, 86)
GOLD_BRIGHT = (236, 204, 132)
GOLD_DIM = (138, 104, 56)
IVORY = (241, 228, 200)
IVORY_SOFT = (214, 194, 158)
CANDLE = (255, 204, 132)
ALERT = (176, 52, 40)

FONT_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"

_TITLE_FONTS: dict[tuple[int, bool], pygame.font.Font] = {}
_BODY_FONTS: dict[tuple[int, bool, bool], pygame.font.Font] = {}
_CACHE: dict[tuple, pygame.Surface] = {}


def title_font(size: int, bold: bool = True) -> pygame.font.Font:
    """Cinzel: Roman capitals with small-capital lowercase, like the CROWNLESS logo."""
    size = max(9, int(size))
    key = (size, bold)
    font = _TITLE_FONTS.get(key)
    if font is None:
        path = FONT_DIR / ("Cinzel-Bold.ttf" if bold else "Cinzel-Regular.ttf")
        if path.exists():
            font = pygame.font.Font(str(path), size)
        else:
            font = pygame.font.SysFont("georgia", size, bold=bold)
        _TITLE_FONTS[key] = font
    return font


def body_font(size: int, bold: bool = False, italic: bool = False) -> pygame.font.Font:
    """Georgia for rules text: plain, readable, and shipped with Windows and macOS."""
    size = max(10, int(size))
    key = (size, bold, italic)
    font = _BODY_FONTS.get(key)
    if font is None:
        font = pygame.font.SysFont("georgia", size, bold=bold, italic=italic)
        _BODY_FONTS[key] = font
    return font


def fitted_title(text: str, size: int, max_width: int, bold: bool = True, floor: int = 10) -> pygame.font.Font:
    size = max(floor, int(size))
    font = title_font(size, bold)
    while size > floor and font.size(text)[0] > max_width:
        size -= 1
        font = title_font(size, bold)
    return font


def text(
    screen: pygame.Surface,
    label: str,
    font: pygame.font.Font,
    color: tuple[int, int, int],
    shadow: tuple[int, int, int, int] | None = None,
    alpha: int = 255,
    **anchor: tuple[int, int],
) -> pygame.Rect:
    """Blit text at an anchor (center=, midleft=, midtop=, ...). A shadow 1px below reads as engraved."""
    surface = font.render(label, True, color)
    rect = surface.get_rect(**anchor) if anchor else surface.get_rect()
    if shadow is not None:
        under = font.render(label, True, shadow[:3])
        under.set_alpha(min(alpha, shadow[3]))
        screen.blit(under, rect.move(0, max(1, font.get_height() // 18)))
    if alpha < 255:
        surface.set_alpha(alpha)
    screen.blit(surface, rect)
    return rect


def wrap(font: pygame.font.Font, label: str, width: int) -> list[str]:
    words = label.split()
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


def soft_shadow(size: tuple[int, int], radius: int = 10, spread: int = 14, alpha: int = 120) -> pygame.Surface:
    """A blurred dark slab the size of a panel plus `spread` on each side. Blit it offset downward."""
    width, height = max(1, size[0]), max(1, size[1])
    key = ("shadow", width, height, radius, spread, alpha)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    full = (width + spread * 2, height + spread * 2)
    shrink = max(2, min(6, spread // 3))
    small = pygame.Surface((max(2, full[0] // shrink), max(2, full[1] // shrink)), pygame.SRCALPHA)
    inner = pygame.Rect(spread // shrink, spread // shrink, max(1, width // shrink), max(1, height // shrink))
    pygame.draw.rect(small, (8, 4, 2, alpha), inner, border_radius=max(0, radius // shrink))
    blurred = pygame.transform.smoothscale(small, (max(2, small.get_width() // 2), max(2, small.get_height() // 2)))
    shadow = pygame.transform.smoothscale(blurred, full)
    _CACHE[key] = shadow
    return shadow


def drop_shadow(screen: pygame.Surface, rect: pygame.Rect, offset: int = 8, spread: int = 14, alpha: int = 120, radius: int = 10) -> None:
    shadow = soft_shadow(rect.size, radius, spread, alpha)
    screen.blit(shadow, (rect.x - spread, rect.y - spread + offset))


def _grain_tile() -> pygame.Surface:
    key = ("grain",)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    rng = random.Random(41)
    side = 96
    tile = pygame.Surface((side, side), pygame.SRCALPHA)
    for y in range(side):
        for x in range(side):
            weave = 10 if (x % 3 == 0) != (y % 3 == 0) else 0
            value = rng.randint(0, 34) + weave
            if value > 26:
                tile.set_at((x, y), (255, 240, 214, value - 26))
            elif value < 8:
                tile.set_at((x, y), (12, 6, 2, 14 - value))
    _CACHE[key] = tile
    return tile


def canvas_grain(screen: pygame.Surface, area: pygame.Rect | None = None) -> None:
    """Fine canvas weave over an area: the painted-surface texture of the reference card."""
    area = screen.get_rect() if area is None else area.clip(screen.get_rect())
    tile = _grain_tile()
    previous = screen.get_clip()
    screen.set_clip(area if previous is None else area.clip(previous))
    for y in range(area.y - area.y % tile.get_height(), area.bottom, tile.get_height()):
        for x in range(area.x - area.x % tile.get_width(), area.right, tile.get_width()):
            screen.blit(tile, (x, y))
    screen.set_clip(previous)


def candle_glow(size: tuple[int, int], color: tuple[int, int, int] = CANDLE, strength: int = 60) -> pygame.Surface:
    """A soft radial warm light, for BLEND_RGB_ADD over a scene."""
    width, height = max(2, size[0]), max(2, size[1])
    key = ("glow", width, height, color, strength)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    small = pygame.Surface((48, 48))
    small.fill((0, 0, 0))
    for step in range(24, 0, -1):
        fade = (1 - step / 24) ** 1.6
        tint = tuple(int(channel * strength / 255 * fade) for channel in color)
        pygame.draw.circle(small, tint, (24, 24), step)
    glow = pygame.transform.smoothscale(small, (width, height))
    _CACHE[key] = glow
    return glow


def _jagged(rect: pygame.Rect, inset: float, offsets: list[float], step: int) -> list[tuple[float, float]]:
    """Points around a rectangle, pushed inward by `inset` plus a per-point wear offset."""
    points: list[tuple[float, float]] = []
    left, top, right, bottom = rect.left, rect.top, rect.right - 1, rect.bottom - 1
    index = 0

    def push(x: float, y: float, nx: float, ny: float) -> None:
        nonlocal index
        wear = offsets[index % len(offsets)]
        index += 1
        points.append((x + nx * (inset + wear), y + ny * (inset + wear)))

    x = left
    while x < right:
        push(x, top, 0, 1)
        x += step
    y = top
    while y < bottom:
        push(right, y, -1, 0)
        y += step
    x = right
    while x > left:
        push(x, bottom, 0, -1)
        x -= step
    y = bottom
    while y > top:
        push(left, y, 1, 0)
        y -= step
    return points


_PAPER: list[pygame.Surface | None] = [None]


def _parchment_source(assets) -> pygame.Surface | None:
    """The relic card's painted paper, remembered the first time any screen passes its assets."""
    if assets is not None and assets.has("relic_card"):
        raw = assets.get("relic_card")
        margin_x = int(raw.get_width() * 0.05)
        margin_y = int(raw.get_height() * 0.04)
        _PAPER[0] = raw.subsurface((margin_x, margin_y, raw.get_width() - margin_x * 2, raw.get_height() - margin_y * 2))
    return _PAPER[0]


def parchment(assets, size: tuple[int, int], seed: int = 0, worn: bool = True) -> pygame.Surface:
    """Aged parchment with a torn, scorched edge. Uses the relic card's painted paper when available."""
    width, height = max(8, int(size[0])), max(8, int(size[1]))
    source = _parchment_source(assets)
    key = ("parchment", width, height, seed, worn, source is not None)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    sheet = pygame.Surface((width, height), pygame.SRCALPHA)
    if source is not None:
        if width > height and source.get_height() > source.get_width():
            source = pygame.transform.rotate(source, 90)
        scale = max(width / source.get_width(), height / source.get_height())
        scaled = pygame.transform.smoothscale(
            source, (max(1, int(source.get_width() * scale) + 1), max(1, int(source.get_height() * scale) + 1))
        )
        sheet.blit(scaled, scaled.get_rect(center=(width // 2, height // 2)))
    else:
        sheet.fill((*PARCHMENT, 255))
    sheet.fill((246, 230, 204), special_flags=pygame.BLEND_RGB_MULT)
    rng = random.Random(f"parchment:{seed}:{width}:{height}")
    stains = pygame.Surface((width, height), pygame.SRCALPHA)
    for _ in range(max(3, (width * height) // 90000)):
        blot = pygame.Rect(0, 0, rng.randint(width // 6, width // 2 + 1), rng.randint(height // 8, height // 3 + 1))
        blot.center = (rng.randint(0, width), rng.randint(0, height))
        pygame.draw.ellipse(stains, (120, 82, 40, rng.randint(6, 14)), blot)
    sheet.blit(stains, (0, 0))
    if not worn:
        _CACHE[key] = sheet
        return sheet
    step = 9
    offsets = [max(0.0, rng.gauss(1.4, 1.5)) for _ in range(512)]
    body = sheet.get_rect()
    burn = pygame.Surface((width, height), pygame.SRCALPHA)
    depth = max(8, min(26, min(width, height) // 12))
    for layer in range(depth, 0, -1):
        fade = (1 - layer / depth) ** 2.2
        pygame.draw.polygon(burn, (96, 58, 26, int(150 * fade)), _jagged(body, layer, offsets, step), 3)
    sheet.blit(burn, (0, 0))
    mask = pygame.Surface((width, height), pygame.SRCALPHA)
    mask.fill((255, 255, 255, 0))
    pygame.draw.polygon(mask, (255, 255, 255, 255), _jagged(body, 0.5, offsets, step))
    sheet.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    _CACHE[key] = sheet
    return sheet


def _wood_grain(width: int, height: int, seed: int, tone: tuple[int, int, int]) -> pygame.Surface:
    """Straight-grained walnut boards, so panels read as carved wood against the swirling backdrop."""
    rng = random.Random(f"wood:{seed}")
    vertical = height >= width
    across = width if vertical else height
    along = height if vertical else width
    cols = max(6, across // 7)
    rows = max(3, along // 26)
    small = pygame.Surface((cols, rows) if vertical else (rows, cols))
    streak = [rng.gauss(0, 1) for _ in range(cols)]
    for _ in range(2):
        streak = [(streak[max(0, i - 1)] + streak[i] * 2 + streak[min(cols - 1, i + 1)]) / 4 for i in range(cols)]
    drift = [rng.gauss(0, 1) for _ in range(rows)]
    for x in range(cols):
        for y in range(rows):
            wave = math.sin(y * 0.45 + x * 0.9 + drift[y] * 0.6) * 2.2
            value = streak[x] * 7 + wave + rng.uniform(-1.6, 1.6)
            color = tuple(max(0, min(255, int(channel + value * (1.0 if i == 0 else 0.72)))) for i, channel in enumerate(tone))
            small.set_at((x, y) if vertical else (y, x), color)
    return pygame.transform.smoothscale(small, (width, height))


def wood_panel(size: tuple[int, int], seed: int = 0, radius: int = 10) -> pygame.Surface:
    """A carved walnut panel: grain, a bevelled rim, a gold inlay groove and small gold corner studs."""
    width, height = max(16, int(size[0])), max(16, int(size[1]))
    key = ("wood", width, height, seed, radius)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    panel = pygame.Surface((width, height), pygame.SRCALPHA)
    grain = _wood_grain(width, height, seed, (52, 32, 20))
    body = panel.get_rect()
    shape = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(shape, (255, 255, 255, 255), body, border_radius=radius)
    panel.blit(grain, (0, 0))
    canvas_grain(panel)
    shade = pygame.Surface((width, height), pygame.SRCALPHA)
    rim = max(5, min(9, min(width, height) // 30))
    for step in range(rim):
        fade = (1 - step / rim) ** 1.3
        inner = body.inflate(-step * 2, -step * 2)
        pygame.draw.line(shade, (255, 222, 170, int(70 * fade)), inner.topleft, (inner.right - 1, inner.top))
        pygame.draw.line(shade, (255, 222, 170, int(52 * fade)), inner.topleft, (inner.left, inner.bottom - 1))
        pygame.draw.line(shade, (6, 3, 1, int(150 * fade)), (inner.left, inner.bottom - 1), (inner.right - 1, inner.bottom - 1))
        pygame.draw.line(shade, (6, 3, 1, int(130 * fade)), (inner.right - 1, inner.top), (inner.right - 1, inner.bottom - 1))
    panel.blit(shade, (0, 0))
    groove = body.inflate(-(rim * 2 + 6), -(rim * 2 + 6))
    pygame.draw.rect(panel, (14, 8, 4), groove.move(0, 1), width=1, border_radius=max(0, radius - 4))
    pygame.draw.rect(panel, GOLD_DIM, groove, width=1, border_radius=max(0, radius - 4))
    for corner in (groove.topleft, (groove.right - 1, groove.top), (groove.left, groove.bottom - 1), (groove.right - 1, groove.bottom - 1)):
        _stud(panel, corner, 3)
    pygame.draw.rect(panel, UMBER_DEEP, body, width=2, border_radius=radius)
    panel.blit(shape, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    _CACHE[key] = panel
    return panel


def _stud(surface: pygame.Surface, center: tuple[int, int], radius: int) -> None:
    x, y = center
    diamond = [(x, y - radius - 1), (x + radius + 1, y), (x, y + radius + 1), (x - radius - 1, y)]
    pygame.draw.polygon(surface, (24, 14, 6), [(px, py + 1) for px, py in diamond])
    pygame.draw.polygon(surface, GOLD, diamond)
    pygame.draw.polygon(surface, GOLD_BRIGHT, [(x, y - radius), (x + radius, y), (x, y)])


def draw_wood_panel(screen: pygame.Surface, rect: pygame.Rect, seed: int = 0, shadow: bool = True) -> None:
    if shadow:
        drop_shadow(screen, rect, offset=6, spread=12, alpha=110)
    screen.blit(wood_panel(rect.size, seed), rect.topleft)


def draw_parchment(screen: pygame.Surface, assets, rect: pygame.Rect, seed: int = 0, shadow: bool = True, alpha: int = 255) -> None:
    if shadow:
        drop_shadow(screen, rect, offset=8, spread=16, alpha=int(130 * alpha / 255))
    sheet = parchment(assets, rect.size, seed)
    if alpha < 255:
        sheet = sheet.copy()
        sheet.set_alpha(alpha)
    screen.blit(sheet, rect.topleft)


def framed_parchment(assets, size: tuple[int, int], seed: int = 0, border: int = 14) -> pygame.Surface:
    """Parchment laid into a carved wood frame, for the larger pages (How to Play, Collection, the win panel)."""
    width, height = max(40, int(size[0])), max(40, int(size[1]))
    key = ("framed", width, height, seed, border, _parchment_source(assets) is not None)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    surface = wood_panel((width, height), seed, radius=12).copy()
    inner = pygame.Rect(border, border, width - border * 2, height - border * 2)
    pygame.draw.rect(surface, (10, 6, 3), inner.inflate(4, 4), border_radius=4)
    sheet = parchment(assets, inner.size, seed, worn=False)
    surface.blit(sheet, inner.topleft)
    inset = pygame.Surface(inner.size, pygame.SRCALPHA)
    for step in range(10):
        fade = (1 - step / 10) ** 1.8
        rect = inset.get_rect().inflate(-step * 2, -step * 2)
        pygame.draw.rect(inset, (60, 34, 14, int(120 * fade)), rect, width=1)
    surface.blit(inset, inner.topleft)
    _CACHE[key] = surface
    return surface


def ornament_rule(screen: pygame.Surface, center: tuple[int, int], width: int, color: tuple[int, int, int] = GOLD, alpha: int = 255) -> None:
    """An engraved divider: a line that fades at both ends with a small diamond at its middle."""
    width = max(12, int(width))
    key = ("rule", width, color)
    rule = _CACHE.get(key)
    if rule is None:
        rule = pygame.Surface((width, 11), pygame.SRCALPHA)
        half = width // 2
        for x in range(width):
            distance = abs(x - half) / max(1, half)
            fade = max(0.0, 1.0 - distance) ** 0.7
            if abs(x - half) < 10:
                continue
            rule.set_at((x, 5), (*color, int(230 * fade)))
            rule.set_at((x, 6), (12, 6, 2, int(90 * fade)))
        pygame.draw.polygon(rule, color, [(half, 1), (half + 5, 5), (half, 9), (half - 5, 5)])
        pygame.draw.circle(rule, color, (half - 9, 5), 1)
        pygame.draw.circle(rule, color, (half + 9, 5), 1)
        _CACHE[key] = rule
    if alpha < 255:
        rule = rule.copy()
        rule.set_alpha(alpha)
    screen.blit(rule, rule.get_rect(center=center))


def _plaque_points(rect: pygame.Rect, chamfer: int) -> list[tuple[int, int]]:
    return [
        (rect.left + chamfer, rect.top),
        (rect.right - 1 - chamfer, rect.top),
        (rect.right - 1, rect.top + chamfer),
        (rect.right - 1, rect.bottom - 1 - chamfer),
        (rect.right - 1 - chamfer, rect.bottom - 1),
        (rect.left + chamfer, rect.bottom - 1),
        (rect.left, rect.bottom - 1 - chamfer),
        (rect.left, rect.top + chamfer),
    ]


def plaque(size: tuple[int, int], state: str = "idle") -> pygame.Surface:
    """A carved walnut name plate with clipped corners and a gold rim, like the shop's Buy plaque.

    state is idle, hover, pressed, selected or disabled.
    """
    width, height = max(12, int(size[0])), max(12, int(size[1]))
    key = ("plaque", width, height, state)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    body = surface.get_rect()
    chamfer = max(4, min(12, height // 4))
    tone = {
        "idle": (64, 38, 22),
        "hover": (86, 52, 28),
        "pressed": (50, 29, 16),
        "selected": (104, 34, 30),
        "disabled": (54, 46, 40),
    }.get(state, (64, 38, 22))
    grain = _wood_grain(width, height, width * 7 + height, tone)
    shape = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.polygon(shape, (255, 255, 255, 255), _plaque_points(body, chamfer))
    surface.blit(grain, (0, 0))
    light = pygame.Surface((width, height), pygame.SRCALPHA)
    band = max(3, height // 7)
    for step in range(band):
        fade = (1 - step / band) ** 1.4
        pygame.draw.line(light, (255, 226, 176, int(60 * fade)), (0, step + 1), (width, step + 1))
        pygame.draw.line(light, (4, 2, 1, int(110 * fade)), (0, height - 2 - step), (width, height - 2 - step))
    surface.blit(light, (0, 0))
    rim = {"hover": GOLD_BRIGHT, "selected": GOLD_BRIGHT, "disabled": (118, 104, 86)}.get(state, GOLD)
    inner = body.inflate(-6, -6)
    pygame.draw.polygon(surface, (14, 8, 4), _plaque_points(inner.move(0, 1), max(2, chamfer - 3)), 1)
    pygame.draw.polygon(surface, rim if state != "disabled" else (96, 86, 72), _plaque_points(inner, max(2, chamfer - 3)), 1)
    pygame.draw.polygon(surface, rim, _plaque_points(body, chamfer), 2)
    surface.blit(shape, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    _CACHE[key] = surface
    return surface


def draw_plaque_button(
    screen: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    state: str = "idle",
    font_size: int = 20,
) -> None:
    """A wooden-plaque button. The label is Cinzel, engraved into the wood."""
    if state != "disabled":
        from rendering.ui_sounds import ui_sounds

        ui_sounds.register(screen, rect, label)
    drawn = rect.move(0, 2) if state == "pressed" else rect
    if state != "disabled":
        drop_shadow(screen, rect, offset=4 if state != "pressed" else 2, spread=6, alpha=120, radius=6)
    if state in ("hover", "selected"):
        glow = candle_glow((rect.w + 40, rect.h + 34), strength=46)
        screen.blit(glow, glow.get_rect(center=drawn.center), special_flags=pygame.BLEND_RGB_ADD)
    screen.blit(plaque(drawn.size, state), drawn.topleft)
    color = {"disabled": (150, 138, 120), "hover": (255, 240, 212), "selected": (255, 236, 196)}.get(state, IVORY)
    font = fitted_title(label, font_size, max(10, drawn.w - 22), bold=True, floor=10)
    text(screen, label, font, color, shadow=(8, 4, 2, 200), center=(drawn.centerx, drawn.centery))


def button_state(rect: pygame.Rect, enabled: bool = True, selected: bool = False) -> str:
    if not enabled:
        return "disabled"
    if selected:
        return "selected"
    if pygame.display.get_surface() is None:
        return "idle"
    pointer = pygame.mouse.get_pos()
    if rect.collidepoint(pointer):
        return "pressed" if pygame.mouse.get_pressed()[0] else "hover"
    return "idle"


def tooltip_panel(screen: pygame.Surface, assets, rect: pygame.Rect) -> None:
    """A small parchment slip with a thin ink border, for hover tooltips."""
    drop_shadow(screen, rect, offset=5, spread=8, alpha=120, radius=6)
    key = ("tip", rect.w, rect.h, _parchment_source(assets) is not None)
    slip = _CACHE.get(key)
    if slip is None:
        slip = parchment(assets, rect.size, seed=rect.w, worn=False).copy()
        pygame.draw.rect(slip, (92, 60, 32), slip.get_rect(), width=2)
        pygame.draw.rect(slip, (196, 160, 104), slip.get_rect().inflate(-6, -6), width=1)
        _CACHE[key] = slip
    screen.blit(slip, rect.topleft)


def ease_out_back(amount: float, overshoot: float = 1.6) -> float:
    amount = max(0.0, min(1.0, amount)) - 1.0
    return 1.0 + (overshoot + 1.0) * amount ** 3 + overshoot * amount ** 2


def sparkle(screen: pygame.Surface, center: tuple[int, int], size: float, alpha: int, color: tuple[int, int, int] = (255, 244, 214)) -> None:
    """A four-point star glint."""
    if size < 1 or alpha <= 0:
        return
    extent = int(size * 2 + 4)
    star = pygame.Surface((extent * 2, extent * 2), pygame.SRCALPHA)
    mid = extent
    long_arm = size * 2
    short = max(1.0, size * 0.28)
    points = []
    for index in range(8):
        angle = math.pi / 4 * index - math.pi / 2
        reach = long_arm if index % 2 == 0 else short
        points.append((mid + math.cos(angle) * reach, mid + math.sin(angle) * reach))
    pygame.draw.polygon(star, (*color, alpha), points)
    pygame.draw.circle(star, (*color, min(255, alpha)), (mid, mid), max(1, int(size * 0.35)))
    screen.blit(star, star.get_rect(center=center), special_flags=pygame.BLEND_RGBA_ADD)


def clear_style_cache() -> None:
    _CACHE.clear()
