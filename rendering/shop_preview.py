import pygame

from config.settings import BOARD_SIZE, PIECE_SCALE
from ai.trait_assignment import coming_battle
from rendering.enemy_tags import HEADING
from rendering.hud_renderer import _blit_text, get_font
from rendering.piece_visual_effects import figurines


def draw_panel_preview(screen: pygame.Surface, assets, run, bounds: pygame.Rect) -> None:
    preview = coming_battle(run)
    if preview is None or bounds.w < BOARD_SIZE or bounds.h < BOARD_SIZE:
        return
    _trait, enemies = preview
    font = get_font(max(15, min(20, bounds.w // 12)), bold=True)
    label_h = font.get_height()
    gap = 8
    square = max(1, min(bounds.w, max(BOARD_SIZE, bounds.h - label_h - gap)) // BOARD_SIZE)
    side = square * BOARD_SIZE
    group_h = label_h + gap + side
    group_top = bounds.y + max(0, (bounds.h - group_h) // 2)
    _blit_text(screen, "Next battle", font, HEADING, center=(bounds.centerx, group_top + label_h // 2))
    board = pygame.Rect(0, 0, side, side)
    board.midtop = (bounds.centerx, group_top + label_h + gap)
    frame = board.inflate(8, 8)
    pygame.draw.rect(screen, (62, 36, 20), frame, border_radius=4)
    pygame.draw.rect(screen, (214, 170, 90), frame, width=1, border_radius=4)
    light = assets.scaled("light", (square, square)) if assets is not None and assets.has("light") else None
    dark = assets.scaled("dark", (square, square)) if assets is not None and assets.has("dark") else None
    for row in range(1, BOARD_SIZE + 1):
        for col in range(BOARD_SIZE):
            rect = pygame.Rect(
                board.x + col * square,
                board.y + (BOARD_SIZE - row) * square,
                square,
                square,
            )
            tile = light if (col + row) % 2 == 1 else dark
            if tile is not None:
                screen.blit(tile, rect.topleft)
            else:
                light_square = (col + row) % 2 == 1
                pygame.draw.rect(screen, (232, 210, 170) if light_square else (118, 76, 46), rect)
    box = max(1, int(square * PIECE_SCALE))
    for piece in sorted(enemies, key=lambda item: item.row, reverse=True):
        if piece.col is None or piece.row is None:
            continue
        image = figurines.image(assets, piece, box)
        square_rect = pygame.Rect(
            board.x + piece.col * square,
            board.y + (BOARD_SIZE - piece.row) * square,
            square,
            square,
        )
        screen.blit(image, image.get_rect(center=square_rect.center))
