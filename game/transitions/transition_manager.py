from dataclasses import dataclass

import pygame

from game.transitions.easing import ease_in_out_cubic


@dataclass(frozen=True)
class TransitionPlacement:
    out_x: int
    in_x: int
    out_alpha: int
    in_alpha: int
    out_scale: float
    in_scale: float


class TransitionManager:
    def __init__(self) -> None:
        self.kind = "slide_left"
        self.duration = 0.75
        self.elapsed = 0.0
        self._running = False

    @property
    def active(self) -> bool:
        return self._running

    def start(self, kind: str, duration: float) -> bool:
        if self._running:
            return False
        self.kind = kind
        self.duration = duration if duration > 0 else 0.01
        self.elapsed = 0.0
        self._running = True
        return True

    def update(self, dt: float) -> None:
        if not self._running:
            return
        self.elapsed += max(0.0, dt)
        if self.elapsed >= self.duration:
            self.elapsed = self.duration
            self._running = False

    def linear(self) -> float:
        if self.duration <= 0:
            return 1.0
        return max(0.0, min(1.0, self.elapsed / self.duration))

    def progress(self) -> float:
        return ease_in_out_cubic(self.linear())

    def placement(self, width: int) -> TransitionPlacement:
        progress = self.progress()
        if self.kind == "slide_right":
            return TransitionPlacement(int(width * progress), int(-width * (1.0 - progress)), 255, 255, 1.0, 1.0)
        if self.kind == "fade":
            return TransitionPlacement(0, 0, int(255 * (1.0 - progress)), int(255 * progress), 1.0, 1.0)
        if self.kind == "scale":
            return TransitionPlacement(0, 0, int(255 * (1.0 - progress)), 255, 1.0, 0.94 + 0.06 * progress)
        if self.kind == "slide_fade":
            return TransitionPlacement(
                int(-width * progress),
                int(width * (1.0 - progress)),
                int(255 * (1.0 - progress)),
                int(255 * progress),
                1.0,
                1.0,
            )
        return TransitionPlacement(int(-width * progress), int(width * (1.0 - progress)), 255, 255, 1.0, 1.0)

    def render(self, screen: pygame.Surface, outgoing: pygame.Surface | None, incoming: pygame.Surface | None) -> None:
        placed = self.placement(screen.get_width())
        _blit_layer(screen, outgoing, placed.out_x, placed.out_alpha, placed.out_scale)
        _blit_layer(screen, incoming, placed.in_x, placed.in_alpha, placed.in_scale)


def _blit_layer(screen: pygame.Surface, surface: pygame.Surface | None, x: int, alpha: int, scale: float) -> None:
    if surface is None or alpha <= 0:
        return
    image = surface
    y = 0
    if scale != 1.0:
        width = max(1, int(surface.get_width() * scale))
        height = max(1, int(surface.get_height() * scale))
        image = pygame.transform.smoothscale(surface, (width, height))
        x = (screen.get_width() - width) // 2
        y = (screen.get_height() - height) // 2
    if alpha < 255:
        image = image.copy()
        image.set_alpha(alpha)
    screen.blit(image, (x, y))
