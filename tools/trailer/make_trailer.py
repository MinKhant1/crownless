"""Crownless gameplay trailer.

Drives the real game (boards, pieces, relics, banners, shop, win screen) shot by shot, adds trailer-only
light effects and story captions on top, synthesises a simple score, and writes an MP4.

    .venv\\Scripts\\python.exe tools\\trailer\\make_trailer.py                 # full trailer -> dist/crownless_trailer.mp4
    .venv\\Scripts\\python.exe tools\\trailer\\make_trailer.py --only 8 --stills 1.0   # one shot, a PNG every second

Needs imageio-ffmpeg (pip install imageio-ffmpeg) for encoding.
"""

import argparse
import array
import math
import os
import random
import subprocess
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame

W, H, FPS = 1920, 1080, 30

# Every animation in the game reads pygame.time.get_ticks(); a virtual clock keeps motion smooth however slowly frames render.
_CLOCK = [0.0]
pygame.time.get_ticks = lambda: int(_CLOCK[0] * 1000)

pygame.display.init()
pygame.font.init()
SCREEN = pygame.display.set_mode((W, H))

from config.settings import ENEMY_ID_START, parse_square
from game.army_manager import ArmyManager
from game.piece import Piece
from game.relics import relic_context as _relic_context
from game.relics.events import CAPTURE_RESOLVED, RELIC_VISUAL_TRIGGER
from game.run_state import RunState
from game.scene_manager import SceneManager
from rendering import style
from rendering.asset_manager import AssetManager
from rendering.battle_columns import draw_left_sidebar
from rendering.layout import build_layout
from rendering.piece_animation_controller import piece_motion
from rendering.relic_bar_renderer import RelicBar
from rendering.relic_flip import shop_reveal
from rendering.shop_layout import build_shop_layout
from rendering.shop_offers import shop_offers
from rendering.shop_piece_hand import shop_piece
from rendering.shop_relic_hand import shop_hand
from rendering.shop_renderer import draw_shop
from rendering.win_screen import win_screen
from scenes import battle_scene
from scenes.campaign_view import present, settle_finished_board
from scenes.deployment_scene import DeploymentScene

# The battle view draws "Debug Win / Debug Loss" buttons; a trailer should not.
battle_scene.draw_button = lambda *args, **kwargs: None

ASSETS = AssetManager(ROOT / "assets")
LAYOUT = build_layout(W, H)
SHOP_LAYOUT = build_shop_layout(W, H, LAYOUT.left.right + 12)

IVORY = (241, 228, 200)
GOLD = (236, 204, 132)
TRAIT_COLORS = {
    "golden": (255, 196, 70),
    "ghost": (150, 190, 255),
    "explosive": (255, 104, 36),
    "wanted": (230, 60, 52),
    "wooden": (190, 130, 70),
    "magnet": (110, 140, 255),
}


