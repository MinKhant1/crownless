"""Board light effects: landing dust, capture sparks, explosions, relic light and special-piece auras.

Particles live in screen pixels; anything queued with a delay (so it lands with the piece's travel animation)
waits in `pending`. The main loop calls update(dt); render_battle calls draw() so banners stay on top.
"""

import math
import random

import pygame

TRAIT_COLORS = {
    "golden": (255, 196, 70),
    "ghost": (150, 190, 255),
    "explosive": (255, 104, 36),
    "wanted": (230, 60, 52),
    "wooden": (190, 130, 70),
    "magnet": (110, 140, 255),
}

_GLOW: dict[tuple, pygame.Surface] = {}


def glow_sprite(radius: int, color: tuple[int, int, int], level: int) -> pygame.Surface:
    radius = max(4, int(radius) // 4 * 4)
    key = (radius, color, level)
    cached = _GLOW.get(key)
    if cached is None:
        cached = pygame.Surface((radius * 2, radius * 2))
        cached.fill((0, 0, 0))
        strength = level / 8.0
        for r in range(radius, 0, -2):
            k = ((1.0 - r / radius) ** 2.0) * strength
            pygame.draw.circle(cached, tuple(min(255, int(c * k)) for c in color), (radius, radius), r)
        _GLOW[key] = cached
    return cached


def add_glow(surface: pygame.Surface, center, radius: float, color, intensity: float) -> None:
    level = max(0, min(8, int(round(intensity * 8))))
    if level <= 0 or radius < 2:
        return
    sprite = glow_sprite(int(radius), tuple(color), level)
    surface.blit(sprite, sprite.get_rect(center=(int(center[0]), int(center[1]))), special_flags=pygame.BLEND_RGB_ADD)


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "age", "size", "color", "drag", "gravity", "kind")

    def __init__(self, x, y, vx, vy, life, size, color, drag=0.0, gravity=0.0, kind="spark") -> None:
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life, self.age, self.size, self.color = life, 0.0, size, color
        self.drag, self.gravity, self.kind = drag, gravity, kind


