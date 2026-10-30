import pygame

from game.relics.effects.castle_wall import protected_squares
from rendering.layout import Layout


def draw_relic_overlays(screen: pygame.Surface, game, layout: Layout, run=None) -> None:
    if game is None:
        return
    board = game.board
    if run is not None and run.relics.owns("castle_wall"):
        for col, row in protected_squares(board):
            rect = layout.square_rect(col, row)
            shield = pygame.Rect(0, 0, max(10, rect.w // 5), max(12, rect.h // 4))
            shield.midtop = (rect.centerx, rect.y + 4)
            pygame.draw.ellipse(screen, (186, 206, 220), shield)
            pygame.draw.ellipse(screen, (70, 110, 140), shield, width=2)
    if game.bonus_piece_id is not None:
        piece = board.piece_by_id(game.bonus_piece_id)
        if piece is not None and piece.col is not None and piece.row is not None:
            rect = layout.square_rect(piece.col, piece.row)
            pygame.draw.circle(screen, (196, 48, 42), (rect.centerx, rect.y + 8), max(4, rect.w // 10))
    for col, row, color in list(getattr(game, "relic_flashes", ())):
        rect = layout.square_rect(col, row)
        glow = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (*color, 90), glow.get_rect().inflate(-rect.w // 5, -rect.h // 5))
        screen.blit(glow, rect.topleft)
