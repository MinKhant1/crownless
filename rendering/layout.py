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
    HEADER_SOURCE,
    LAYOUT_BOTTOM_PAD,
    LAYOUT_CROWN_HEIGHT,
    LAYOUT_FILE_LABEL_H,
    LAYOUT_FRAME_WIDTH,
    LAYOUT_HEADER_STATUS_GAP,
    LAYOUT_HEADER_WIDTH,
    LAYOUT_RANK_GUTTER,
    LAYOUT_SIDE_PAD,
    LAYOUT_STATUS_FRAME_GAP,
    LAYOUT_TOP_PAD,
    LAYOUT_TURN_H,
    STATUS_SOURCE,
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


def layout_for_status_width(window_w: int, window_h: int, status_w: int) -> Layout:
    status_h = max(1, int(round(status_w * STATUS_SOURCE[1] / STATUS_SOURCE[0])))
    header_w = max(1, int(round(status_w * LAYOUT_HEADER_WIDTH)))
    header_h = max(1, int(round(header_w * HEADER_SOURCE[1] / HEADER_SOURCE[0])))
    frame_size = max(1, int(round(status_w * LAYOUT_FRAME_WIDTH)))
    crown_h = max(1, int(round(header_h * LAYOUT_CROWN_HEIGHT)))
    crown_w = max(1, int(round(crown_h * CROWN_SOURCE[0] / CROWN_SOURCE[1])))
    block_w = max(status_w, header_w, frame_size, crown_w)
    origin_x = max(LAYOUT_RANK_GUTTER, (window_w - block_w) // 2)
    header_y = LAYOUT_TOP_PAD + max(0, crown_h - header_h)
    header = pygame.Rect(origin_x + (block_w - header_w) // 2, header_y, header_w, header_h)
    status = pygame.Rect(
        origin_x + (block_w - status_w) // 2,
        header.bottom + LAYOUT_HEADER_STATUS_GAP,
        status_w,
        status_h,
    )
    frame = pygame.Rect(
        origin_x + (block_w - frame_size) // 2,
        status.bottom + LAYOUT_STATUS_FRAME_GAP,
        frame_size,
        frame_size,
    )
    crown = pygame.Rect(0, 0, crown_w, crown_h)
    crown.midbottom = (header.centerx, header.bottom)
    board, square = _board_inside(frame)
    turn = pygame.Rect(0, frame.bottom + LAYOUT_FILE_LABEL_H, window_w, LAYOUT_TURN_H)
    return Layout((window_w, window_h), header, status, frame, board, square, crown, turn)


def layout_fits(layout: Layout, window_w: int, window_h: int) -> bool:
    if layout.crown.top < 4:
        return False
    if layout.crown.left < 4 or layout.crown.right > window_w - 4:
        return False
    if layout.frame.left < LAYOUT_RANK_GUTTER or layout.frame.right > window_w - LAYOUT_SIDE_PAD:
        return False
    if layout.turn.bottom > window_h - LAYOUT_BOTTOM_PAD:
        return False
    if layout.square < 8:
        return False
    return True


def build_layout(window_w: int, window_h: int) -> Layout:
    low = 240
    high = max(240, window_w)
    best = low
    while low <= high:
        mid = (low + high) // 2
        candidate = layout_for_status_width(window_w, window_h, mid)
        if layout_fits(candidate, window_w, window_h):
            best = mid
            low = mid + 1
        else:
            high = mid - 1
    return layout_for_status_width(window_w, window_h, best)


def square_at(layout: Layout, pos: tuple[int, int]) -> tuple[int, int] | None:
    x, y = pos
    if not layout.board.collidepoint(x, y):
        return None
    col = (x - layout.board.x) // layout.square
    screen_row = (y - layout.board.y) // layout.square
    if col < 0 or col >= BOARD_SIZE or screen_row < 0 or screen_row >= BOARD_SIZE:
        return None
    return int(col), BOARD_SIZE - int(screen_row)
