import pygame

from config.settings import (
    CAPTURE_OUTLINE,
    CHECK_FILL,
    MOVE_DOT,
    MOVE_DOT_EDGE,
    PIECE_SCALE,
    SELECT_FILL,
    SELECT_OUTLINE,
)
from game.game import Game
from game.piece import Piece
from rendering.asset_manager import AssetManager
from rendering.layout import Layout
from rendering.overlay_renderer import draw_crosshair, draw_explosive_marks, draw_lock
from rendering.special_piece_renderer import special_pieces


class _MarkerCache:
    def __init__(self) -> None:
        self.square = 0
        self.selected: pygame.Surface | None = None
        self.check: pygame.Surface | None = None

    def ensure(self, square: int) -> None:
        if self.square == square and self.selected is not None and self.check is not None:
            return
        self.square = square
        selected = pygame.Surface((square, square), pygame.SRCALPHA)
        selected.fill(SELECT_FILL)
        check = pygame.Surface((square, square), pygame.SRCALPHA)
        check.fill(CHECK_FILL)
        self.selected = selected
        self.check = check


_MARKERS = _MarkerCache()
HOVER_OUTLINE = (232, 206, 150)


def draw_trait_sprite(
    screen: pygame.Surface,
    assets: AssetManager,
    piece: Piece,
    rect: pygame.Rect,
    box: int,
) -> None:
    if piece.trait == "wanted":
        draw_crosshair(screen, rect)
    image = special_pieces.image(assets, piece.color, piece.kind, piece.trait, box)
    screen.blit(image, image.get_rect(center=rect.center))
    if piece.trait == "explosive":
        draw_explosive_marks(screen, rect)


def draw_pieces(screen: pygame.Surface, assets: AssetManager, game: Game, layout: Layout) -> None:
    _MARKERS.ensure(layout.square)
    king = game.board.king(game.turns.current)
    if game.turns.in_check and king is not None and _MARKERS.check is not None:
        screen.blit(_MARKERS.check, layout.square_rect(king.col, king.row))
    selected = game.selected_piece()
    if selected is not None and _MARKERS.selected is not None:
        screen.blit(_MARKERS.selected, layout.square_rect(selected.col, selected.row))
    _draw_legal(screen, game, layout)
    box = max(1, int(layout.square * PIECE_SCALE))
    pieces = sorted(game.board.pieces, key=lambda piece: piece.row, reverse=True)
    for piece in pieces:
        square = layout.square_rect(piece.col, piece.row)
        draw_trait_sprite(screen, assets, piece, square, box)
        status = game.statuses.get(piece.id)
        if status is not None and status.status_id == "immobilized" and status.remaining_owner_turns > 0:
            draw_lock(screen, square)
    border = max(2, layout.square // 16)
    if game.turns.in_check and king is not None:
        pygame.draw.rect(screen, CAPTURE_OUTLINE, layout.square_rect(king.col, king.row), width=border)
    if selected is not None:
        pygame.draw.rect(screen, SELECT_OUTLINE, layout.square_rect(selected.col, selected.row), width=border)
    hover = game.hover
    if hover is not None and (selected is None or (selected.col, selected.row) != hover):
        pygame.draw.rect(screen, HOVER_OUTLINE, layout.square_rect(*hover), width=max(1, border - 1))


def _draw_legal(screen: pygame.Surface, game: Game, layout: Layout) -> None:
    radius = max(5, layout.square // 9)
    outline = max(2, layout.square // 18)
    for move in game.legal:
        rect = layout.square_rect(move.to_col, move.to_row)
        occupant = game.board.piece_at(move.to_col, move.to_row)
        if occupant is None:
            center = rect.center
            pygame.draw.circle(screen, MOVE_DOT_EDGE, center, radius)
            pygame.draw.circle(screen, MOVE_DOT, center, max(2, radius - 2))
        else:
            pygame.draw.rect(screen, CAPTURE_OUTLINE, rect, width=outline, border_radius=4)
