from dataclasses import dataclass

import pygame

from config.settings import (
    BOARD_SIZE,
    CROWN_SOURCE,
    FRAME_CONTENT_H,
    FRAME_CONTENT_W,
    FRAME_CONTENT_X,
    FRAME_CONTENT_Y,
    FRAME_SOURCE,
    LAYOUT_BOTTOM_PAD,
    LAYOUT_FILE_LABEL_H,
    RELIC_BAR_PAD,
    RELIC_CARD_HEIGHT,
    WINDOW_HEIGHT,
)


@dataclass
class Layout:
    window: tuple[int, int]
    header: pygame.Rect
    status: pygame.Rect
    frame: pygame.Rect
    board: pygame.Rect
    square: int
    crown: pygame.Rect
    turn: pygame.Rect
    relics: pygame.Rect
    left: pygame.Rect
    center: pygame.Rect
    right: pygame.Rect
    reset: pygame.Rect
    start: pygame.Rect
    deploy: pygame.Rect
    menu: pygame.Rect
    options: pygame.Rect

    def square_rect(self, col: int, row: int) -> pygame.Rect:
        screen_row = BOARD_SIZE - row
        return pygame.Rect(
            self.board.x + col * self.square,
            self.board.y + screen_row * self.square,
            self.square,
            self.square,
        )


def _board_inside(frame: pygame.Rect) -> tuple[pygame.Rect, int]:
    content_x = frame.x + int(round(FRAME_CONTENT_X * frame.w / FRAME_SOURCE))
    content_y = frame.y + int(round(FRAME_CONTENT_Y * frame.h / FRAME_SOURCE))
    content_w = int(round(FRAME_CONTENT_W * frame.w / FRAME_SOURCE))
    content_h = int(round(FRAME_CONTENT_H * frame.h / FRAME_SOURCE))
    side = min(content_w, content_h)
    square = max(1, side // BOARD_SIZE)
    side = square * BOARD_SIZE
    board = pygame.Rect(0, 0, side, side)
    board.center = (content_x + content_w // 2, content_y + content_h // 2)
    return board, square


def _relic_band_height(window_h: int) -> int:
    scale = window_h / WINDOW_HEIGHT
    card_h = max(64, min(RELIC_CARD_HEIGHT, int(round(RELIC_CARD_HEIGHT * scale))))
    return card_h + RELIC_BAR_PAD


def _columns(window_w: int, window_h: int) -> tuple[pygame.Rect, pygame.Rect, pygame.Rect]:
    outer = 12
    side_w = max(168, int(round(window_w * 0.25)) - outer)
    side_w = min(side_w, max(168, int(window_w * 0.28)))
    left = pygame.Rect(outer, outer, side_w, max(1, window_h - outer * 2))
    right = pygame.Rect(window_w - outer - side_w, outer, side_w, left.h)
    gap = 10
    center = pygame.Rect(left.right + gap, outer, max(1, right.left - gap - (left.right + gap)), left.h)
    return left, center, right


def _menu_buttons(left: pygame.Rect) -> tuple[pygame.Rect, pygame.Rect]:
    height = 40
    gap = 8
    inset = 14
    options = pygame.Rect(left.x + inset, left.bottom - inset - height, max(1, left.w - inset * 2), height)
    menu = pygame.Rect(options.x, options.y - gap - height, options.w, height)
    return menu, options


def build_layout(window_w: int, window_h: int) -> Layout:
    window_w = max(1, int(window_w))
    window_h = max(1, int(window_h))
    left, center, right = _columns(window_w, window_h)
    menu, options = _menu_buttons(left)
    crown_h = min(72, max(36, int(center.h * 0.08)))
    crown_w = max(1, int(round(crown_h * CROWN_SOURCE[0] / CROWN_SOURCE[1])))
    relic_h = _relic_band_height(window_h)
    label_h = LAYOUT_FILE_LABEL_H
    action_h = 42
    rank_gutter = 28

    def place(relic_height: int, crown_height: int) -> pygame.Rect:
        top = crown_height + 6 + relic_height + 8
        bottom_reserve = label_h + 8 + action_h + 8
        avail_h = center.h - top - bottom_reserve
        avail_w = center.w - rank_gutter - 8
        side = max(1, min(avail_w, avail_h))
        frame = pygame.Rect(0, 0, side, side)
        inner_left = center.left + rank_gutter
        inner_w = max(1, center.right - 8 - inner_left)
        frame.x = inner_left + max(0, (inner_w - side) // 2)
        frame.y = center.top + top
        return frame

    frame = place(relic_h, crown_h)
    _board, square = _board_inside(frame)
    action_top = frame.bottom + label_h + 6
    if square < 40 or action_top + action_h > window_h - LAYOUT_BOTTOM_PAD:
        relic_h = max(78, relic_h - 20)
        crown_h = max(36, crown_h - 12)
        crown_w = max(1, int(round(crown_h * CROWN_SOURCE[0] / CROWN_SOURCE[1])))
        frame = place(relic_h, crown_h)
    board, square = _board_inside(frame)
    relics = pygame.Rect(frame.x, frame.y - 8 - relic_h, frame.w, relic_h)
    crown = pygame.Rect(0, 0, crown_w, crown_h)
    crown.centerx = min(max(frame.centerx, center.left + crown_w // 2), center.right - crown_w // 2)
    crown.bottom = max(crown_h + 4, relics.top - 2)
    start = pygame.Rect(0, 0, min(260, max(160, frame.w // 2)), action_h)
    start.midtop = (frame.centerx, frame.bottom + label_h + 6)
    reset = pygame.Rect(0, 0, 0, 0)
    deploy = start.copy()
    turn = pygame.Rect(frame.x, start.y, frame.w, action_h)
    header = pygame.Rect(frame.x, crown.y, frame.w, max(1, relics.y - crown.y))
    status = pygame.Rect(frame.x, relics.y, frame.w, max(1, relics.h))
    return Layout(
        (window_w, window_h),
        header,
        status,
        frame,
        board,
        square,
        crown,
        turn,
        relics,
        left,
        center,
        right,
        reset,
        start,
        deploy,
        menu,
        options,
    )


def square_at(layout: Layout, pos: tuple[int, int]) -> tuple[int, int] | None:
    x, y = pos
    for blocker in (layout.left, layout.right, layout.menu, layout.options, layout.start, layout.reset, layout.deploy):
        if blocker.collidepoint(x, y):
            return None
    if not layout.board.collidepoint(x, y):
        return None
    col = (x - layout.board.x) // layout.square
    screen_row = (y - layout.board.y) // layout.square
    if col < 0 or col >= BOARD_SIZE or screen_row < 0 or screen_row >= BOARD_SIZE:
        return None
    return int(col), BOARD_SIZE - int(screen_row)
