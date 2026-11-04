import pygame

from config.settings import (
    BOARD_HIGHLIGHT,
    BOARD_INLAY,
    BOARD_INLAY_LIGHT,
    BOARD_RECESS,
    BOARD_SHADE,
    BOARD_SHADOW_ALPHA,
    BOARD_SHADOW_OFFSET_X,
    BOARD_SHADOW_OFFSET_Y,
    BOARD_THICKNESS,
    FRAME_CONTENT_H,
    FRAME_CONTENT_W,
    FRAME_CONTENT_X,
    FRAME_CONTENT_Y,
    FRAME_SOURCE,
)
from rendering.asset_manager import AssetManager
from rendering.layout import Layout

_SHADOW_PAD_X = 44
_SHADOW_PAD_Y = 36


class _BoardCache:
    def __init__(self) -> None:
        self.square = 0
        self.light: pygame.Surface | None = None
        self.dark: pygame.Surface | None = None
        self.inlay_surface: pygame.Surface | None = None
        self.frame: tuple[int, int] | None = None
        self.shadow: pygame.Surface | None = None
        self.rim: pygame.Surface | None = None
        self.recess_side = 0
        self.recess_surface: pygame.Surface | None = None

    def clear(self) -> None:
        self.square = 0
        self.light = None
        self.dark = None
        self.inlay_surface = None
        self.frame = None
        self.shadow = None
        self.rim = None
        self.recess_side = 0
        self.recess_surface = None

    def tiles(self, assets: AssetManager, square: int) -> tuple[pygame.Surface, pygame.Surface]:
        if self.square != square or self.light is None or self.dark is None:
            self.square = square
            self.light = assets.scaled("light", (square, square))
            self.dark = assets.scaled("dark", (square, square))
            self.inlay_surface = _inlay(square)
        return self.light, self.dark

    def drop_shadow(self, frame: pygame.Rect) -> pygame.Surface:
        key = (frame.w, frame.h)
        if self.frame != key or self.shadow is None:
            self.frame = key
            self.shadow = _drop_shadow(frame.w, frame.h)
            self.rim = _frame_rim(frame.w, frame.h)
        assert self.shadow is not None
        return self.shadow

    def frame_rim(self, frame: pygame.Rect) -> pygame.Surface:
        self.drop_shadow(frame)
        assert self.rim is not None
        return self.rim

    def recess(self, side: int) -> pygame.Surface:
        if self.recess_side != side or self.recess_surface is None:
            self.recess_side = side
            self.recess_surface = _recess(side)
        return self.recess_surface


def draw_board(screen: pygame.Surface, assets: AssetManager, layout: Layout) -> None:
    frame = layout.frame
    shadow = _CACHE.drop_shadow(frame)
    screen.blit(shadow, (frame.x - _SHADOW_PAD_X, frame.y - _SHADOW_PAD_Y))
    _draw_thickness(screen, frame)
    light, dark = _CACHE.tiles(assets, layout.square)
    for row in range(1, 7):
        for col in range(6):
            texture = light if (col + row) % 2 == 1 else dark
            screen.blit(texture, layout.square_rect(col, row))
    # one wooden board: thin inlay lines between squares and a single soft light, not 36 glossy tiles
    screen.blit(_CACHE.inlay_surface, layout.board.topleft)
    screen.blit(assets.scaled("frame", (frame.w, frame.h)), frame.topleft)
    screen.blit(_CACHE.frame_rim(frame), frame.topleft)
    screen.blit(_CACHE.recess(layout.board.w), layout.board.topleft)


def clear_board_cache() -> None:
    _CACHE.clear()


def _inlay(square: int) -> pygame.Surface:
    side = square * 6
    surface = pygame.Surface((side, side), pygame.SRCALPHA)
    light = pygame.Surface((48, 48), pygame.SRCALPHA)
    for step in range(24, 0, -1):
        fade = (1 - step / 24) ** 1.5
        pygame.draw.circle(light, (255, 236, 200, int(BOARD_INLAY_LIGHT * fade)), (16, 14), step + 8)
    surface.blit(pygame.transform.smoothscale(light, (side, side)), (0, 0))
    for index in range(1, 6):
        offset = index * square
        pygame.draw.line(surface, (*BOARD_INLAY, 210), (offset - 1, 0), (offset - 1, side - 1))
        pygame.draw.line(surface, (255, 230, 190, 40), (offset, 0), (offset, side - 1))
        pygame.draw.line(surface, (*BOARD_INLAY, 210), (0, offset - 1), (side - 1, offset - 1))
        pygame.draw.line(surface, (255, 230, 190, 40), (0, offset), (side - 1, offset))
    return surface


