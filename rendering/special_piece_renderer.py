import pygame

from rendering.trait_style import trait_style


class SpecialPieceRenderer:
    def __init__(self) -> None:
        self._cache: dict[tuple, pygame.Surface] = {}

    def clear(self) -> None:
        self._cache.clear()

    def image(self, assets, color: str, kind: str, trait: str | None, box: int) -> pygame.Surface:
        fitted = assets.fitted(f"{color}_{kind}", box, box)
        if trait not in ("golden", "ghost", "wooden", "explosive"):
            return fitted
        strong = trait_style.strong
        key = (color, kind, trait, fitted.get_width(), fitted.get_height(), strong)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        surface = _paint(fitted.copy(), trait, strong)
        self._cache[key] = surface
        return surface


def _paint(source: pygame.Surface, trait: str, strong: bool) -> pygame.Surface:
    if trait == "golden":
        tint = (236, 164, 28) if strong else (222, 176, 72)
        edge = (255, 214, 72) if strong else (196, 146, 48)
        return _outline(_tint(source, tint, 0.82 if strong else 0.48), edge, 2 if strong else 1)
    if trait == "ghost":
        body = _fade(_tint(source, (126, 214, 236) if strong else (168, 214, 236), 0.88 if strong else 0.78), 0.78 if strong else 0.60)
        if not strong:
            return body
        return _outline(body, (210, 246, 255), 2)
    if trait == "wooden":
        body = _grain(_tint(source, (128, 74, 32) if strong else (168, 108, 54), 0.84 if strong else 0.62), strong)
        if not strong:
            return body
        return _outline(body, (72, 42, 22), 2)
    body = _tint(source, (228, 64, 24) if strong else (214, 96, 42), 0.76 if strong else 0.45)
    if not strong:
        return body
    return _outline(body, (186, 48, 22), 1)


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


def _outline(image: pygame.Surface, color: tuple[int, int, int], pad: int = 1) -> pygame.Surface:
    mask = pygame.mask.from_surface(image, threshold=24)
    width, height = image.get_size()
    canvas = pygame.Surface((width + pad * 2, height + pad * 2), pygame.SRCALPHA)
    stamp = mask.to_surface(setcolor=(*color, 230), unsetcolor=(0, 0, 0, 0))
    for ox in range(pad * 2 + 1):
        for oy in range(pad * 2 + 1):
            if ox == pad and oy == pad:
                continue
            canvas.blit(stamp, (ox, oy))
    cover = mask.to_surface(setcolor=(0, 0, 0, 255), unsetcolor=(0, 0, 0, 0))
    canvas.blit(cover, (pad, pad), special_flags=pygame.BLEND_RGBA_SUB)
    canvas.blit(image, (pad, pad))
    return canvas


def _grain(image: pygame.Surface, strong: bool) -> pygame.Surface:
    width, height = image.get_size()
    strokes = pygame.Surface((width, height), pygame.SRCALPHA)
    color = (62, 32, 16, 220) if strong else (92, 58, 32, 160)
    ratios = (0.42, 0.54, 0.66, 0.78) if strong else (0.56, 0.68, 0.80)
    for index, ratio in enumerate(ratios):
        y = int(height * ratio)
        start = int(width * 0.18)
        end = int(width * 0.84)
        bend = max(1, height // 18)
        pygame.draw.line(strokes, color, (start, y + index), (end, y - bend), max(2, height // 28) if strong else max(1, height // 48))
    mask = pygame.mask.from_surface(image, threshold=24)
    cover = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
    strokes.blit(cover, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    marked = image.copy()
    marked.blit(strokes, (0, 0))
    return marked


special_pieces = SpecialPieceRenderer()