class BoardEffects:
    def __init__(self) -> None:
        self.rng = random.Random()
        self.particles: list[Particle] = []
        self.glows: list[list] = []  # x, y, radius, color, life, age, grow
        self.rings: list[list] = []  # x, y, radius, color, life, age
        self.pending: list[list] = []  # delay, callable
        self.time = 0.0
        self.auras = True

    def clear(self) -> None:
        self.particles.clear()
        self.glows.clear()
        self.rings.clear()
        self.pending.clear()

    def busy(self) -> bool:
        return bool(self.particles or self.glows or self.rings or self.pending)

    def later(self, delay: float, action) -> None:
        if delay <= 0:
            action()
        else:
            self.pending.append([delay, action])

    # ------------------------------------------------------------------ primitives
    def glow(self, pos, radius, color, life=0.8, grow=0.0) -> None:
        self.glows.append([pos[0], pos[1], radius, color, life, 0.0, grow])

    def ring(self, pos, radius, color, life=0.6) -> None:
        self.rings.append([pos[0], pos[1], radius, color, life, 0.0])

    def burst(self, pos, color, count=20, speed=240.0, life=0.6, size=3.0, gravity=0.0, drag=2.5, kind="spark") -> None:
        for _ in range(count):
            angle = self.rng.uniform(0, math.tau)
            v = speed * self.rng.uniform(0.25, 1.0)
            self.particles.append(
                Particle(pos[0], pos[1], math.cos(angle) * v, math.sin(angle) * v, life * self.rng.uniform(0.6, 1.2),
                         size * self.rng.uniform(0.6, 1.3), color, drag, gravity, kind)
            )

    def rise(self, pos, color, spread=30.0, speed=60.0, life=1.4, size=2.5, kind="mote") -> None:
        self.particles.append(
            Particle(pos[0] + self.rng.uniform(-spread, spread), pos[1] + self.rng.uniform(-spread * 0.3, spread * 0.3),
                     self.rng.uniform(-12, 12), -speed * self.rng.uniform(0.5, 1.2), life * self.rng.uniform(0.7, 1.3),
                     size * self.rng.uniform(0.6, 1.4), color, 0.4, 0.0, kind)
        )

    # ------------------------------------------------------------------ moments
    def landing(self, pos, square: int, color: str) -> None:
        tint = (255, 222, 160) if color == "white" else (170, 120, 150)
        foot = (pos[0], pos[1] + square * 0.28)
        self.ring(foot, square * 0.42, tint, life=0.35)
        self.burst(foot, (110, 86, 64), count=8, speed=90, life=0.45, size=4, drag=4.0, kind="dust")

    def capture(self, pos, square: int, attacker: str) -> None:
        color = (255, 214, 140) if attacker == "white" else (210, 70, 90)
        self.glow(pos, square * 0.95, color, life=0.45)
        self.ring(pos, square * 0.75, color, life=0.45)
        self.burst(pos, color, count=22, speed=square * 2.6, life=0.55, size=3.0)
        self.burst(pos, (90, 70, 56), count=10, speed=square, life=0.8, size=5, drag=3.0, kind="dust")

    def explosion(self, pos, square: int) -> None:
        self.glow(pos, square * 2.6, (255, 140, 50), life=0.9, grow=0.4)
        self.glow(pos, square * 1.3, (255, 236, 190), life=0.35)
        self.ring(pos, square * 2.1, (255, 150, 60), life=0.7)
        self.ring(pos, square * 1.35, (255, 220, 150), life=0.45)
        self.burst(pos, (255, 160, 60), count=60, speed=square * 5.0, life=0.9, size=3.6, gravity=square * 2)
        self.burst(pos, (255, 230, 170), count=24, speed=square * 3.4, life=0.5, size=2.8)
        self.burst(pos, (60, 40, 30), count=20, speed=square * 1.3, life=1.5, size=10, drag=2.0, kind="smoke")

    def holy(self, pos, square: int, color, big: bool = False) -> None:
        self.glow(pos, square * (2.0 if big else 1.2), color, life=1.3 if big else 0.95, grow=0.25)
        self.ring(pos, square * (1.6 if big else 1.0), color, life=0.85)
        for _ in range(34 if big else 16):
            self.rise(pos, color, spread=square * (0.5 if big else 0.28), speed=square * (1.1 if big else 0.75), life=1.5, size=2.8, kind="spark")

    # ------------------------------------------------------------------ frame
    def update(self, dt: float) -> None:
        self.time += dt
        if self.pending:
            due = []
            for item in self.pending:
                item[0] -= dt
                if item[0] <= 0:
                    due.append(item)
            for item in due:
                self.pending.remove(item)
                item[1]()
        for p in self.particles:
            p.age += dt
            damp = math.exp(-p.drag * dt)
            p.vx *= damp
            p.vy = p.vy * damp + p.gravity * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
        self.particles = [p for p in self.particles if p.age < p.life]
        for g in self.glows:
            g[5] += dt
        self.glows = [g for g in self.glows if g[5] < g[4]]
        for r in self.rings:
            r[5] += dt
        self.rings = [r for r in self.rings if r[5] < r[4]]

    def draw_auras(self, screen: pygame.Surface, game, layout, dt: float = 1 / 60) -> None:
        """Soft trait-coloured light under special pieces and the motes each trait gives off."""
        if not self.auras or game is None:
            return
        square = layout.square
        rng = self.rng
        for piece in game.board.pieces:
            if not piece.trait or piece.col is None or piece.row is None:
                continue
            color = TRAIT_COLORS.get(piece.trait)
            if color is None:
                continue
            cx, cy = layout.square_rect(piece.col, piece.row).center
            pulse = 0.75 + 0.25 * math.sin(self.time * 3.0 + piece.id)
            add_glow(screen, (cx, cy + square * 0.18), square * 0.6, color, 0.32 * pulse)
            if rng.random() > dt * 5.0:
                continue
            if piece.trait == "golden":
                self.rise((cx, cy), (255, 214, 110), spread=square * 0.3, speed=square * 0.45, size=2.4, kind="spark")
            elif piece.trait == "ghost":
                self.rise((cx, cy + square * 0.1), (170, 205, 255), spread=square * 0.32, speed=square * 0.3, life=1.8, size=3.0)
            elif piece.trait == "explosive":
                self.rise((cx, cy - square * 0.25), (255, 120, 40), spread=square * 0.12, speed=square * 0.7, life=0.9, size=2.0)
            elif piece.trait == "wanted":
                if rng.random() < 0.3:
                    self.ring((cx, cy), square * 0.5, (200, 50, 46), life=0.9)
            elif piece.trait == "magnet":
                angle = rng.uniform(0, math.tau)
                self.particles.append(Particle(cx + math.cos(angle) * square * 0.45, cy + math.sin(angle) * square * 0.3,
                                               -math.cos(angle) * 40, -math.sin(angle) * 30, 0.9, 2.2, (140, 170, 255), 0.5))
            else:
                self.rise((cx, cy + square * 0.2), (200, 150, 90), spread=square * 0.3, speed=square * 0.18, life=1.5, size=2.0)

    def draw(self, screen: pygame.Surface) -> None:
        for p in self.particles:
            if p.kind in ("smoke", "dust"):
                k = 1.0 - p.age / p.life
                size = max(1, int(p.size * (1.0 + p.age * 1.5)))
                blob = pygame.Surface((size * 2 + 2, size * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(blob, (*p.color, int(110 * k)), (size + 1, size + 1), size)
                screen.blit(blob, (p.x - size, p.y - size))
        for x, y, radius, color, life, age, grow in self.glows:
            k = 1.0 - age / life
            add_glow(screen, (x, y), radius * (1.0 + grow * age / life), color, k * k)
        for x, y, radius, color, life, age in self.rings:
            k = age / life
            r = int(radius * _ease(k) + 6)
            fade = (1.0 - k) ** 1.5
            layer = pygame.Surface((r * 2 + 4, r * 2 + 4))
            layer.fill((0, 0, 0))
            pygame.draw.circle(layer, tuple(int(c * fade) for c in color), (r + 2, r + 2), r, width=max(2, int(8 * (1 - k))))
            screen.blit(layer, (int(x) - r - 2, int(y) - r - 2), special_flags=pygame.BLEND_RGB_ADD)
        for p in self.particles:
            if p.kind in ("smoke", "dust"):
                continue
            k = 1.0 - p.age / p.life
            add_glow(screen, (p.x, p.y), p.size * 4.0, p.color, 0.5 * k)
            core = tuple(min(255, int(c * k + 70 * k)) for c in p.color)
            pygame.draw.circle(screen, core, (int(p.x), int(p.y)), max(1, int(p.size * (0.5 + 0.5 * k))))


def _ease(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


board_effects = BoardEffects()
