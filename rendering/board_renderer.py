import pygame

from rendering.asset_manager import AssetManager
from rendering.layout import Layout


def draw_board(screen: pygame.Surface, assets: AssetManager, layout: Layout) -> None:
    light = assets.scaled("light", (layout.square, layout.square))
    dark = assets.scaled("dark", (layout.square, layout.square))
    for row in range(1, 7):
        for col in range(6):
            texture = light if (col + row) % 2 == 1 else dark
            screen.blit(texture, layout.square_rect(col, row))
    frame = assets.scaled("frame", (layout.frame.w, layout.frame.h))
    screen.blit(frame, layout.frame.topleft)