def _drop_shadow(width: int, height: int) -> pygame.Surface:
    surface = pygame.Surface((width + _SHADOW_PAD_X * 2, height + _SHADOW_PAD_Y * 2), pygame.SRCALPHA)
    pool = pygame.Rect(
        _SHADOW_PAD_X + BOARD_SHADOW_OFFSET_X + width // 14,
        _SHADOW_PAD_Y + height + BOARD_SHADOW_OFFSET_Y - 16,
        int(width * 0.82),
        30,
    )
    for step in range(8):
        spread = (7 - step) * 8
        fade = ((step + 1) / 8) ** 1.35
        alpha = max(1, int(BOARD_SHADOW_ALPHA * fade))
        pygame.draw.ellipse(surface, (5, 3, 2, alpha), pool.inflate(spread * 2, spread))
    side = pygame.Rect(
        _SHADOW_PAD_X + width + BOARD_SHADOW_OFFSET_X - 16,
        _SHADOW_PAD_Y + height // 4,
        26,
        int(height * 0.62),
    )
    for step in range(5):
        fade = ((step + 1) / 5) ** 1.4
        alpha = max(1, int(BOARD_SHADOW_ALPHA * fade * 0.42))
        pygame.draw.ellipse(surface, (5, 3, 2, alpha), side.inflate((4 - step) * 10, (4 - step) * 8))
    return surface


def _frame_rim(width: int, height: int) -> pygame.Surface:
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    band = max(5, width // 42)
    for step in range(band):
        fade = (1 - step / band) ** 1.15
        light = max(1, int(BOARD_HIGHLIGHT * fade))
        dark = max(1, int(BOARD_SHADE * fade))
        pygame.draw.line(surface, (255, 238, 210, light), (step, step), (width - 1 - step, step))
        pygame.draw.line(surface, (255, 236, 206, int(light * 0.75)), (step, step), (step, height - 1 - step))
        pygame.draw.line(surface, (24, 12, 6, dark), (step, height - 1 - step), (width - 1 - step, height - 1 - step))
        pygame.draw.line(surface, (18, 8, 4, int(dark * 0.88)), (width - 1 - step, step), (width - 1 - step, height - 1 - step))
    opening = _opening(width, height)
    pygame.draw.line(surface, (255, 244, 214, BOARD_HIGHLIGHT), opening.topleft, opening.topright, 2)
    pygame.draw.line(surface, (255, 244, 214, int(BOARD_HIGHLIGHT * 0.7)), opening.topleft, opening.bottomleft, 2)
    pygame.draw.line(surface, (20, 10, 6, BOARD_SHADE), (opening.left, opening.bottom - 1), (opening.right, opening.bottom - 1), 3)
    pygame.draw.line(surface, (16, 8, 4, int(BOARD_SHADE * 0.85)), (opening.right - 1, opening.top), (opening.right - 1, opening.bottom), 2)
    return surface


def _recess(side: int) -> pygame.Surface:
    surface = pygame.Surface((side, side), pygame.SRCALPHA)
    depth = max(10, side // 18)
    for step in range(depth):
        fade = (1 - step / depth) ** 1.25
        light = max(1, int(BOARD_RECESS * fade * 0.42))
        dark = max(1, int(BOARD_RECESS * fade * 0.72))
        pygame.draw.line(surface, (255, 246, 224, light), (step, step), (side - 1 - step, step))
        pygame.draw.line(surface, (255, 244, 220, int(light * 0.8)), (step, step), (step, side - 1 - step))
        pygame.draw.line(surface, (18, 8, 4, dark), (step, side - 1 - step), (side - 1 - step, side - 1 - step))
        pygame.draw.line(surface, (12, 6, 3, int(dark * 0.9)), (side - 1 - step, step), (side - 1 - step, side - 1 - step))
    return surface


def _draw_thickness(screen: pygame.Surface, frame: pygame.Rect) -> None:
    depth = max(4, BOARD_THICKNESS)
    bottom = pygame.Rect(frame.x + 8, frame.bottom - 3, frame.w - 14, depth + 3)
    right = pygame.Rect(frame.right - 3, frame.y + 10, max(4, int(depth * 0.72)), frame.h - 8)
    pygame.draw.rect(screen, (92, 52, 28), bottom, border_radius=3)
    pygame.draw.rect(screen, (74, 40, 22), right, border_radius=2)
    pygame.draw.line(screen, (128, 82, 48), (bottom.x + 6, bottom.y + 1), (bottom.right - 6, bottom.y + 1))
    pygame.draw.line(screen, (42, 22, 12), (bottom.x + 6, bottom.bottom - 2), (bottom.right - 8, bottom.bottom - 2))
    pygame.draw.line(screen, (110, 68, 38), (right.x + 1, right.y + 4), (right.x + 1, right.bottom - 6))


def _opening(width: int, height: int) -> pygame.Rect:
    return pygame.Rect(
        int(round(FRAME_CONTENT_X * width / FRAME_SOURCE)),
        int(round(FRAME_CONTENT_Y * height / FRAME_SOURCE)),
        int(round(FRAME_CONTENT_W * width / FRAME_SOURCE)),
        int(round(FRAME_CONTENT_H * height / FRAME_SOURCE)),
    )


_CACHE = _BoardCache()
