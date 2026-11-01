import math
from dataclasses import dataclass

import pygame


CARD_ANIMATION = {
    "hover_lift": -10,
    "selected_lift": -24,
    "drag_lift": -35,
    "hover_scale": 1.06,
    "selected_scale": 1.08,
    "drag_scale": 1.10,
    "max_drag_rotation": 6.0,
    "drag_threshold": 6.0,
    "animation_speed": 12.0,
    "drag_speed": 64.0,
}


@dataclass
class Motion:
    centerx: float
    bottom: float
    scale: float
    angle: float


def approach(current: float, target: float, dt: float, speed: float) -> float:
    if dt <= 0:
        return current
    delta = target - current
    if abs(delta) <= 0.2:
        return target
    blend = 1.0 - math.exp(-speed * max(0.0, dt))
    return current + delta * blend


def step_motion(current: Motion | None, target: Motion, dt: float, move_speed: float) -> Motion:
    if current is None:
        return Motion(target.centerx, target.bottom, target.scale, target.angle)
    if dt <= 0:
        return Motion(current.centerx, current.bottom, current.scale, current.angle)
    turn = CARD_ANIMATION["animation_speed"]
    return Motion(
        approach(current.centerx, target.centerx, dt, move_speed),
        approach(current.bottom, target.bottom, dt, move_speed),
        approach(current.scale, target.scale, dt, turn),
        approach(current.angle, target.angle, dt, turn),
    )


def past_drag_threshold(start: tuple[int, int] | None, pos: tuple[int, int]) -> bool:
    if start is None:
        return False
    dx = pos[0] - start[0]
    dy = pos[1] - start[1]
    limit = CARD_ANIMATION["drag_threshold"]
    return dx * dx + dy * dy >= limit * limit


def preview_order(ids: list[str], drag_id: str, mouse_x: float, centers: list[float]) -> list[str]:
    if drag_id not in ids:
        return list(ids)
    others = [item for item in ids if item != drag_id]
    insert = 0
    for center in centers:
        if mouse_x > center:
            insert += 1
    insert = max(0, min(insert, len(others)))
    return others[:insert] + [drag_id] + others[insert:]


def card_rect(centerx: float, bottom: float, width: float, height: float) -> pygame.Rect:
    rect = pygame.Rect(0, 0, max(1, int(round(width))), max(1, int(round(height))))
    rect.midbottom = (int(round(centerx)), int(round(bottom)))
    return rect


def clamp_rect(rect: pygame.Rect, window: tuple[int, int], margin: int = 6) -> pygame.Rect:
    bounds = pygame.Rect(margin, margin, max(1, window[0] - margin * 2), max(1, window[1] - margin * 2))
    placed = rect.copy()
    if placed.w > bounds.w:
        placed.w = bounds.w
    if placed.h > bounds.h:
        placed.h = bounds.h
    placed.clamp_ip(bounds)
    return placed


def placed_rect(motion: Motion, rest: pygame.Rect, window: tuple[int, int]) -> pygame.Rect:
    rect = card_rect(motion.centerx, motion.bottom, rest.w * motion.scale, rest.h * motion.scale)
    return clamp_rect(rect, window)


def anchored(motion: Motion, rest: pygame.Rect, window: tuple[int, int]) -> Motion:
    rect = placed_rect(motion, rest, window)
    return Motion(rect.centerx, rect.bottom, motion.scale, motion.angle)


def drag_angle(velocity_x: float) -> float:
    limit = CARD_ANIMATION["max_drag_rotation"]
    return max(-limit, min(limit, -velocity_x * 0.45))