def ease(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def ramp(t: float, start: float, end: float) -> float:
    if end <= start:
        return 1.0 if t >= end else 0.0
    return ease((t - start) / (end - start))


def window_alpha(t: float, start: float, end: float, fade: float = 0.7) -> float:
    """1 inside [start, end], fading over `fade` seconds at both edges."""
    return min(ramp(t, start, start + fade), 1.0 - ramp(t, end - fade, end))


def square_center(name: str) -> tuple[int, int]:
    return LAYOUT.square_rect(*parse_square(name)).center


# ----------------------------------------------------------------------------------------------- light effects

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


class Effects:
    """Particles, glows and rings drawn in game-space, so the camera zooms them with the board."""

    def __init__(self) -> None:
        self.rng = random.Random(7)
        self.particles: list[Particle] = []
        self.glows: list[list] = []  # [x, y, radius, color, life, age, grow]
        self.rings: list[list] = []  # [x, y, radius_end, color, life, age]
        self.shake = 0.0

    def clear(self) -> None:
        self.particles.clear()
        self.glows.clear()
        self.rings.clear()
        self.shake = 0.0

    def glow(self, pos, radius, color, life=0.8, grow=0.0) -> None:
        self.glows.append([pos[0], pos[1], radius, color, life, 0.0, grow])

    def ring(self, pos, radius, color, life=0.6) -> None:
        self.rings.append([pos[0], pos[1], radius, color, life, 0.0])

    def burst(self, pos, color, count=24, speed=260.0, life=0.7, size=3.0, gravity=0.0, drag=2.5, kind="spark") -> None:
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

    def capture(self, pos, attacker: str) -> None:
        color = (255, 214, 140) if attacker == "white" else (200, 70, 90)
        self.glow(pos, 120, color, life=0.45)
        self.ring(pos, 90, color, life=0.45)
        self.burst(pos, color, count=26, speed=320, life=0.55, size=3.2)
        self.burst(pos, (90, 70, 56), count=14, speed=120, life=0.9, size=6, drag=3.0, kind="dust")
        self.shake = max(self.shake, 4.0)

    def explosion(self, pos) -> None:
        self.glow(pos, 340, (255, 140, 50), life=0.9, grow=0.4)
        self.glow(pos, 160, (255, 236, 190), life=0.35)
        self.ring(pos, 260, (255, 150, 60), life=0.7)
        self.ring(pos, 170, (255, 220, 150), life=0.45)
        self.burst(pos, (255, 160, 60), count=70, speed=620, life=0.9, size=4.0, gravity=240)
        self.burst(pos, (255, 230, 170), count=30, speed=420, life=0.5, size=3.0)
        self.burst(pos, (60, 40, 30), count=26, speed=160, life=1.6, size=12, drag=2.0, kind="smoke")
        self.shake = max(self.shake, 22.0)

    def holy(self, pos, color, big=False) -> None:
        self.glow(pos, 260 if big else 150, color, life=1.4 if big else 1.0, grow=0.25)
        self.ring(pos, 200 if big else 120, color, life=0.9)
        for _ in range(40 if big else 18):
            self.rise(pos, color, spread=60 if big else 34, speed=140 if big else 90, life=1.6, size=3.0, kind="spark")

    def update(self, dt: float) -> None:
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
        self.shake *= math.exp(-6.0 * dt)

    def draw(self, surface: pygame.Surface) -> None:
        for p in self.particles:
            if p.kind in ("smoke", "dust"):
                k = 1.0 - p.age / p.life
                size = int(p.size * (1.0 + p.age * 1.5))
                blob = pygame.Surface((size * 2 + 2, size * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(blob, (*p.color, int(110 * k)), (size + 1, size + 1), size)
                surface.blit(blob, (p.x - size, p.y - size))
        for x, y, radius, color, life, age, grow in self.glows:
            k = 1.0 - age / life
            add_glow(surface, (x, y), radius * (1.0 + grow * age / life), color, k * k)
        for x, y, radius, color, life, age in self.rings:
            k = age / life
            r = int(radius * ease(k) + 8)
            fade = (1.0 - k) ** 1.5
            ring_color = tuple(int(c * fade) for c in color)
            # additive, so a fading ring dims towards nothing instead of towards a dark outline
            layer = pygame.Surface((r * 2 + 4, r * 2 + 4))
            layer.fill((0, 0, 0))
            pygame.draw.circle(layer, ring_color, (r + 2, r + 2), r, width=max(2, int(10 * (1 - k))))
            surface.blit(layer, (int(x) - r - 2, int(y) - r - 2), special_flags=pygame.BLEND_RGB_ADD)
        for p in self.particles:
            if p.kind in ("smoke", "dust"):
                continue
            k = 1.0 - p.age / p.life
            add_glow(surface, (p.x, p.y), p.size * 4.0, p.color, 0.55 * k)
            core = tuple(min(255, int(c * k + 70 * k)) for c in p.color)
            pygame.draw.circle(surface, core, (int(p.x), int(p.y)), max(1, int(p.size * (0.5 + 0.5 * k))))


FX = Effects()


def aura(game, dt: float, t: float, strength: float = 1.0) -> None:
    """Soft trait-coloured light under special pieces, plus the motes each trait gives off."""
    if game is None or strength <= 0:
        return
    rng = FX.rng
    square = LAYOUT.square
    for piece in game.board.pieces:
        if not piece.trait or piece.col is None:
            continue
        color = TRAIT_COLORS.get(piece.trait)
        if color is None:
            continue
        cx, cy = LAYOUT.square_rect(piece.col, piece.row).center
        pulse = 0.75 + 0.25 * math.sin(t * 3.0 + piece.id)
        add_glow(SCREEN, (cx, cy + square * 0.18), square * 0.62, color, 0.42 * pulse * strength)
        chance = dt * 9.0 * strength
        if rng.random() < chance:
            if piece.trait == "golden":
                FX.rise((cx, cy), (255, 214, 110), spread=square * 0.3, speed=50, size=2.6, kind="spark")
            elif piece.trait == "ghost":
                FX.rise((cx, cy + square * 0.1), (170, 205, 255), spread=square * 0.32, speed=34, life=1.8, size=3.4)
            elif piece.trait == "explosive":
                FX.rise((cx, cy - square * 0.25), (255, 120, 40), spread=square * 0.12, speed=80, life=0.9, size=2.2)
            elif piece.trait == "wanted":
                if rng.random() < 0.35:
                    FX.ring((cx, cy), square * 0.55, (200, 50, 46), life=0.9)
            elif piece.trait == "magnet":
                angle = rng.uniform(0, math.tau)
                FX.particles.append(Particle(cx + math.cos(angle) * square * 0.45, cy + math.sin(angle) * square * 0.3,
                                             -math.cos(angle) * 40, -math.sin(angle) * 30, 0.9, 2.4, (140, 170, 255), 0.5))
            else:
                FX.rise((cx, cy + square * 0.2), (200, 150, 90), spread=square * 0.3, speed=20, life=1.5, size=2.2)


def ambient_embers(dt: float, rate: float, area: pygame.Rect | None = None) -> None:
    area = area or pygame.Rect(0, 0, W, H)
    count = int(rate * dt + FX.rng.random())
    for _ in range(count):
        FX.particles.append(Particle(FX.rng.uniform(area.left, area.right), area.bottom + 10, FX.rng.uniform(-20, 20),
                                     -FX.rng.uniform(25, 70), FX.rng.uniform(4, 8), FX.rng.uniform(1.2, 2.6),
                                     (255, FX.rng.randint(120, 170), 60), 0.05, 0.0, "ember"))


# Relic flashes in the game last a single frame (the turn ends in the same click); make them a visible pillar of light.
_original_flash = _relic_context.RelicContext.flash


def _flash(self, col, row, color):
    _original_flash(self, col, row, color)
    center = LAYOUT.square_rect(col, row).center
    FX.holy(center, tuple(min(255, c + 30) for c in color))
    DIRECTOR.sfx("chime", 0.7)


_relic_context.RelicContext.flash = _flash


# ----------------------------------------------------------------------------------------------- camera and post

class Camera:
    def __init__(self, keys=None) -> None:
        self.keys = keys or [(0.0, W / 2, H / 2, 1.0)]
        self.rect = pygame.Rect(0, 0, W, H)
        self.zoom = 1.0

    def at(self, t: float):
        keys = self.keys
        if t <= keys[0][0]:
            return keys[0][1:]
        for (t0, x0, y0, z0), (t1, x1, y1, z1) in zip(keys, keys[1:]):
            if t <= t1:
                k = ease((t - t0) / max(1e-6, t1 - t0))
                return x0 + (x1 - x0) * k, y0 + (y1 - y0) * k, z0 + (z1 - z0) * k
        return keys[-1][1:]

    def apply(self, source: pygame.Surface, t: float) -> pygame.Surface:
        cx, cy, zoom = self.at(t)
        if FX.shake > 0.3:
            cx += FX.rng.uniform(-FX.shake, FX.shake)
            cy += FX.rng.uniform(-FX.shake, FX.shake)
            zoom = max(zoom, 1.0 + FX.shake / 600)
        self.zoom = zoom
        if zoom <= 1.001:
            self.rect = pygame.Rect(0, 0, W, H)
            return source.copy()
        w, h = int(W / zoom), int(H / zoom)
        x = int(max(0, min(W - w, cx - w / 2)))
        y = int(max(0, min(H - h, cy - h / 2)))
        self.rect = pygame.Rect(x, y, w, h)
        return pygame.transform.smoothscale(source.subsurface(self.rect), (W, H))

    def map(self, point) -> tuple[int, int]:
        return (int((point[0] - self.rect.x) * W / self.rect.w), int((point[1] - self.rect.y) * H / self.rect.h))


def _vignette() -> pygame.Surface:
    small = pygame.Surface((192, 108))
    for y in range(108):
        for x in range(192):
            dx = (x - 96) / 96
            dy = (y - 54) / 54
            d = math.sqrt(dx * dx * 0.85 + dy * dy)
            v = int(255 * max(0.38, min(1.0, 1.18 - 0.55 * d * d)))
            small.set_at((x, y), (v, v, v))
    return pygame.transform.smoothscale(small, (W, H))


VIGNETTE = _vignette()


def grade(frame: pygame.Surface, desaturate: float = 0.0, brightness: float = 1.0, warm: float = 0.0) -> None:
    if desaturate > 0.01:
        gray = pygame.transform.grayscale(frame)
        gray.set_alpha(int(255 * min(1.0, desaturate)))
        frame.blit(gray, (0, 0))
    if warm > 0.01:
        frame.fill((255, int(255 - 18 * warm), int(255 - 46 * warm)), special_flags=pygame.BLEND_RGB_MULT)
    if brightness < 0.999:
        v = int(255 * max(0.0, brightness))
        frame.fill((v, v, v), special_flags=pygame.BLEND_RGB_MULT)
    frame.blit(VIGNETTE, (0, 0), special_flags=pygame.BLEND_RGB_MULT)


def fade(frame: pygame.Surface, amount: float, color=(0, 0, 0)) -> None:
    if amount <= 0.004:
        return
    veil = pygame.Surface((W, H))
    veil.fill(color)
    veil.set_alpha(int(255 * min(1.0, amount)))
    frame.blit(veil, (0, 0))


def caption(frame: pygame.Surface, text: str, alpha: float, y: int | None = None, size: int = 52, color=IVORY, drift: float = 0.0, bold=False) -> None:
    if alpha <= 0.01:
        return
    font = style.title_font(size, bold=bold)
    surface = font.render(text, True, color)
    y = H // 2 if y is None else y
    rect = surface.get_rect(center=(W // 2, int(y + (1.0 - alpha) * 14 + drift)))
    # warm halo behind the words: rendered on black so the additive blend only lights the letters' surroundings
    halo = font.render(text, True, (150, 96, 36), (0, 0, 0)).convert()
    halo = pygame.transform.smoothscale(halo, (max(1, rect.w // 8), max(1, rect.h // 8)))
    halo = pygame.transform.smoothscale(halo, (rect.w + 80, rect.h + 50))
    level = int(255 * alpha * 0.8)
    halo.fill((level, level, level), special_flags=pygame.BLEND_RGB_MULT)
    frame.blit(halo, halo.get_rect(center=rect.center), special_flags=pygame.BLEND_RGB_ADD)
    shadow = font.render(text, True, (0, 0, 0))
    shadow.set_alpha(int(200 * alpha))
    frame.blit(shadow, rect.move(0, 3))
    surface.set_alpha(int(255 * alpha))
    frame.blit(surface, rect)


def lower_band(frame: pygame.Surface, alpha: float) -> None:
    if alpha <= 0.01:
        return
    band = pygame.Surface((W, 260), pygame.SRCALPHA)
    for y in range(260):
        band.fill((0, 0, 0, int(190 * alpha * (y / 260) ** 1.4)), pygame.Rect(0, y, W, 1))
    frame.blit(band, (0, H - 260))


def trait_label(frame: pygame.Surface, camera: Camera, square: str, text: str, color, alpha: float) -> None:
    if alpha <= 0.01:
        return
    cx, cy = camera.map(square_center(square))
    font = style.title_font(34, bold=True)
    surface = font.render(text, True, color)
    rect = surface.get_rect(midtop=(cx, cy + int(LAYOUT.square * camera.zoom * 0.52)))
    plate = pygame.Surface((rect.w + 40, rect.h + 14), pygame.SRCALPHA)
    plate.fill((14, 8, 5, int(170 * alpha)))
    frame.blit(plate, plate.get_rect(center=rect.center))
    pygame.draw.line(frame, (*GOLD,), (rect.left - 16, rect.bottom + 8), (rect.right + 16, rect.bottom + 8), 1)
    surface.set_alpha(int(255 * alpha))
    frame.blit(surface, rect)


# ----------------------------------------------------------------------------------------------- the game, scripted

class Stage:
    """One self-contained game state: a run, its scene manager and widgets, ticked like main.py does."""

    def __init__(self, run: RunState) -> None:
        self.run = run
        self.scene = SceneManager()
        self.deployment = DeploymentScene()
        self.relic_bar = RelicBar()
        self.relic_bar.bind(run)
        piece_motion.clear()
        FX.clear()
        dispatcher = run.relics.dispatcher
        dispatcher.subscribe(CAPTURE_RESOLVED, self._on_capture, priority=99)
        dispatcher.subscribe(RELIC_VISUAL_TRIGGER, self._on_relic, priority=99)
        self.queue: list[tuple[float, object]] = []

    def _on_capture(self, event) -> None:
        payload = event.payload
        pos = LAYOUT.square_rect(*payload["destination_square"]).center
        if payload.get("captured_trait") == "explosive":
            FX.explosion(pos)
            DIRECTOR.sfx("boom", 1.0)
        else:
            FX.capture(pos, payload.get("capturing_color", "white"))
            DIRECTOR.sfx("hit", 0.8 if payload.get("captured_piece_type") == "king" else 0.5)

    def _on_relic(self, event) -> None:
        instance_id = event.payload.get("relic_instance_id")
        for slot in self.relic_bar.placements(self.run, LAYOUT, pygame.time.get_ticks()):
            if slot.owned.instance_id == instance_id:
                FX.holy(slot.drawn.center, (255, 210, 120))
                FX.glow(slot.drawn.center, 170, (255, 200, 110), life=1.2)

    # moves are queued as (game time, action) and fire as the clock passes them
    def at(self, when: float, action) -> None:
        self.queue.append((when, action))
        self.queue.sort(key=lambda item: item[0])

    def move(self, when: float, origin: str, target: str, lift: float = 0.45) -> None:
        self.at(when, lambda: self._click(origin, select=True))
        self.at(when + lift, lambda: self._click(target, select=False, origin=origin))

    def _click(self, square: str, select: bool, origin: str | None = None) -> None:
        session = self.run.battle
        if session is None or session.outcome is not None:
            return
        col, row = parse_square(square)
        if select:
            piece = session.game.board.piece_at(col, row)
            if piece is None or piece.color != session.game.turns.current:
                raise RuntimeError(f"no {session.game.turns.current} piece to select on {square}")
        else:
            legal = {(m.to_col, m.to_row) for m in session.game.legal}
            if (col, row) not in legal:
                raise RuntimeError(f"illegal move {origin}->{square}; legal: {sorted(legal)}")
        session.click(col, row)
        if session.outcome == "victory":
            settle_finished_board(self.run)
            self.run.finish_victory()
            self.scene.begin_banner("level_complete")
        elif session.outcome == "defeat":
            settle_finished_board(self.run)
            self.run.finish_defeat()
            self.scene.begin_banner("game_over")

    def tick(self, game_time: float, dt: float) -> None:
        while self.queue and self.queue[0][0] <= game_time:
            _when, action = self.queue.pop(0)
            action()
        run = self.run
        self.relic_bar.bind(run)
        self.scene.update(dt)
        if run.phase in ("preview", "deployment", "battle", "victory", "defeat"):
            self.relic_bar.update(dt, run, LAYOUT)
        if run.phase == "shop":
            shop_reveal.update(dt, (run.shop.offer_serial, run.shop.relic_id))
            shop_piece.prepare(ASSETS, run, SHOP_LAYOUT)
            shop_piece.update(dt, run, SHOP_LAYOUT, (W, H))
            shop_hand.update(dt, run, SHOP_LAYOUT, (W, H))
            shop_offers.update(dt, run, SHOP_LAYOUT)
        if run.phase == "complete":
            win_screen.update(dt, run)

    def draw(self) -> None:
        present(SCREEN, ASSETS, self.run, self.deployment, self.relic_bar, self.scene, LAYOUT, SHOP_LAYOUT)

    @property
    def game(self):
        return None if self.run.battle is None else self.run.battle.game


def make_run(level: int, army, enemies, relics=(), seed: int = 11) -> RunState:
    """army: (kind, square, trait) for white; enemies: (kind, square) for black. Starts in deployment."""
    run = RunState(seed)
    run.level = level
    run.prepare_level()
    run.army = ArmyManager()
    run.army.capacity = 9
    run.deployment.placed = {}
    for kind, square, trait in army:
        piece = run.army.create(kind)
        piece.trait = trait
        run.deployment.placed[piece.id] = parse_square(square)
    run.enemies = [Piece(ENEMY_ID_START + i, kind, "black", *parse_square(square)) for i, (kind, square) in enumerate(enemies)]
    for relic_id in relics:
        run.relics.acquire(relic_id)
    run.phase = "deployment"
    run.formation_snapshot = dict(run.deployment.placed)
    # trailer boards are staged mid-battle, so pieces may stand beyond the two deployment rows
    run.validate_deployment = lambda: True
    return run


def start(run: RunState, stage: Stage, banner: bool = True) -> None:
    if not run.start_battle():
        raise RuntimeError(f"battle did not start: {run.notice}")
    if banner:
        stage.scene.begin_banner("battle_start")


STARTER_ARMY = (
    ("rook", "A1", None), ("knight", "B1", None), ("queen", "C1", None), ("king", "D1", None),
    ("bishop", "E1", None), ("pawn", "A2", None),
)
LEVEL1 = (("pawn", "A5"), ("pawn", "C5"), ("pawn", "E5"), ("knight", "D6"))


# ----------------------------------------------------------------------------------------------- director

class Director:
    def __init__(self, out: Path | None, stills: float, still_dir: Path | None) -> None:
        self.time = 0.0  # seconds of finished video
        self.frames = 0
        self.out = out
        self.stills = stills
        self.still_dir = still_dir
        self.next_still = 0.0
        self.sounds: list[tuple[float, str, float]] = []
        self.music: list[tuple[float, str, float]] = []
        self.encoder = None
        if out is not None:
            import imageio_ffmpeg

            self.ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            self.video_tmp = out.with_suffix(".video.mp4")
            self.encoder = subprocess.Popen(
                [self.ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                 "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                 str(self.video_tmp)],
                stdin=subprocess.PIPE,
            )

    def sfx(self, kind: str, strength: float = 1.0) -> None:
        self.sounds.append((self.time, kind, strength))

    def cue(self, kind: str, value: float = 1.0, offset: float = 0.0) -> None:
        self.music.append((self.time + offset, kind, value))

    def emit(self, frame: pygame.Surface) -> None:
        if self.encoder is not None:
            self.encoder.stdin.write(pygame.image.tobytes(frame, "RGB"))
        if self.still_dir is not None and self.stills > 0 and self.time >= self.next_still:
            pygame.image.save(frame, str(self.still_dir / f"t{self.time:06.2f}.png"))
            self.next_still += self.stills
        self.frames += 1
        self.time = self.frames / FPS

    def run(self, seconds: float, step):
        """Call step(local_time, dt) once per frame for `seconds` of video; step returns the finished frame."""
        count = int(round(seconds * FPS))
        for i in range(count):
            t = i / FPS
            dt = 1.0 / FPS
            _CLOCK[0] += dt
            self.emit(step(t, dt))

    def finish(self) -> None:
        if self.encoder is not None:
            self.encoder.stdin.close()
            self.encoder.wait()


DIRECTOR: Director = None  # set in main()


def render_stage(stage: Stage, camera: Camera, t: float, game_dt: float, game_time: float, *, auras: float = 0.0,
                 embers: float = 0.0, desat: float = 0.0, bright: float = 1.0, warm: float = 0.25) -> pygame.Surface:
    stage.tick(game_time, game_dt)
    stage.draw()
    aura(stage.game, game_dt, game_time, auras)
    if embers:
        ambient_embers(game_dt, embers)
    FX.update(game_dt)
    FX.draw(SCREEN)
    frame = camera.apply(SCREEN, t)
    grade(frame, desat, bright, warm)
    return frame


class SlowMo:
    """Game time that can run slower than video time (speed 1 = real time)."""

    def __init__(self, keys=((0.0, 1.0),)) -> None:
        self.keys = list(keys)
        self.time = 0.0

    def speed(self, t: float) -> float:
        keys = self.keys
        if t <= keys[0][0]:
            return keys[0][1]
        for (t0, s0), (t1, s1) in zip(keys, keys[1:]):
            if t <= t1:
                return s0 + (s1 - s0) * ease((t - t0) / max(1e-6, t1 - t0))
        return keys[-1][1]

    def advance(self, t: float, dt: float) -> float:
        game_dt = dt * self.speed(t)
        self.time += game_dt
        return game_dt


# ----------------------------------------------------------------------------------------------- shots

def black_card(lines, seconds: float, crown: bool = False, embers: float = 14.0, music: str | None = None) -> None:
    """Story text on black. lines: (text, start, end, y, size)."""
    FX.clear()
    crown_img = ASSETS.fitted("crown", 300, 260) if crown and ASSETS.has("crown") else None

    def step(t, dt):
        frame = pygame.Surface((W, H))
        frame.fill((6, 4, 3))
        if crown_img is not None:
            k = t / seconds
            img = pygame.transform.rotozoom(crown_img, -8 * k, 1.0 - 0.15 * k)
            img.set_alpha(int(255 * window_alpha(t, 0.2, seconds - 0.2, 1.4) * (1.0 - 0.7 * k)))
            add_glow(frame, (W // 2, int(H * 0.26 + 220 * ease(k))), 230, (120, 70, 20), 0.6 * (1 - k))
            frame.blit(img, img.get_rect(center=(W // 2, int(H * 0.26 + 220 * ease(k)))))
        ambient_embers(dt, embers)
        FX.update(dt)
        FX.draw(frame)
        for text, start_t, end_t, y, size in lines:
            caption(frame, text, window_alpha(t, start_t, end_t, 0.8), y=y, size=size)
        frame.blit(VIGNETTE, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        return frame

    DIRECTOR.run(seconds, step)


def shot_open() -> None:
    DIRECTOR.cue("pad", 0.35)
    DIRECTOR.cue("note", 0, offset=0.9)
    DIRECTOR.cue("note", 1, offset=3.9)
    black_card([("When the last king fell,", 0.9, 3.6, H // 2 + 150, 54),
                ("the crown fell with him.", 3.9, 7.0, H // 2 + 150, 54)], 7.4, crown=True)


def shot_gathering() -> None:
    """The empty board; the army steps onto it one piece at a time."""
    run = make_run(1, (), LEVEL1)
    stage = Stage(run)
    order = [("pawn", "A2"), ("rook", "A1"), ("knight", "B1"), ("bishop", "E1"), ("queen", "C1"), ("king", "D1")]
    appear = [1.6 + i * 0.75 for i in range(len(order))]
    placed = set()
    board = LAYOUT.board
    camera = Camera([(0.0, board.centerx, board.centery + 40, 1.32), (8.0, board.centerx, board.centery + 10, 1.12)])
    DIRECTOR.cue("note", 2, offset=0.6)

    def step(t, dt):
        for index, (kind, square) in enumerate(order):
            if t >= appear[index] and index not in placed:
                placed.add(index)
                piece = run.army.create(kind)
                run.deployment.placed[piece.id] = parse_square(square)
                center = square_center(square)
                FX.holy(center, (255, 214, 140), big=kind == "king")
                DIRECTOR.sfx("chime" if kind == "king" else "tick", 0.9 if kind == "king" else 0.35)
        frame = render_stage(stage, camera, t, dt, t, embers=6, bright=0.62 + 0.25 * ramp(t, 0, 6), desat=0.25)
        lower_band(frame, window_alpha(t, 0.4, 7.6, 0.8))
        caption(frame, "Only a few still answer the call.", window_alpha(t, 0.6, 7.4, 0.9), y=H - 120, size=44)
        fade(frame, 1.0 - ramp(t, 0, 0.8))
        return frame

    DIRECTOR.run(8.0, step)


def shot_king() -> None:
    run = make_run(1, STARTER_ARMY, LEVEL1)
    stage = Stage(run)
    # lift the king without showing deployment's green destination dots
    stage.deployment._destinations = lambda _run: ([], [])
    king_id = next(p.id for p in run.army.pieces if p.kind == "king")
    kx, ky = square_center("D1")
    camera = Camera([(0.0, kx, ky - 30, 1.65), (6.0, kx, ky - 50, 2.0)])
    DIRECTOR.cue("note", 3, offset=0.5)
    DIRECTOR.cue("note", 4, offset=3.0)

    def step(t, dt):
        if t > 1.0 and run.selected_piece_id is None:
            run.selected_piece_id = king_id
            FX.holy((kx, ky), (255, 220, 150), big=True)
            DIRECTOR.sfx("chime", 0.8)
        if t > 1.0 and FX.rng.random() < 0.5:
            FX.rise((kx, ky), (255, 220, 140), spread=40, speed=70, size=2.4, kind="spark")
        frame = render_stage(stage, camera, t, dt, t, embers=4, bright=0.8, desat=0.2)
        lower_band(frame, window_alpha(t, 0.3, 5.8, 0.6))
        caption(frame, "A king without a crown", window_alpha(t, 0.5, 3.0, 0.7), y=H - 120, size=48)
        caption(frame, "is still a king.", window_alpha(t, 3.0, 5.7, 0.7), y=H - 120, size=48)
        fade(frame, max(1.0 - ramp(t, 0, 0.5), ramp(t, 5.6, 6.0)))
        return frame

    DIRECTOR.run(6.0, step)


def shot_first_battle() -> None:
    run = make_run(1, STARTER_ARMY, LEVEL1, relics=("crowns_blessing",))
    stage = Stage(run)
    start(run, stage)
    stage.move(1.0, "B1", "C3")
    stage.move(2.1, "E5", "E4")
    stage.move(3.2, "C3", "E4")
    stage.move(4.4, "D6", "E4")
    stage.move(5.6, "E1", "C3")
    stage.move(6.8, "C5", "C4")
    stage.move(7.9, "C1", "C2")
    board = LAYOUT.board
    camera = Camera([(0.0, W / 2, H / 2, 1.0), (3.0, board.centerx, board.centery, 1.12), (9.5, board.centerx + 60, board.centery - 20, 1.22)])
    DIRECTOR.cue("pad", 0.55)
    DIRECTOR.cue("pulse", 0.4)

    def step(t, dt):
        frame = render_stage(stage, camera, t, dt, t, auras=0.6)
        fade(frame, max(1.0 - ramp(t, 0, 0.4), ramp(t, 9.1, 9.5)))
        return frame

    DIRECTOR.sfx("impact", 0.6)
    DIRECTOR.run(9.5, step)


def shot_shop() -> None:
    run = make_run(1, STARTER_ARMY, LEVEL1)
    run.gold = 18
    run.shop.begin_visit(run.relics.owned_ids())
    run.shop.relic_id = "crowns_blessing"
    run.shop.piece_kind = "queen"
    run.shop.piece_trait = "golden"
    run.shop.relic_choices = []
    run.shop.piece_choices = []
    run.phase = "shop"
    stage = Stage(run)
    shop_hand.clear()
    shop_piece.clear()
    shop_offers.clear()
    shop_reveal.key = None
    card = SHOP_LAYOUT.cards[1]
    camera = Camera([(0.0, W / 2 + 120, H / 2, 1.0), (2.6, card.centerx, card.centery + 40, 1.25), (6.4, card.centerx, card.centery + 20, 1.6)])
    clicked = {"card": False, "buy": False}
    entrance = {"value": 0.0}

    def step(t, dt):
        entrance["value"] = min(1.0, entrance["value"] + dt / 0.9)
        if t >= 3.4 and not clicked["card"]:
            clicked["card"] = True
            pos = card.center
            shop_hand.on_left_down(pos, run, SHOP_LAYOUT, (W, H))
            shop_hand.on_left_up(pos, run, SHOP_LAYOUT, (W, H))
            FX.holy(card.center, (255, 210, 130))
            DIRECTOR.sfx("chime", 0.6)
        if t >= 5.0 and not clicked["buy"]:
            clicked["buy"] = True
            button = shop_hand.buy_rect(run, SHOP_LAYOUT, (W, H))
            if button is not None:
                shop_hand.on_left_down(button.center, run, SHOP_LAYOUT, (W, H))
                shop_hand.on_left_up(button.center, run, SHOP_LAYOUT, (W, H))
                FX.holy(card.center, (255, 226, 160), big=True)
                DIRECTOR.sfx("chime", 1.0)
        stage.tick(t, dt)
        draw_shop(SCREEN, ASSETS, run, SHOP_LAYOUT, backdrop=True, entrance=entrance["value"])
        draw_left_sidebar(SCREEN, run, LAYOUT, ASSETS)
        if shop_reveal.face_up:
            add_glow(SCREEN, card.center, 210, (255, 190, 100), 0.35 + 0.1 * math.sin(t * 4))
            if FX.rng.random() < 0.6:
                FX.rise(card.center, (255, 220, 140), spread=card.w * 0.4, speed=60, size=2.4, kind="spark")
        FX.update(dt)
        FX.draw(SCREEN)
        frame = camera.apply(SCREEN, t)
        grade(frame, 0.0, 1.0, 0.25)
        fade(frame, max(1.0 - ramp(t, 0, 0.5), ramp(t, 6.0, 6.4)))
        return frame

    DIRECTOR.run(6.4, step)


def shot_specials() -> None:
    army = (
        ("king", "D1", None), ("rook", "A1", "ghost"), ("pawn", "B2", "golden"), ("knight", "E2", "wanted"),
        ("bishop", "F1", "magnet"), ("queen", "C1", "wooden"), ("pawn", "D2", "explosive"),
    )
    enemies = (("queen", "D6"), ("pawn", "C5"), ("knight", "B6"), ("rook", "F6"), ("pawn", "E5"))
    run = make_run(2, army, enemies)
    stage = Stage(run)
    start(run, stage, banner=False)
    stage.move(0.8, "D2", "D3")       # the explosive pawn steps forward as bait
    stage.move(9.0, "D6", "D3", 0.6)  # the queen takes it, and the blast takes her
    stage.move(11.6, "C1", "C4")
    board = LAYOUT.board
    cut = [
        (0.0, board.centerx, board.centery, 1.08),
        (1.6, board.centerx, board.centery, 1.08),
        (2.2, *square_center("B2"), 1.9), (3.7, *square_center("B2"), 2.0),
        (4.1, *square_center("A1"), 1.9), (5.5, *square_center("A1"), 2.0),
        (5.9, *square_center("E2"), 1.9), (7.3, *square_center("E2"), 2.0),
        (7.8, *square_center("D4"), 1.5), (9.6, *square_center("D4"), 1.6),
        (11.0, board.centerx, board.centery, 1.25), (13.5, board.centerx, board.centery, 1.12),
    ]
    camera = Camera(cut)
    clock = SlowMo([(0.0, 1.0), (9.55, 1.0), (9.75, 0.3), (11.2, 0.3), (12.0, 1.0)])
    labels = [("B2", "GOLDEN", TRAIT_COLORS["golden"], 2.3, 3.8), ("A1", "GHOST", TRAIT_COLORS["ghost"], 4.2, 5.6),
              ("E2", "WANTED", TRAIT_COLORS["wanted"], 6.0, 7.4), ("D3", "EXPLOSIVE", TRAIT_COLORS["explosive"], 7.9, 9.4)]
    DIRECTOR.cue("pad", 0.6)
    DIRECTOR.cue("pulse", 0.6)
    DIRECTOR.cue("riser", 1.0, offset=7.6)

    def step(t, dt):
        game_dt = clock.advance(t, dt)
        frame = render_stage(stage, camera, t, game_dt, clock.time, auras=1.0)
        for square, text, color, a, b in labels:
            trait_label(frame, camera, square, text, color, window_alpha(t, a, b, 0.35))
        if 9.5 < t < 11.4:
            fade(frame, 0.25 * (1 - ramp(t, 9.6, 11.4)), (255, 200, 140))
        lower_band(frame, window_alpha(t, 0.2, 1.9, 0.4))
        caption(frame, "Raise an army touched by strange power.", window_alpha(t, 0.3, 1.9, 0.4), y=H - 120, size=44)
        fade(frame, max(1.0 - ramp(t, 0, 0.4), ramp(t, 13.1, 13.5)))
        return frame

    DIRECTOR.run(13.5, step)


def shot_relics() -> None:
    army = (("king", "D1", None), ("knight", "C3", None), ("rook", "A1", None), ("bishop", "F1", None), ("pawn", "B2", None))
    enemies = (("pawn", "D5"), ("pawn", "B5"), ("knight", "E6"), ("rook", "A6"))
    run = make_run(3, army, enemies, relics=("squire", "recruitment"))
    stage = Stage(run)
    start(run, stage, banner=False)
    stage.move(1.4, "C3", "D5", 0.55)
    stage.move(4.3, "E6", "C5")
    relic_center = LAYOUT.relics.center
    camera = Camera([(0.0, LAYOUT.board.centerx, LAYOUT.board.centery, 1.15), (1.9, *square_center("D4"), 1.55),
                     (3.6, *square_center("D4"), 1.62), (4.4, relic_center[0], relic_center[1] + 120, 1.45),
                     (6.5, LAYOUT.board.centerx, LAYOUT.board.centery - 60, 1.2)])
    clock = SlowMo([(0.0, 1.0), (1.9, 1.0), (2.05, 0.45), (3.4, 0.45), (3.9, 1.0)])

    def step(t, dt):
        game_dt = clock.advance(t, dt)
        frame = render_stage(stage, camera, t, game_dt, clock.time, auras=0.4)
        lower_band(frame, window_alpha(t, 4.2, 6.9, 0.5))
        caption(frame, "Relics of the old reign answer once more.", window_alpha(t, 4.3, 6.8, 0.6), y=H - 120, size=42)
        fade(frame, max(1.0 - ramp(t, 0, 0.4), ramp(t, 6.6, 7.0)))
        return frame

    DIRECTOR.run(7.0, step)


def shot_defeat() -> None:
    army = (("king", "D2", None), ("rook", "A1", None), ("pawn", "C2", None), ("bishop", "F1", None))
    enemies = (("pawn", "A5"), ("knight", "E4"), ("rook", "F6"), ("pawn", "C5"))
    run = make_run(3, army, enemies)
    stage = Stage(run)
    start(run, stage, banner=False)
    stage.move(0.9, "A1", "A5")          # greed: the rook takes a pawn far from home
    stage.move(2.2, "E4", "D2", 0.7)     # and the knight finds the king
    kx, ky = square_center("D2")
    camera = Camera([(0.0, LAYOUT.board.centerx, LAYOUT.board.centery, 1.1), (2.0, kx, ky - 40, 1.6), (3.6, kx, ky - 60, 1.95),
                     (5.0, W / 2, H / 2, 1.0), (8.5, W / 2, H / 2, 1.04)])
    clock = SlowMo([(0.0, 1.0), (2.75, 1.0), (2.9, 0.22), (4.2, 0.22), (5.0, 1.0)])
    DIRECTOR.cue("pad", 0.25)
    DIRECTOR.cue("pulse", 0.0)
    state = {"hit": False}

    def step(t, dt):
        game_dt = clock.advance(t, dt)
        if run.phase == "defeat" and not state["hit"]:
            state["hit"] = True
            DIRECTOR.sfx("impact", 1.0)
            DIRECTOR.cue("pad", 0.0)
            FX.glow((kx, ky), 260, (200, 30, 30), life=1.6, grow=0.3)
        frame = render_stage(stage, camera, t, game_dt, clock.time, desat=0.15 + 0.6 * ramp(t, 2.9, 5.0),
                             bright=1.0 - 0.25 * ramp(t, 2.9, 5.0))
        if state["hit"]:
            fade(frame, 0.35 * (1 - ramp(t, 2.95, 4.0)), (120, 10, 10))
        fade(frame, max(1.0 - ramp(t, 0, 0.4), ramp(t, 7.7, 8.5)))
        return frame

    DIRECTOR.run(8.5, step)


def shot_rise_montage() -> None:
    """Fast cuts: Crown's Blessing at battle start, a queen's sweep, a level won."""
    DIRECTOR.cue("pad", 0.75)
    DIRECTOR.cue("pulse", 1.0)

    def flash_in(frame, t):
        fade(frame, 0.7 * (1.0 - ramp(t, 0, 0.22)), (255, 236, 200))

    # 1: Crown's Blessing blesses the piece in front of the king the moment battle starts
    army = (("king", "C1", None), ("pawn", "C2", None), ("knight", "B1", None), ("bishop", "D1", None), ("rook", "F1", None))
    run = make_run(3, army, (("pawn", "B5"), ("pawn", "D5"), ("bishop", "C6"), ("knight", "E6"), ("rook", "A6")),
                   relics=("crowns_blessing",), seed=5)
    stage = Stage(run)
    camera = Camera([(0.0, *square_center("C2"), 1.9), (2.4, *square_center("C2"), 2.2)])
    state = {"started": False}

    def blessing(t, dt):
        if t >= 0.35 and not state["started"]:
            state["started"] = True
            start(run, stage)
        frame = render_stage(stage, camera, t, dt, t, auras=1.0)
        flash_in(frame, t)
        return frame

    DIRECTOR.sfx("impact", 0.5)
    DIRECTOR.run(2.4, blessing)

    # 2: the queen sweeps the board
    army = (("king", "D1", None), ("queen", "A2", "golden"), ("rook", "F1", None), ("knight", "B1", None))
    run = make_run(4, army, (("rook", "A6"), ("pawn", "C5"), ("bishop", "B6"), ("knight", "D6")), seed=6)
    stage = Stage(run)
    start(run, stage, banner=False)
    stage.move(0.3, "A2", "A6", 0.35)
    camera = Camera([(0.0, *square_center("A4"), 1.7), (1.9, *square_center("A5"), 1.95)])

    def sweep(t, dt):
        frame = render_stage(stage, camera, t, dt, t, auras=1.0)
        flash_in(frame, t)
        return frame

    DIRECTOR.sfx("impact", 0.5)
    DIRECTOR.run(1.9, sweep)

    # 3: a bishop clears the last enemy and the level falls
    army = (("king", "D1", None), ("bishop", "B2", "ghost"), ("rook", "F2", None), ("knight", "C1", None))
    run = make_run(4, army, (("knight", "E5"),), seed=8)
    stage = Stage(run)
    start(run, stage, banner=False)
    stage.move(0.2, "B2", "E5", 0.35)
    camera = Camera([(0.0, *square_center("D4"), 1.5), (1.6, W / 2, H / 2, 1.0), (3.6, W / 2, H / 2, 1.03)])

    def won(t, dt):
        frame = render_stage(stage, camera, t, dt, t, auras=0.8)
        flash_in(frame, t)
        fade(frame, ramp(t, 3.3, 3.6))
        return frame

    DIRECTOR.sfx("impact", 0.6)
    DIRECTOR.run(3.6, won)


def shot_final_battle() -> None:
    army = (("king", "D1", None), ("queen", "D2", "golden"), ("rook", "A1", "ghost"), ("knight", "E3", "wanted"),
            ("bishop", "F1", None), ("pawn", "C2", None))
    run = make_run(5, army, (("king", "E6"), ("pawn", "B5")), relics=("crowns_blessing", "squire", "recruitment"), seed=9)
    run.battles_won = 4
    run.gold_earned = 41
    run.pieces_lost = 3
    stage = Stage(run)
    start(run, stage, banner=False)
    stage.move(0.8, "C2", "C3")
    stage.move(1.7, "B5", "B4")
    stage.move(2.6, "C3", "B4")          # the last guard falls
    stage.move(3.6, "E6", "D6")          # the enemy king steps into the open file
    stage.move(4.6, "D2", "D6", 0.7)     # and the queen takes the crown's last keeper
    kx, ky = square_center("D6")
    camera = Camera([(0.0, LAYOUT.board.centerx, LAYOUT.board.centery, 1.12), (4.2, kx, ky + 160, 1.6),
                     (5.7, kx, ky + 60, 2.0), (6.6, W / 2, H / 2, 1.0), (9.5, W / 2, H / 2, 1.02)])
    clock = SlowMo([(0.0, 1.0), (5.25, 1.0), (5.4, 0.3), (6.4, 0.3), (6.9, 1.0)])
    state = {"blessed": False}
    DIRECTOR.cue("riser", 1.0, offset=3.2)

    def step(t, dt):
        game_dt = clock.advance(t, dt)
        if run.phase == "victory" and not state["blessed"]:
            state["blessed"] = True
            FX.holy((kx, ky), (255, 220, 140), big=True)
            FX.explosion((kx, ky))
            FX.shake = 10.0
            DIRECTOR.sfx("impact", 1.0)
        frame = render_stage(stage, camera, t, game_dt, clock.time, auras=1.0)
        if state["blessed"]:
            fade(frame, 0.45 * (1 - ramp(t, 5.4, 6.4)), (255, 236, 200))
        fade(frame, max(1.0 - ramp(t, 0, 0.4), ramp(t, 9.1, 9.5)))
        return frame

    DIRECTOR.run(9.5, step)

    # the win screen: crown comes down, coins fall, the army takes its plinth
    run.continue_from_victory()
    win_screen.update(0.0, run)
    camera = Camera([(0.0, W / 2, H / 2 - 40, 1.12), (9.0, W / 2, H / 2, 1.0)])
    DIRECTOR.cue("pad", 1.0)
    DIRECTOR.cue("pulse", 0.0)
    DIRECTOR.cue("chord", 1.0, offset=0.3)

    def crowned(t, dt):
        frame = render_stage(stage, camera, t, dt, t, embers=10, warm=0.35)
        fade(frame, max(1.0 - ramp(t, 0, 0.6), ramp(t, 8.4, 9.0)))
        return frame

    DIRECTOR.run(9.0, crowned)


def shot_title() -> None:
    FX.clear()
    logo = ASSETS.fitted("crownless_logo", 1100, 420) if ASSETS.has("crownless_logo") else None
    DIRECTOR.cue("chord", 1.0, offset=0.2)
    DIRECTOR.sfx("impact", 0.9)

    def step(t, dt):
        frame = pygame.Surface((W, H))
        frame.fill((6, 4, 3))
        ambient_embers(dt, 22)
        FX.update(dt)
        FX.draw(frame)
        a = ramp(t, 0.3, 2.0)
        add_glow(frame, (W // 2, H // 2 - 70), 620, (130, 70, 20), 0.55 * a)
        if logo is not None:
            scale = 0.94 + 0.06 * ease(t / 9.0)
            img = pygame.transform.rotozoom(logo, 0, scale)
            img.set_alpha(int(255 * a))
            rect = img.get_rect(center=(W // 2, H // 2 - 70))
            frame.blit(img, rect)
            sweep = ramp(t, 1.6, 3.2)
            if 0 < sweep < 1:
                x = rect.left + int(rect.w * sweep)
                add_glow(frame, (x, rect.centery), 200, (255, 230, 170), 0.7 * math.sin(sweep * math.pi))
        caption(frame, "A chess roguelike", window_alpha(t, 2.6, 10.0, 0.8), y=H // 2 + 200, size=40)
        caption(frame, "Take back the crown.", window_alpha(t, 4.2, 10.0, 0.8), y=H // 2 + 290, size=30, color=GOLD)
        frame.blit(VIGNETTE, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        fade(frame, ramp(t, 9.4, 10.4))
        return frame

    DIRECTOR.run(10.4, step)


SHOTS = [
    ("open", shot_open),
    ("gathering", shot_gathering),
    ("king", shot_king),
    ("first battle", shot_first_battle),
    ("card: relics", lambda: black_card([("Gather what the old reign left behind.", 0.4, 3.2, H // 2, 50)], 3.6)),
    ("shop", shot_shop),
    ("specials", shot_specials),
    ("relics", shot_relics),
    ("card: dark", lambda: (DIRECTOR.cue("pulse", 0.0), DIRECTOR.cue("pad", 0.3),
                            black_card([("But the dark remembers every king.", 0.4, 3.4, H // 2, 50)], 3.8, embers=6))),
    ("defeat", shot_defeat),
    ("card: fall", lambda: (DIRECTOR.cue("pad", 0.0),
                            black_card([("Most kings fall.", 0.5, 2.8, H // 2, 56)], 3.2, embers=3))),
    ("card: rise", lambda: (DIRECTOR.cue("riser", 1.0), DIRECTOR.cue("note", 5, offset=0.4),
                            black_card([("Rise again.", 0.4, 2.4, H // 2, 64)], 2.6, embers=40))),
    ("montage", shot_rise_montage),
    ("card: crown", lambda: black_card([("One king. One last battle.", 0.3, 2.3, H // 2, 56)], 2.6, crown=False, embers=30)),
    ("final battle", shot_final_battle),
    ("title", shot_title),
]


# ----------------------------------------------------------------------------------------------- score

RATE = 44100


def synth_score(length: float, sounds, music, path: Path) -> None:
    """A small synthesised score: drone pad, a heartbeat pulse, piano-ish notes, risers and hits."""
    n = int(length * RATE) + RATE
    out = array.array("f", bytes(4 * n))
    rng = random.Random(3)

    def env_track(kind, default):
        points = sorted((t, v) for t, k, v in music if k == kind)
        return [(0.0, default)] + points

    def level_at(points, t, glide=1.5):
        value = points[0][1]
        for i, (pt, pv) in enumerate(points):
            if t < pt:
                break
            prev = points[i - 1][1] if i > 0 else pv
            value = prev + (pv - prev) * min(1.0, (t - pt) / glide)
        return value

    pad_points = env_track("pad", 0.0)
    pulse_points = env_track("pulse", 0.0)

    # drone pad: A minor colour, slow breathing; evaluated per 64 samples for the envelope
    voices = [(55.0, 0.5), (82.41, 0.32), (110.0, 0.28), (130.81, 0.16), (164.81, 0.12)]
    phases = [0.0] * len(voices)
    step = 64
    for block in range(0, n, step):
        t = block / RATE
        level = level_at(pad_points, t) * 0.16
        for vi, (freq, amp) in enumerate(voices):
            wobble = 1.0 + 0.003 * math.sin(t * 0.7 + vi)
            inc = math.tau * freq * wobble / RATE
            breathe = 0.75 + 0.25 * math.sin(t * 0.4 + vi * 1.3)
            a = level * amp * breathe
            ph = phases[vi]
            for i in range(block, min(n, block + step)):
                out[i] += a * (math.sin(ph) + 0.25 * math.sin(2 * ph))
                ph += inc
            phases[vi] = ph % math.tau

    def add(start: float, samples) -> None:
        offset = int(start * RATE)
        for i, value in enumerate(samples):
            j = offset + i
            if 0 <= j < n:
                out[j] += value

    def tone(freq, seconds, amp, decay, harmonics=((1, 1.0), (2, 0.35), (3, 0.12))):
        count = int(seconds * RATE)
        return [amp * math.exp(-decay * i / RATE) * min(1.0, i / 200) *
                sum(h_amp * math.sin(math.tau * freq * h * i / RATE) for h, h_amp in harmonics) for i in range(count)]

    def noise_burst(seconds, amp, decay, smooth=0.08):
        count = int(seconds * RATE)
        value = 0.0
        result = []
        for i in range(count):
            value += smooth * (rng.uniform(-1, 1) - value)
            result.append(amp * value * math.exp(-decay * i / RATE))
        return result

    def boom(amp, seconds=1.6, f0=70.0, f1=32.0):
        count = int(seconds * RATE)
        result = []
        ph = 0.0
        for i in range(count):
            k = i / count
            freq = f0 + (f1 - f0) * k
            ph += math.tau * freq / RATE
            result.append(amp * math.sin(ph) * math.exp(-3.2 * k) * min(1.0, i / 120))
        return result

    # heartbeat pulse: two soft low thumps per beat at 72 bpm, louder as the music drives
    beat = 60 / 72
    t = 0.0
    thump = boom(0.5, 0.35, 90, 45)
    while t < length:
        level = level_at(pulse_points, t, glide=0.8)
        if level > 0.02:
            add(t, [v * level for v in thump])
            add(t + 0.22, [v * level * 0.6 for v in thump])
        t += beat

    melody = [440.0, 659.25, 523.25, 587.33, 493.88, 880.0]
    for t, kind, value in music:
        if kind == "note":
            freq = melody[int(value) % len(melody)]
            add(t, tone(freq, 3.5, 0.18, 1.3))
            add(t + 0.02, tone(freq / 2, 3.5, 0.08, 1.6))
        elif kind == "riser":
            count = int(2.4 * RATE)
            value_n = 0.0
            ph = 0.0
            samples = []
            for i in range(count):
                k = i / count
                value_n += 0.05 * (rng.uniform(-1, 1) - value_n)
                ph += math.tau * (120 + 500 * k * k) / RATE
                samples.append((0.25 * value_n + 0.05 * math.sin(ph)) * k * k)
            add(t, samples)
        elif kind == "chord":
            for freq, amp in ((110.0, 0.12), (164.81, 0.1), (220.0, 0.1), (261.63, 0.08), (329.63, 0.08), (440.0, 0.05)):
                add(t, tone(freq, 6.0, amp, 0.45))

    for t, kind, strength in sounds:
        if kind == "hit":
            add(t, [v * strength for v in boom(0.55, 0.5, 110, 50)])
            add(t, noise_burst(0.12, 0.35 * strength, 30, 0.5))
        elif kind == "boom":
            add(t, boom(0.9 * strength, 2.0, 60, 25))
            add(t, noise_burst(1.4, 0.7 * strength, 3.0, 0.06))
        elif kind == "impact":
            add(t, boom(0.85 * strength, 2.4, 55, 28))
            add(t, noise_burst(0.5, 0.35 * strength, 6.0, 0.03))
        elif kind == "chime":
            add(t, tone(1318.5, 1.8, 0.07 * strength, 2.2, ((1, 1.0), (2.76, 0.4), (5.4, 0.15))))
            add(t + 0.06, tone(1975.5, 1.4, 0.04 * strength, 2.8, ((1, 1.0), (2.76, 0.3))))
        elif kind == "tick":
            add(t, tone(880.0, 0.6, 0.05 * strength, 6.0))

    peak = max(1e-6, max(abs(v) for v in out))
    gain = 0.89 / peak if peak > 0.89 else 1.0
    frames = array.array("h", (int(max(-1.0, min(1.0, v * gain)) * 32767) for v in out))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes(frames.tobytes())


# ----------------------------------------------------------------------------------------------- main

def main() -> None:
    global DIRECTOR
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=str(ROOT / "dist" / "crownless_trailer.mp4"))
    parser.add_argument("--only", default="", help="comma-separated shot numbers (1-based) to render without encoding")
    parser.add_argument("--stills", type=float, default=0.0, help="also save a PNG every N seconds")
    parser.add_argument("--still-dir", default=str(ROOT / "dist" / "trailer_stills"))
    args = parser.parse_args()

    only = {int(x) for x in args.only.split(",") if x.strip()}
    still_dir = Path(args.still_dir) if args.stills > 0 else None
    if still_dir is not None:
        still_dir.mkdir(parents=True, exist_ok=True)
    out = None if only else Path(args.out)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
    DIRECTOR = Director(out, args.stills, still_dir)
    for index, (name, shot) in enumerate(SHOTS, start=1):
        if only and index not in only:
            continue
        began = DIRECTOR.time
        shot()
        print(f"shot {index:2d} {name:<14} {began:6.1f}s -> {DIRECTOR.time:6.1f}s", flush=True)
    DIRECTOR.finish()
    if out is None:
        return
    audio = out.with_suffix(".wav")
    print("synthesising score...", flush=True)
    synth_score(DIRECTOR.time, DIRECTOR.sounds, DIRECTOR.music, audio)
    subprocess.run([DIRECTOR.ffmpeg, "-y", "-loglevel", "error", "-i", str(DIRECTOR.video_tmp), "-i", str(audio),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], check=True)
    DIRECTOR.video_tmp.unlink(missing_ok=True)
    audio.unlink(missing_ok=True)
    print(f"done: {out}  ({DIRECTOR.time:.1f}s)")


if __name__ == "__main__":
    main()
