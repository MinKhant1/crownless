import pygame

from config.settings import (
    PIECE_SHADOW_ALPHA,
    PIECE_SHADOW_HEIGHT,
    PIECE_SHADOW_LIFT_SPREAD,
    PIECE_SHADOW_OFFSET,
    PIECE_SHADOW_WIDTH,
)
from game.piece import Piece
from rendering.special_piece_renderer import special_pieces


class FigurineCache:
    def __init__(self) -> None:
        self._cache: dict[tuple, pygame.Surface] = {}
        self._shadows: dict[tuple, pygame.Surface] = {}

    def clear(self) -> None:
        self._cache.clear()
        self._shadows.clear()

    def image(self, assets, piece: Piece, box: int) -> pygame.Surface:
        key = (piece.color, piece.kind, piece.trait, box)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        source = special_pieces.image(assets, piece.color, piece.kind, piece.trait, box)
        dressed = _dress(source, piece.trait == "ghost")
        self._cache[key] = dressed
        return dressed

    def ellipse(self, width: int, height: int, alpha: int) -> pygame.Surface:
        key = (width, height, alpha)
        cached = self._shadows.get(key)
        if cached is not None:
            return cached
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.ellipse(surface, (28, 16, 10, alpha), surface.get_rect())
        self._shadows[key] = surface
        return surface


def draw_contact_shadow(
    screen: pygame.Surface,
    center: tuple[float, float],
    square: int,
    lift_ratio: float,
) -> pygame.Rect:
    lift_ratio = max(0.0, min(1.0, lift_ratio))
    spread = 1 + PIECE_SHADOW_LIFT_SPREAD * lift_ratio
    radius_x = max(3, int(square * PIECE_SHADOW_WIDTH * spread))
    radius_y = max(2, int(square * PIECE_SHADOW_HEIGHT * spread))
    base = PIECE_SHADOW_ALPHA * (1 - 0.22 * lift_ratio)
    outer: pygame.Rect | None = None
    point = (int(center[0]), int(center[1]))
    for scale, fade in ((1.55, 0.28), (1.05, 0.62), (0.62, 1.0)):
        width = max(2, int(radius_x * 2 * scale))
        height = max(2, int(radius_y * 2 * scale))
        alpha = max(1, min(255, int(base * fade) // 4 * 4))
        blob = figurines.ellipse(width, height, alpha)
        dest = blob.get_rect(center=point)
        screen.blit(blob, dest)
        if outer is None:
            outer = dest
    return outer if outer is not None else pygame.Rect(point[0], point[1], 1, 1)


def shadow_center(center: tuple[float, float], square: int) -> tuple[float, float]:
    return center[0], center[1] + square * PIECE_SHADOW_OFFSET


def present(image: pygame.Surface, scale: float, tilt: float) -> pygame.Surface:
    if abs(tilt) < 0.15 and abs(scale - 1.0) < 0.012:
        return image
    return pygame.transform.rotozoom(image, tilt, scale)


def _dress(image: pygame.Surface, ghost: bool) -> pygame.Surface:
    source = image.copy()
    width, height = source.get_size()
    mask = pygame.mask.from_surface(source, threshold=24)
    cover = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
    body = source.copy()
    _shade_base(body, cover, width, height, ghost)
    _add_highlight(body, cover, width, height, ghost)
    if not ghost:
        _add_speck(body, cover, width, height)
    pad = 1
    canvas = pygame.Surface((width + pad * 2, height + pad * 2), pygame.SRCALPHA)
    dark = mask.to_surface(setcolor=(36, 22, 14, 22 if ghost else 48), unsetcolor=(0, 0, 0, 0))
    light = mask.to_surface(setcolor=(255, 236, 210, 18 if ghost else 36), unsetcolor=(0, 0, 0, 0))
    canvas.blit(dark, (pad + 1, pad + 1))
    canvas.blit(light, (0, 0))
    canvas.blit(body, (pad, pad))
    return canvas


def _shade_base(body: pygame.Surface, cover: pygame.Surface, width: int, height: int, ghost: bool) -> None:
    shade = pygame.Surface((width, height), pygame.SRCALPHA)
    start = int(height * 0.62)
    span = max(1, height - start)
    peak = 30 if ghost else 78
    for y in range(start, height):
        fade = (y - start) / span
        alpha = int(peak * fade * fade)
        pygame.draw.line(shade, (32, 20, 12, alpha), (0, y), (width, y))
    shade.blit(cover, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    body.blit(shade, (0, 0))


def _add_highlight(body: pygame.Surface, cover: pygame.Surface, width: int, height: int, ghost: bool) -> None:
    gloss = pygame.Surface((width, height), pygame.SRCALPHA)
    rect = pygame.Rect(int(width * 0.22), int(height * 0.08), max(2, int(width * 0.34)), max(2, int(height * 0.16)))
    pygame.draw.ellipse(gloss, (255, 248, 236, 10 if ghost else 28), rect)
    gloss.blit(cover, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    body.blit(gloss, (0, 0))


def _add_speck(body: pygame.Surface, cover: pygame.Surface, width: int, height: int) -> None:
    speck = pygame.Surface((width, height), pygame.SRCALPHA)
    radius = max(1, width // 16)
    pygame.draw.circle(speck, (255, 250, 240, 26), (int(width * 0.36), int(height * 0.20)), radius)
    speck.blit(cover, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    body.blit(speck, (0, 0))


figurines = FigurineCache()
