import pygame

from config.settings import (
    CAPTURE_OUTLINE,
    CHECK_FILL,
    MOVE_DOT,
    MOVE_DOT_EDGE,
    PIECE_SCALE,
    PIECE_SHADOW_HEIGHT,
    PIECE_SHADOW_LIFT_SPREAD,
    PIECE_SHADOW_WIDTH,
    SELECT_FILL,
    SELECT_OUTLINE,
)
from game.game import Game
from game.piece import Piece
from rendering.asset_manager import AssetManager
from rendering.layout import Layout
from rendering.overlay_renderer import draw_crosshair, draw_explosive_marks, draw_lock
from rendering.piece_animation_controller import piece_motion
from rendering.piece_visual_effects import draw_contact_shadow, figurines, present, shadow_center


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
    lift: float = 0.0,
) -> None:
    if piece.trait == "wanted":
        draw_crosshair(screen, rect)
    draw_contact_shadow(screen, (rect.centerx, rect.centery + rect.h * 0.30), rect.w, min(1.0, lift / 12))
    blit_piece(screen, assets, piece, box, (rect.centerx, rect.centery - lift), 1.0, 0.0)
    if piece.trait == "explosive":
        draw_explosive_marks(screen, rect.move(0, -int(lift)))


def blit_piece(
    screen: pygame.Surface,
    assets: AssetManager,
    piece: Piece,
    box: int,
    center: tuple[float, float],
    scale: float,
    tilt: float,
) -> None:
    image = present(figurines.image(assets, piece, box), scale, tilt)
    screen.blit(image, image.get_rect(center=(int(center[0]), int(center[1]))))


def draw_pieces(
    screen: pygame.Surface,
    assets: AssetManager,
    game: Game,
    layout: Layout,
    skip_id: int | None = None,
) -> None:
    _MARKERS.ensure(layout.square)
    pieces = [piece for piece in game.board.pieces if piece.col is not None and piece.row is not None]
    selected = game.selected_piece()
    selected_id = None if selected is None or selected.id == skip_id else selected.id
    piece_motion.update(pieces, selected_id, layout.square)
    king = game.board.king(game.turns.current)
    if game.turns.in_check and king is not None and king.col is not None and _MARKERS.check is not None:
        screen.blit(_MARKERS.check, layout.square_rect(king.col, king.row))
    if selected is not None and selected.col is not None and selected.id != skip_id and _MARKERS.selected is not None:
        screen.blit(_MARKERS.selected, layout.square_rect(selected.col, selected.row))
    box = max(1, int(layout.square * PIECE_SCALE))
    ordered = sorted(pieces, key=lambda piece: piece.row, reverse=True)
    for piece in ordered:
        if piece.id == skip_id:
            continue
        center = _board_center(layout, piece)
        lift, _scale, _tilt, ratio = piece_motion.offset(piece.id)
        draw_contact_shadow(screen, shadow_center(center, layout.square), layout.square, ratio)
    for piece in ordered:
        if piece.trait == "wanted" and piece.id != skip_id:
            mark = pygame.Rect(0, 0, layout.square, layout.square)
            mark.center = _board_center(layout, piece)
            draw_crosshair(screen, mark)
    _draw_legal(screen, game, layout)
    held: Piece | None = None
    for piece in ordered:
        if piece.id == skip_id:
            continue
        if piece.id == selected_id:
            held = piece
            continue
        _draw_board_piece(screen, assets, piece, layout, box)
    border = max(2, layout.square // 16)
    if game.turns.in_check and king is not None and king.col is not None:
        pygame.draw.rect(screen, CAPTURE_OUTLINE, layout.square_rect(king.col, king.row), width=border)
    if selected is not None and selected.col is not None and selected.id != skip_id:
        pygame.draw.rect(screen, SELECT_OUTLINE, layout.square_rect(selected.col, selected.row), width=border)
    hover = game.hover
    if hover is not None and (selected is None or (selected.col, selected.row) != hover):
        pygame.draw.rect(screen, HOVER_OUTLINE, layout.square_rect(*hover), width=max(1, border - 1))
    if held is not None:
        _draw_board_piece(screen, assets, held, layout, box)
    for piece in ordered:
        if piece.id == skip_id or piece.col is None or piece.row is None:
            continue
        status = game.statuses.get(piece.id)
        if status is not None and status.status_id == "immobilized" and status.remaining_owner_turns > 0:
            draw_lock(screen, layout.square_rect(piece.col, piece.row))
    if piece_motion.debug:
        _draw_motion_debug(screen, ordered, layout, skip_id)


def _draw_board_piece(
    screen: pygame.Surface,
    assets: AssetManager,
    piece: Piece,
    layout: Layout,
    box: int,
) -> None:
    center = _board_center(layout, piece)
    lift, scale, tilt, _ratio = piece_motion.offset(piece.id)
    blit_piece(screen, assets, piece, box, (center[0], center[1] - lift), scale, tilt)
    if piece.trait == "explosive":
        mark = pygame.Rect(0, 0, layout.square, layout.square)
        mark.center = (int(center[0]), int(center[1] - lift))
        draw_explosive_marks(screen, mark)


def _board_center(layout: Layout, piece: Piece) -> tuple[float, float]:
    dest = layout.square_rect(piece.col, piece.row).center
    motion = piece_motion.motions.get(piece.id)
    if motion is None or motion.travel_from is None:
        return float(dest[0]), float(dest[1])
    start = layout.square_rect(*motion.travel_from).center
    blend = _smooth(min(1.0, motion.travel_t))
    return (
        start[0] + (dest[0] - start[0]) * blend,
        start[1] + (dest[1] - start[1]) * blend,
    )


def _smooth(amount: float) -> float:
    return amount * amount * (3 - 2 * amount)


def _draw_motion_debug(
    screen: pygame.Surface,
    pieces: list[Piece],
    layout: Layout,
    skip_id: int | None,
) -> None:
    color = (232, 196, 96)
    for piece in pieces:
        if piece.id == skip_id:
            continue
        center = _board_center(layout, piece)
        ground = shadow_center(center, layout.square)
        _lift, _scale, _tilt, ratio = piece_motion.offset(piece.id)
        spread = 1 + PIECE_SHADOW_LIFT_SPREAD * ratio
        width = max(4, int(layout.square * PIECE_SHADOW_WIDTH * spread * 1.55))
        height = max(3, int(layout.square * PIECE_SHADOW_HEIGHT * spread * 1.55))
        bounds = pygame.Rect(0, 0, width, height)
        bounds.center = (int(ground[0]), int(ground[1]))
        pygame.draw.ellipse(screen, color, bounds, 1)
        anchor = (int(center[0]), int(center[1]))
        pygame.draw.line(screen, color, (anchor[0] - 4, anchor[1]), (anchor[0] + 4, anchor[1]), 1)
        pygame.draw.line(screen, color, (anchor[0], anchor[1] - 4), (anchor[0], anchor[1] + 4), 1)


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
