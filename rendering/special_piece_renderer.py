import pygame


class SpecialPieceRenderer:
    def __init__(self) -> None:
        self._cache: dict[tuple, pygame.Surface] = {}

    def clear(self) -> None:
        self._cache.clear()

    def image(self, assets, color: str, kind: str, trait: str | None, box: int) -> pygame.Surface:
        fitted = assets.fitted(f"{color}_{kind}", box, box)
        if trait not in ("golden", "ghost", "wooden", "explosive"):
            return fitted
        key = (color, kind, trait, fitted.get_width(), fitted.get_height())
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        source = fitted.copy()
        if trait == "golden":
            surface = _outline(_tint(source, (222, 176, 72), 0.48), (196, 146, 48))
        elif trait == "ghost":
            surface = _fade(_tint(source, (168, 214, 236), 0.78), 0.60)
        elif trait == "wooden":
            surface = _grain(_tint(source, (168, 108, 54), 0.62))
        else:
            surface = _tint(source, (214, 96, 42), 0.45)
        self._cache[key] = surface
        return surface


def _tint(image: pygame.Surface, color: tuple[int, int, int], strength: float) -> pygame.Surface:
    tinted = pygame.Surface(image.get_size(), pygame.SRCALPHA)
    tinted.fill((*color, 255))
    tinted.blit(image, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    if strength >= 0.99:
        return tinted
    mixed = image.copy()
    layer = tinted.copy()
    fade = pygame.Surface(image.get_size(), pygame.SRCALPHA)
    fade.fill((255, 255, 255, int(255 * strength)))
    layer.blit(fade, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    mixed.blit(layer, (0, 0))
    return mixed


def _fade(image: pygame.Surface, opacity: float) -> pygame.Surface:
    faded = image.copy()
    shade = pygame.Surface(image.get_size(), pygame.SRCALPHA)
    shade.fill((255, 255, 255, int(255 * opacity)))
    faded.blit(shade, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return faded


def _outline(image: pygame.Surface, color: tuple[int, int, int]) -> pygame.Surface:
    pad = 1
    mask = pygame.mask.from_surface(image, threshold=24)
    width, height = image.get_size()
    canvas = pygame.Surface((width + pad * 2, height + pad * 2), pygame.SRCALPHA)
    stamp = mask.to_surface(setcolor=(*color, 230), unsetcolor=(0, 0, 0, 0))
    for ox in range(pad * 2 + 1):
        for oy in range(pad * 2 + 1):
            if ox == pad and oy == pad:
                continue
            canvas.blit(stamp, (ox, oy))
    canvas.blit(image, (pad, pad))
    return canvas


def _grain(image: pygame.Surface) -> pygame.Surface:
    width, height = image.get_size()
    strokes = pygame.Surface((width, height), pygame.SRCALPHA)
    color = (214, 164, 102, 150)
    for index, ratio in enumerate((0.56, 0.68, 0.80)):
        y = int(height * ratio)
        start = int(width * 0.22)
        end = int(width * 0.80)
        bend = max(1, height // 24)
        pygame.draw.line(strokes, color, (start, y + index), (end, y - bend), max(1, height // 48))
    mask = pygame.mask.from_surface(image, threshold=24)
    cover = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
    strokes.blit(cover, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    marked = image.copy()
    marked.blit(strokes, (0, 0))
    return marked


special_pieces = SpecialPieceRenderer()
