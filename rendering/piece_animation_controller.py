import math

import pygame

from config.settings import (
    PIECE_BOB_AMPLITUDE,
    PIECE_BOB_SPEED,
    PIECE_EASE_RATE,
    PIECE_IDLE_BOB,
    PIECE_LIFT_MAX,
    PIECE_LIFT_MIN,
    PIECE_LIFT_RATIO,
    PIECE_SELECT_SCALE,
    PIECE_TILT,
    PIECE_TRAVEL_TIME,
)
from game.piece import Piece


class PieceMotion:
    def __init__(self) -> None:
        self.height = 0.0
        self.scale = 1.0
        self.tilt = 0.0
        self.phase = 0.0
        self.anchor: tuple[int, int] | None = None
        self.travel_from: tuple[int, int] | None = None
        self.travel_t = 1.0


class PieceAnimationController:
    def __init__(self) -> None:
        self.motions: dict[int, PieceMotion] = {}
        self.debug = False
        self.lift_pixels = 0.0
        self._last_ms: int | None = None
        self._selected: int | None = None

    def clear(self) -> None:
        self.motions.clear()
        self._last_ms = None
        self._selected = None
        self.lift_pixels = 0.0

    def toggle_debug(self) -> None:
        self.debug = not self.debug

    def update(
        self,
        pieces: list[Piece],
        selected_id: int | None,
        square: int,
        now_ms: int | None = None,
    ) -> None:
        now = pygame.time.get_ticks() if now_ms is None else now_ms
        if self._last_ms is None:
            dt = 0.0
        else:
            dt = min(0.05, max(0.0, (now - self._last_ms) / 1000))
        self._last_ms = now
        self.lift_pixels = _lift_pixels(square)
        alive = {piece.id for piece in pieces if piece.col is not None and piece.row is not None}
        for gone in list(self.motions):
            if gone not in alive:
                self.motions.pop(gone, None)
        changed: list[int] = []
        for piece in pieces:
            if piece.col is None or piece.row is None:
                continue
            motion = self.motions.get(piece.id)
            square_key = (piece.col, piece.row)
            if motion is None:
                motion = PieceMotion()
                motion.anchor = square_key
                self.motions[piece.id] = motion
                continue
            if motion.anchor != square_key:
                changed.append(piece.id)
        if len(changed) == 1:
            piece_id = changed[0]
            motion = self.motions[piece_id]
            piece = next(item for item in pieces if item.id == piece_id)
            lifted = motion.height > 1.0 or self._selected == piece_id
            if lifted and motion.anchor is not None:
                motion.travel_from = motion.anchor
                motion.travel_t = 0.0
            else:
                motion.travel_from = None
                motion.travel_t = 1.0
            motion.anchor = (piece.col, piece.row)
        else:
            for piece_id in changed:
                motion = self.motions[piece_id]
                piece = next(item for item in pieces if item.id == piece_id)
                motion.anchor = (piece.col, piece.row)
                motion.travel_from = None
                motion.travel_t = 1.0
        self._selected = selected_id
        for piece in pieces:
            if piece.col is None or piece.row is None:
                continue
            motion = self.motions[piece.id]
            selected = piece.id == selected_id
            target_height = self.lift_pixels if selected else 0.0
            target_scale = PIECE_SELECT_SCALE if selected else 1.0
            target_tilt = PIECE_TILT if selected else 0.0
            motion.height = _approach(motion.height, target_height, PIECE_EASE_RATE, dt)
            motion.scale = _approach(motion.scale, target_scale, PIECE_EASE_RATE, dt)
            motion.tilt = _approach(motion.tilt, target_tilt, PIECE_EASE_RATE, dt)
            if motion.travel_from is not None:
                motion.travel_t = min(1.0, motion.travel_t + dt / max(0.01, PIECE_TRAVEL_TIME))
                if motion.travel_t >= 1.0:
                    motion.travel_from = None
            moving = selected or motion.height > 0.4 or motion.travel_from is not None or PIECE_IDLE_BOB > 0
            if moving:
                motion.phase += PIECE_BOB_SPEED * dt

    def offset(self, piece_id: int) -> tuple[float, float, float, float]:
        motion = self.motions.get(piece_id)
        if motion is None:
            return 0.0, 1.0, 0.0, 0.0
        bob = 0.0
        if motion.height > 0.4 and self.lift_pixels > 0:
            bob = math.sin(motion.phase) * PIECE_BOB_AMPLITUDE * min(1.0, motion.height / self.lift_pixels)
        elif PIECE_IDLE_BOB > 0:
            bob = math.sin(motion.phase) * PIECE_IDLE_BOB
        tilt = motion.tilt
        if abs(motion.tilt) > 0.2:
            tilt += math.sin(motion.phase * 0.7) * 0.8
        if self.lift_pixels <= 0:
            ratio = 0.0
        else:
            ratio = min(1.0, max(0.0, motion.height) / self.lift_pixels)
        return motion.height + bob, motion.scale, tilt, ratio


def _lift_pixels(square: int) -> float:
    raw = square * PIECE_LIFT_RATIO
    low = min(float(PIECE_LIFT_MIN), square * 0.2)
    return max(low, min(float(PIECE_LIFT_MAX), raw))


def _approach(current: float, target: float, rate: float, dt: float) -> float:
    if dt <= 0:
        return current
    return current + (target - current) * (1 - math.exp(-rate * dt))


piece_motion = PieceAnimationController()
