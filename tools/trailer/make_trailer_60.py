"""Crownless - 60-second trailer.

Fast and loud, but dressed like the game: Cinzel titles engraved in gold, burgundy ribbons with gold trim,
parchment slips and carved walnut, candle glow, golden light sweeps and embers. Cut to the beat of the game's own
132 bpm battle theme; every board shot is the real game, driven move by move.

    .venv\\Scripts\\python.exe tools\\trailer\\make_trailer_60.py                       # -> dist/crownless_trailer_60s.mp4
    .venv\\Scripts\\python.exe tools\\trailer\\make_trailer_60.py --only 8 --stills 0.25   # one shot, PNG stills, no video

Needs numpy and imageio-ffmpeg (tools/requirements.txt). Reuses the engine in make_trailer.py.
"""

import argparse
import math
import random
import subprocess
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_trailer as mt  # noqa: E402  (sets up pygame, the virtual clock and the game)

import numpy as np  # noqa: E402
import pygame  # noqa: E402

from config.settings import MAX_LEVEL, parse_square  # noqa: E402
from game.relics.relic_data import relic_by_id  # noqa: E402
from game.traits import trait_by_id  # noqa: E402
from rendering import style  # noqa: E402
from rendering.hud_renderer import draw_background  # noqa: E402
from rendering.layout import build_layout  # noqa: E402
from rendering.relic_bar_renderer import RelicBar  # noqa: E402
from rendering.relic_card import RelicCardRenderer  # noqa: E402
from rendering.special_piece_renderer import special_pieces  # noqa: E402
from rendering.win_screen import win_screen  # noqa: E402
from scenes.deployment_scene import DeploymentScene  # noqa: E402

W, H, FPS = mt.W, mt.H, mt.FPS
ROOT = mt.ROOT
BPM = 132
BEAT = 60.0 / BPM
BAR = BEAT * 4

# the game's palette (rendering/style.py)
GOLD = style.GOLD_BRIGHT
GOLD_DEEP = (150, 100, 38)
IVORY = style.IVORY
INK = style.INK
BURGUNDY = style.BURGUNDY
BURGUNDY_DEEP = style.BURGUNDY_DEEP
NIGHT = (14, 9, 6)
CANDLE = (255, 196, 120)
WARM_FLASH = (255, 232, 190)


def ease_out_back(x: float, s: float = 1.7) -> float:
    x = max(0.0, min(1.0, x)) - 1
    return 1 + x * x * ((s + 1) * x + s)


# ----------------------------------------------------------------------------------------------- titles

_GRADIENTS: dict[tuple, pygame.Surface] = {}
_TITLES: dict[tuple, pygame.Surface] = {}


def _gradient(width: int, height: int, top, middle, bottom) -> pygame.Surface:
    key = (width, height, top, middle, bottom)
    if key not in _GRADIENTS:
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        for y in range(height):
            k = y / max(1, height - 1)
            a, b, f = (top, middle, k * 2) if k < 0.5 else (middle, bottom, (k - 0.5) * 2)
            color = tuple(int(a[i] + (b[i] - a[i]) * f) for i in range(3))
            pygame.draw.line(surface, (*color, 255), (0, y), (width, y))
        _GRADIENTS[key] = surface
    return _GRADIENTS[key]


def engraved(text: str, size: int, ink: str = "gold", italic: bool = False) -> pygame.Surface:
    """Cinzel lettering cut in gold (or ivory / ink) with a dark rim and a soft drop shadow."""
    face = style.body_font(size, italic=True) if italic else style.title_font(size, bold=True)
    mask = face.render(text, True, (255, 255, 255))
    w, h = mask.get_size()
    pad = max(4, size // 7)
    out = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    rim_color = (24, 12, 6) if ink != "ink" else (250, 236, 206)
    rim = face.render(text, True, rim_color)
    shadow = face.render(text, True, (0, 0, 0))
    shadow.set_alpha(150)
    out.blit(shadow, (pad + max(2, size // 22), pad + max(3, size // 16)))
    radius = max(1, size // 30)
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            if dx * dx + dy * dy <= radius * radius:
                out.blit(rim, (pad + dx, pad + dy))
    if ink == "gold":
        fill = _gradient(w, h, (255, 244, 206), (238, 196, 112), (160, 104, 40)).copy()
    elif ink == "ivory":
        fill = _gradient(w, h, (255, 252, 240), IVORY, (206, 186, 150)).copy()
    else:
        fill = _gradient(w, h, (74, 46, 28), INK, (36, 22, 12)).copy()
    fill.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    out.blit(fill, (pad, pad))
    return out


def ribbon(text: str, size: int, kind: str = "burgundy", tilt: float = 0.0) -> pygame.Surface:
    """A title on a backing in the game's materials.

    burgundy: cloth banner with swallowtail ends and gold trim, gold lettering (like the CROWNLESS logo)
    parchment: a torn parchment slip with ink lettering
    wood: a carved walnut plaque with gold lettering
    """
    key = (text, size, kind, tilt)
    if key in _TITLES:
        return _TITLES[key]
    word = engraved(text, size, "ink" if kind == "parchment" else ("ivory" if kind == "night" else "gold"))
    w, h = word.get_size()
    pad_x, pad_y = int(size * 0.75), int(size * 0.18)
    bw, bh = w + pad_x * 2, h + pad_y * 2
    surface = pygame.Surface((bw + 40, bh + 40), pygame.SRCALPHA)
    body = pygame.Rect(20, 16, bw, bh)
    shadow = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    if kind == "burgundy":
        notch = int(bh * 0.32)
        points = [(body.left, body.top), (body.right, body.top), (body.right - notch, body.centery),
                  (body.right, body.bottom), (body.left, body.bottom), (body.left + notch, body.centery)]
        pygame.draw.polygon(shadow, (0, 0, 0, 120), [(x + 8, y + 10) for x, y in points])
        surface.blit(shadow, (0, 0))
        cloth = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(cloth, (*BURGUNDY, 255), points)
        shade = _gradient(surface.get_width(), surface.get_height(), (150, 52, 44), BURGUNDY, BURGUNDY_DEEP)
        tinted = shade.copy()
        tinted.blit(cloth, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(tinted, (0, 0))
        trim = int(size * 0.07) + 4
        for offset, color in ((trim, style.GOLD), (trim + 4, style.GOLD_DIM)):
            pygame.draw.line(surface, color, (body.left + notch // 2 + 6, body.top + offset), (body.right - notch // 2 - 6, body.top + offset), 2)
            pygame.draw.line(surface, color, (body.left + notch // 2 + 6, body.bottom - offset), (body.right - notch // 2 - 6, body.bottom - offset), 2)
        for x in (body.left + notch + 18, body.right - notch - 18):
            style.ornament_rule(surface, (x, body.centery), 22, style.GOLD)
    elif kind == "parchment":
        style.draw_parchment(surface, mt.ASSETS, body, seed=len(text) + size, shadow=True)
        style.ornament_rule(surface, (body.centerx, body.bottom - pad_y // 2 - 2), int(bw * 0.5), style.GOLD_DIM)
    else:  # wood or night
        style.draw_wood_panel(surface, body, seed=len(text), shadow=True)
    surface.blit(word, word.get_rect(center=body.center))
    if tilt:
        surface = pygame.transform.rotozoom(surface, tilt, 1.0)
    _TITLES[key] = surface
    return surface


def slam(frame: pygame.Surface, image: pygame.Surface, center, t: float, start: float, end: float = 99.0) -> None:
    """Bring a title in hard and settle it: drops in large, lands with a glint of light running across it,
    and lifts away with a fade at `end`."""
    if t < start:
        return
    k = (t - start) / 0.18
    scale = 1.0 + 0.32 * (1 - ease_out_back(min(1.0, k)))
    alpha = min(1.0, (t - start) / 0.07)
    cx, cy = center
    cy -= 26 * (1 - min(1.0, k))
    if t > end:
        out = min(1.0, (t - end) / 0.16)
        alpha *= 1 - out
        cy -= 40 * out
    if alpha <= 0.01:
        return
    img = pygame.transform.rotozoom(image, 0, scale) if abs(scale - 1) > 0.002 else image
    if alpha < 0.99:
        img = img.copy()
        img.set_alpha(int(255 * alpha))
    rect = img.get_rect(center=(int(cx), int(cy)))
    frame.blit(img, rect)
    glint = (t - start - 0.16) / 0.42
    if 0 < glint < 1:
        x = rect.left + rect.w * glint
        mt.add_glow(frame, (x, rect.centery), rect.h * 0.55, WARM_FLASH, 0.55 * math.sin(glint * math.pi))


def light_sweep(frame: pygame.Surface, t: float, seed: int = 0, strength: float = 1.0, color=CANDLE) -> None:
    """Soft golden shafts of light sweeping across the frame, like sun through a cathedral window."""
    if strength <= 0.01:
        return
    small = pygame.Surface((W // 6, H // 6))
    small.fill((0, 0, 0))
    rng = random.Random(seed)
    for i in range(4):
        width = rng.uniform(10, 34)
        speed = rng.uniform(55, 110) * (1 if i % 2 else -1)
        x = (rng.uniform(0, W // 6) + speed * t) % (W // 6 + 120) - 60
        lean = H // 6 * 0.6
        level = rng.uniform(0.35, 0.7) * strength
        tint = tuple(int(c * level) for c in color)
        pygame.draw.polygon(small, tint, [(x, 0), (x + width, 0), (x + width - lean, H // 6), (x - lean, H // 6)])
    soft = pygame.transform.smoothscale(pygame.transform.smoothscale(small, (W // 48, H // 48)), (W, H))
    soft.fill((205, 205, 205), special_flags=pygame.BLEND_RGB_MULT)
    frame.blit(soft, (0, 0), special_flags=pygame.BLEND_RGB_ADD)


_GRAIN: list[pygame.Surface] = []


def grain(frame: pygame.Surface) -> None:
    if not _GRAIN:
        rng = np.random.default_rng(5)
        noise = rng.integers(0, 255, (W // 2, H // 2), dtype=np.uint8)
        rgb = np.repeat(noise[:, :, None], 3, axis=2)
        tile = pygame.transform.scale(pygame.surfarray.make_surface(rgb), (W, H))
        tile.set_alpha(14)
        _GRAIN.append(tile)
    frame.blit(_GRAIN[0], (0, 0))


def backdrop(frame: pygame.Surface, kind: str = "wood", darkness: float = 0.55) -> None:
    """The game's own wood background, dimmed to candlelight; or deep burgundy velvet."""
    if kind == "wood":
        draw_background(frame, mt.ASSETS)
    else:
        frame.blit(_gradient(W, H, (90, 26, 24), BURGUNDY_DEEP, (24, 8, 8)), (0, 0))
    v = int(255 * (1 - darkness))
    frame.fill((v, int(v * 0.95), int(v * 0.9)), special_flags=pygame.BLEND_RGB_MULT)


_BARS: list[pygame.Surface] = []


def letterbox(frame: pygame.Surface) -> None:
    """Carved walnut bars top and bottom, with an engraved gold rule: the frame around gameplay shots."""
    if not _BARS:
        _BARS.append(style.wood_panel((W + 40, 92), seed=3, radius=0))
    bar = _BARS[0]
    frame.blit(bar, (-20, -34))
    frame.blit(bar, (-20, H - 58))
    pygame.draw.line(frame, style.GOLD_DIM, (0, 58), (W, 58), 2)
    pygame.draw.line(frame, style.GOLD_DIM, (0, H - 59), (W, H - 59), 2)
    style.ornament_rule(frame, (W // 2, 58), 520, style.GOLD)
    style.ornament_rule(frame, (W // 2, H - 59), 520, style.GOLD)


def flash(frame: pygame.Surface, amount: float, color=WARM_FLASH) -> None:
    mt.fade(frame, max(0.0, min(1.0, amount)), color)


def ember_wash(frame: pygame.Surface, amount: float) -> None:
    """Drain the colour and leave it ember-dark: the mood when the King falls."""
    if amount <= 0:
        return
    gray = pygame.transform.grayscale(frame)
    gray.set_alpha(int(220 * amount))
    frame.blit(gray, (0, 0))
    tint = pygame.Surface((W, H))
    tint.fill((255, int(255 - 120 * amount), int(255 - 150 * amount)))
    frame.blit(tint, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    v = int(255 * (1 - 0.3 * amount))
    frame.fill((v, v, v), special_flags=pygame.BLEND_RGB_MULT)


def god_rays(frame: pygame.Surface, center, t: float, strength: float, color=CANDLE) -> None:
    """Golden rays turning slowly behind a title."""
    small = pygame.Surface((W // 4, H // 4))
    small.fill((0, 0, 0))
    cx, cy = center[0] / 4, center[1] / 4
    rng = random.Random(9)
    for i in range(12):
        angle = i / 12 * math.tau + t * 0.12 + rng.uniform(-0.15, 0.15)
        spread = rng.uniform(0.04, 0.09)
        far = 900
        pts = [(cx, cy), (cx + math.cos(angle - spread) * far, cy + math.sin(angle - spread) * far),
               (cx + math.cos(angle + spread) * far, cy + math.sin(angle + spread) * far)]
        level = strength * rng.uniform(0.18, 0.32)
        pygame.draw.polygon(small, tuple(int(c * level) for c in color), pts)
    # blurred hard so the rays read as candlelight through dust, not a cartoon sunburst
    soft = pygame.transform.smoothscale(pygame.transform.smoothscale(small, (W // 40, H // 40)), (W, H))
    frame.blit(soft, (0, 0), special_flags=pygame.BLEND_RGB_ADD)


def embers(frame: pygame.Surface, dt: float, rate: float) -> None:
    mt.ambient_embers(dt, rate)
    mt.FX.update(dt)
    mt.FX.draw(frame)


_FROM_BOARD = [False]


def finish(frame: pygame.Surface) -> pygame.Surface:
    """Canvas grain on everything; the vignette only on title cards (board shots already have the game's)."""
    grain(frame)
    if not _FROM_BOARD[0]:
        frame.blit(mt.VIGNETTE, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
    _FROM_BOARD[0] = False
    return frame


# ----------------------------------------------------------------------------------------------- timing

class Timeline:
    """Shots are placed on bar lines so cuts land on the music; frame counts come from absolute times."""

    def __init__(self) -> None:
        self.bar = 0.0

    def run(self, bars: float, step) -> None:
        start = round(self.bar * BAR * FPS)
        end = round((self.bar + bars) * BAR * FPS)
        self.bar += bars
        mt.DIRECTOR.run((end - start) / FPS, step)


TIMELINE = Timeline()


class PunchCamera(mt.Camera):
    """A camera that kicks in a little on chosen moments (captures, titles)."""

    def __init__(self, keys, punches=()) -> None:
        super().__init__(keys)
        self.punches = list(punches)

    def at(self, t):
        x, y, z = super().at(t)
        kick = sum(0.06 * math.exp(-(t - p) / 0.09) for p in self.punches if t >= p)
        return x, y, z * (1 + kick)


class Stage(mt.Stage):
    """The trailer stage, plus a wooden knock for every quiet move (captures already make their own sound)."""

    def _click(self, square, select, origin=None):
        session = self.run.battle
        if not select and session is not None and session.outcome is None:
            col, row = parse_square(square)
            if session.game.board.piece_at(col, row) is None:
                mover = session.game.turns.current
                mt.DIRECTOR.sfx("move" if mover == "white" else "move_enemy", 0.9)
        super()._click(square, select, origin)


def board_frame(stage, camera, t, game_dt, game_time, auras=0.8, desat=0.0, bright=1.0) -> pygame.Surface:
    _FROM_BOARD[0] = True
    return mt.render_stage(stage, camera, t, game_dt, game_time, auras=auras, desat=desat, bright=bright, warm=0.2)


def callout(frame, camera, square, text, t, start, end, size=58, offset=(170, -130), kind="burgundy") -> None:
    if not (start <= t <= end + 0.2):
        return
    x, y = camera.map(mt.square_center(square))
    slam(frame, ribbon(text, size, kind), (x + offset[0], y + offset[1]), t, start, end)


# ----------------------------------------------------------------------------------------------- shots

def shot_open() -> None:
    crown = mt.ASSETS.fitted("crown", 520, 460) if mt.ASSETS.has("crown") else None
    line1 = ribbon("YOUR KING", 120, "burgundy")
    line2 = ribbon("has no crown", 84, "parchment")
    mt.FX.clear()
    mt.DIRECTOR.sfx("whoosh", 1.0)

    def step(t, dt):
        frame = pygame.Surface((W, H))
        frame.fill(NIGHT)
        mt.add_glow(frame, (W * 0.5, H * 0.45), 760, (120, 60, 20), 0.5 * mt.ramp(t, 0, BEAT * 2))
        light_sweep(frame, t, seed=4, strength=0.6 * mt.ramp(t, BEAT * 0.5, BEAT * 2))
        if crown is not None:
            k = min(1.0, t / (BAR * 2))
            img = pygame.transform.rotozoom(crown, -16 * k, 1.0 - 0.1 * k)
            img.set_alpha(int(170 * (1 - k * 0.6)))
            frame.blit(img, img.get_rect(center=(W * 0.5, H * 0.3 + 240 * k * k)))
        embers(frame, dt, 26)
        slam(frame, line1, (W * 0.5, H * 0.42), t, BEAT * 1)
        slam(frame, line2, (W * 0.5, H * 0.64), t, BEAT * 3)
        flash(frame, 0.7 * (1 - (t - BEAT) / 0.15) if BEAT <= t < BEAT + 0.15 else 0)
        flash(frame, ((t - (BAR * 2 - 0.12)) / 0.12) if t > BAR * 2 - 0.12 else 0)
        return finish(frame)

    mt.DIRECTOR.sfx("slam", 0.9, at=BEAT * 1)
    mt.DIRECTOR.sfx("slam", 0.8, at=BEAT * 3)
    TIMELINE.run(2, step)


STARTER = (("rook", "A1", None), ("knight", "B1", None), ("queen", "C1", "golden"), ("king", "D1", None),
           ("bishop", "E1", None), ("pawn", "A2", None))


def shot_battle() -> None:
    from config.settings import ENEMY_FORMATIONS, ENEMY_TRAITS
    run = mt.make_run(10, STARTER, ENEMY_FORMATIONS[10], seed=31)
    for piece in run.enemies:  # the stage's own wooden knight
        piece.trait = ENEMY_TRAITS[10].get(f"{'ABCDEF'[piece.col]}{piece.row}")
    stage = Stage(run)
    mt.start(run, stage)
    stage.move(0.30, "C1", "C4", 0.28)
    stage.move(1.15, "B5", "B4", 0.28)
    stage.move(2.05, "C4", "C5", 0.3)
    stage.move(2.95, "E5", "E4", 0.28)
    board = mt.LAYOUT.board
    camera = PunchCamera([(0, board.centerx, board.centery, 1.05), (BAR * 2, board.centerx, board.centery - 40, 1.28)],
                         punches=[2.38])
    tag = ribbon("6 x 6 CHESS", 60, "wood")
    tag2 = ribbon("ROGUELIKE", 74, "burgundy")

    def step(t, dt):
        frame = board_frame(stage, camera, t, dt, t)
        letterbox(frame)
        slam(frame, tag, (W * 0.17, H * 0.3), t, BEAT * 1, BAR * 2 - 0.2)
        slam(frame, tag2, (W * 0.19, H * 0.47), t, BEAT * 2, BAR * 2 - 0.2)
        flash(frame, 0.7 * (1 - t / 0.14) if t < 0.14 else 0)
        return finish(frame)

    mt.DIRECTOR.sfx("slam", 0.6, at=BEAT * 1)
    TIMELINE.run(2, step)


TRAIT_CARDS = (("golden", "queen"), ("ghost", "rook"), ("wanted", "knight"), ("wooden", "bishop"), ("magnet", "knight"), ("explosive", "pawn"))


def shot_specials() -> None:
    images = {trait: special_pieces.image(mt.ASSETS, "white", kind, trait, 470) for trait, kind in TRAIT_CARDS}
    header = ribbon("SPECIAL PIECES", 40, "wood")
    card_rect = pygame.Rect(0, 0, 560, 760)
    card_rect.center = (int(W * 0.29), int(H * 0.53))
    frame_card = style.framed_parchment(mt.ASSETS, card_rect.size, seed=7, border=22)
    mt.FX.clear()

    def step(t, dt):
        index = min(len(TRAIT_CARDS) - 1, int(t / (BEAT * 2)))
        local = t - index * BEAT * 2
        trait, kind = TRAIT_CARDS[index]
        color = mt.TRAIT_COLORS[trait]
        frame = pygame.Surface((W, H))
        backdrop(frame, "wood", 0.6)
        light_sweep(frame, t, seed=10 + index, strength=0.35, color=color)
        # a collector's card: carved frame, parchment, the piece lit by its trait's colour
        k = ease_out_back(min(1.0, local / 0.2))
        style.drop_shadow(frame, card_rect, offset=14, spread=22, alpha=160)
        frame.blit(frame_card, card_rect.move(int(-50 * (1 - k)), 0))
        inner = card_rect.inflate(-80, -80).move(int(-50 * (1 - k)), 0)
        mt.add_glow(frame, inner.center, 330, color, 0.75)
        img = images[trait]
        bob = math.sin(local * 8) * 5
        frame.blit(img, img.get_rect(center=(inner.centerx, inner.centery + 10 + bob)))
        name = ribbon(trait.upper(), 120, "burgundy")
        slam(frame, name, (W * 0.71, H * 0.4), local, 0.02)
        description = trait_by_id(trait).description
        slip_font = style.body_font(34, italic=True)
        lines = style.wrap(slip_font, description, 640)
        slip = pygame.Rect(0, 0, 720, 44 + 46 * len(lines))
        slip.center = (int(W * 0.71), int(H * 0.66))
        if local > 0.12:
            style.draw_parchment(frame, mt.ASSETS, slip, seed=index, shadow=True)
            for i, line in enumerate(lines):
                style.text(frame, line, slip_font, INK, center=(slip.centerx, slip.top + 42 + i * 46))
            pygame.draw.line(frame, color, (slip.left + 40, slip.bottom - 14), (slip.right - 40, slip.bottom - 14), 3)
        frame.blit(header, (40, 40))
        embers(frame, dt, 10)
        flash(frame, 0.7 * (1 - local / 0.1) if local < 0.1 else 0)
        return finish(frame)

    for i in range(len(TRAIT_CARDS)):
        mt.DIRECTOR.sfx("slam", 0.5, at=i * BEAT * 2)
    TIMELINE.run(3, step)


def shot_explosion() -> None:
    army = (("king", "D1", None), ("pawn", "D3", "explosive"), ("pawn", "B2", "golden"), ("rook", "A1", "ghost"))
    run = mt.make_run(20, army, (("queen", "D6"), ("pawn", "C5"), ("pawn", "E5")), seed=33)
    stage = Stage(run)
    mt.start(run, stage, banner=False)
    stage.move(0.05, "B2", "B3", 0.2)
    stage.move(0.45, "D6", "D3", 0.3)
    cx, cy = mt.square_center("D4")
    camera = PunchCamera([(0, cx, cy, 1.45), (BAR, cx, cy, 1.7)], punches=[0.92])
    clock = mt.SlowMo([(0, 1.0), (0.9, 1.0), (1.0, 0.3), (1.6, 0.3), (1.8, 1.0)])
    boom = ribbon("BOOM!", 150, "burgundy")

    def step(t, dt):
        game_dt = clock.advance(t, dt)
        frame = board_frame(stage, camera, t, game_dt, clock.time, auras=1.0)
        letterbox(frame)
        slam(frame, boom, (W * 0.68, H * 0.34), t, 0.95)
        flash(frame, 0.55 * (1 - (t - 0.92) / 0.2) if 0.92 <= t < 1.12 else 0, (255, 200, 140))
        return finish(frame)

    mt.DIRECTOR.sfx("slam", 0.7, at=0.95)
    TIMELINE.run(1, step)


RELIC_CARDS = ("recruitment", "squire", "crowns_blessing")


def shot_relic_cards() -> None:
    renderer = RelicCardRenderer()
    cards = []
    for relic_id in RELIC_CARDS:
        surface = pygame.Surface((330, 495), pygame.SRCALPHA)
        renderer.draw(surface, mt.ASSETS, relic_by_id(relic_id), surface.get_rect())
        cards.append(surface)
    title = ribbon("RELICS", 150, "burgundy")
    sub = ribbon("stack them", 70, "parchment")
    spots = [(W * 0.3, H * 0.56, 9), (W * 0.5, H * 0.52, 0), (W * 0.7, H * 0.56, -9)]
    mt.FX.clear()

    def step(t, dt):
        frame = pygame.Surface((W, H))
        backdrop(frame, "velvet", 0.25)
        light_sweep(frame, t, seed=52, strength=0.7)
        for i, (card, (x, y, angle)) in enumerate(zip(cards, spots)):
            start = BEAT * i
            if t < start:
                continue
            k = ease_out_back(min(1.0, (t - start) / 0.22))
            py = y + (1 - k) * 700
            img = pygame.transform.rotozoom(card, angle * k, 1.0)
            mt.add_glow(frame, (x, py), 310, CANDLE, 0.5)
            style.drop_shadow(frame, img.get_rect(center=(x, py)), offset=12, spread=18, alpha=150)
            frame.blit(img, img.get_rect(center=(x, py)))
        slam(frame, title, (W * 0.5, H * 0.17), t, BEAT * 3)
        slam(frame, sub, (W * 0.5, H * 0.9), t, BEAT * 5)
        embers(frame, dt, 18)
        flash(frame, 0.7 * (1 - t / 0.12) if t < 0.12 else 0)
        return finish(frame)

    for i in range(3):
        mt.DIRECTOR.sfx("whoosh", 0.5, at=BEAT * i)
    mt.DIRECTOR.sfx("slam", 1.0, at=BEAT * 3)
    mt.DIRECTOR.sfx("slam", 0.8, at=BEAT * 5)
    TIMELINE.run(2, step)


def shot_relics_fire() -> None:
    army = (("king", "D1", None), ("knight", "C3", None), ("rook", "A1", None), ("bishop", "F1", None))
    enemies = (("pawn", "D5"), ("pawn", "B5"), ("knight", "E6"), ("rook", "A6"))
    run = mt.make_run(12, army, enemies, relics=("squire", "squire", "recruitment"), seed=34)
    stage = Stage(run)
    mt.start(run, stage, banner=False)
    stage.move(0.35, "C3", "D5", 0.35)
    stage.move(2.3, "E6", "C5", 0.3)
    cx, cy = mt.square_center("D4")
    camera = PunchCamera([(0, mt.LAYOUT.board.centerx, mt.LAYOUT.board.centery, 1.15), (0.8, cx, cy - 20, 1.55),
                          (2.2, cx, cy - 20, 1.6), (BAR * 2, mt.LAYOUT.board.centerx, mt.LAYOUT.board.centery - 80, 1.25)],
                         punches=[0.75])
    clock = mt.SlowMo([(0, 1.0), (0.75, 1.0), (0.85, 0.4), (2.0, 0.4), (2.3, 1.0)])

    def step(t, dt):
        game_dt = clock.advance(t, dt)
        frame = board_frame(stage, camera, t, game_dt, clock.time, auras=0.6)
        letterbox(frame)
        callout(frame, camera, "C4", "SQUIRE x2", t, 0.85, BAR * 2 - 0.3, size=72, offset=(360, -240))
        callout(frame, camera, "C3", "RECRUITED", t, 1.35, BAR * 2 - 0.3, size=72, offset=(-360, 150))
        return finish(frame)

    mt.DIRECTOR.sfx("slam", 0.6, at=0.85)
    mt.DIRECTOR.sfx("slam", 0.6, at=1.35)
    TIMELINE.run(2, step)


def shot_stages() -> None:
    layout = build_layout(W, H)
    boards = {}
    for level in (5, 10, 15, 20, 25, 30):
        run = mt.RunState(1)
        run.level = level
        run.prepare_level()
        scene = DeploymentScene()
        bar = RelicBar()
        bar.bind(run)
        scene.draw(mt.SCREEN, mt.ASSETS, run, layout, bar)
        board = mt.SCREEN.subsurface(layout.board).copy()
        boards[level] = pygame.transform.smoothscale(board, (620, 620))
    from game.level_manager import describe_counts, formation_counts

    order = list(boards)
    mt.FX.clear()

    def step(t, dt):
        index = min(len(order) - 1, int(t / (BEAT * 2)))
        local = t - index * BEAT * 2
        level = order[index]
        frame = pygame.Surface((W, H))
        backdrop(frame, "wood", 0.62)
        light_sweep(frame, t, seed=70 + index, strength=0.4)
        k = ease_out_back(min(1.0, local / 0.18))
        board_rect = boards[level].get_rect(center=(int(W * 0.29), int(H * 0.52) + int(40 * (1 - k))))
        frame_rect = board_rect.inflate(46, 46)
        style.draw_wood_panel(frame, frame_rect, seed=level, shadow=True)
        frame.blit(boards[level], board_rect)
        number = ribbon(f"STAGE {level}", 112, "burgundy")
        slam(frame, number, (W * 0.71, H * 0.4), local, 0.0)
        army = describe_counts(formation_counts(level))
        if local > 0.1:
            style.text(frame, army, style.body_font(36, italic=True), IVORY, shadow=(0, 0, 0, 220), center=(W * 0.71, H * 0.58))
            style.ornament_rule(frame, (int(W * 0.71), int(H * 0.63)), 520, style.GOLD)
        if index == len(order) - 1 and local > BEAT:
            slam(frame, ribbon("thirty stages", 64, "parchment"), (W * 0.71, H * 0.8), local, BEAT)
        embers(frame, dt, 8)
        flash(frame, 0.6 * (1 - local / 0.08) if local < 0.08 else 0)
        return finish(frame)

    for i in range(6):
        mt.DIRECTOR.sfx("slam", 0.5, at=i * BEAT * 2)
    TIMELINE.run(3, step)


def shot_defeat() -> None:
    army = (("king", "D2", None), ("rook", "A1", None), ("pawn", "C2", None), ("bishop", "F1", None))
    enemies = (("pawn", "A5"), ("knight", "E4"), ("rook", "F6"), ("pawn", "C5"))
    run = mt.make_run(17, army, enemies, seed=35)
    stage = Stage(run)
    mt.start(run, stage, banner=False)
    stage.move(0.4, "A1", "A5", 0.3)
    stage.move(1.3, "E4", "D2", 0.6)
    kx, ky = mt.square_center("D2")
    from scenes.result_scene import _banner_panel

    panel = _banner_panel((W, H), run, "defeat", 1.0)
    # after the fall the camera settles on the Game Over panel, so "Fell at Stage 17 of 30" reads clearly
    camera = PunchCamera([(0, mt.LAYOUT.board.centerx, mt.LAYOUT.board.centery, 1.1), (1.6, kx, ky - 40, 1.7),
                          (3.4, kx, ky - 60, 1.95), (4.2, panel.centerx, panel.centery - 40, 1.45),
                          (BAR * 4, panel.centerx, panel.centery - 40, 1.55)],
                         punches=[2.0])
    clock = mt.SlowMo([(0, 1.0), (1.85, 1.0), (2.0, 0.2), (3.2, 0.2), (4.0, 1.0)])
    game_over = ribbon("THE KING HAS FALLEN", 92, "wood")
    fell = ribbon("fell at stage 17", 64, "parchment")
    state = {"hit": False}

    def step(t, dt):
        game_dt = clock.advance(t, dt)
        if run.phase == "defeat" and not state["hit"]:
            state["hit"] = True
            mt.FX.glow((kx, ky), 300, (200, 40, 24), life=1.5, grow=0.3)
        frame = board_frame(stage, camera, t, game_dt, clock.time)
        ember_wash(frame, 0.85 * mt.ramp(t, 2.0, 3.2))
        letterbox(frame)
        slam(frame, game_over, (W * 0.5, H * 0.17), t, 4.0)
        slam(frame, fell, (W * 0.5, H * 0.85), t, 4.0 + BEAT * 2)
        flash(frame, 0.5 * (1 - (t - 2.0) / 0.25) if 2.0 <= t < 2.25 else 0, (200, 60, 30))
        mt.fade(frame, mt.ramp(t, BAR * 4 - 0.25, BAR * 4))
        return finish(frame)

    mt.DIRECTOR.sfx("slam", 1.0, at=4.0)
    mt.DIRECTOR.sfx("slam", 0.7, at=4.0 + BEAT * 2)
    TIMELINE.run(4, step)


def shot_rise_again() -> None:
    line1 = ribbon("RISE", 170, "burgundy")
    line2 = ribbon("AGAIN", 170, "burgundy")
    mt.FX.clear()

    def step(t, dt):
        frame = pygame.Surface((W, H))
        frame.fill(NIGHT)
        mt.add_glow(frame, (W / 2, H * 0.6), 820, (150, 70, 20), 0.35 + 0.4 * mt.ramp(t, BEAT * 2, BAR))
        light_sweep(frame, t, seed=112, strength=mt.ramp(t, BEAT * 2, BAR))
        embers(frame, dt, 30 + 160 * mt.ramp(t, BEAT * 2, BAR))
        slam(frame, line1, (W * 0.5, H * 0.36), t, BEAT * 0.2)
        slam(frame, line2, (W * 0.5, H * 0.62), t, BEAT * 2)
        flash(frame, (t - (BAR - 0.1)) / 0.1 if t > BAR - 0.1 else 0)
        return finish(frame)

    mt.DIRECTOR.sfx("slam", 0.8, at=BEAT * 0.2)
    mt.DIRECTOR.sfx("slam", 1.0, at=BEAT * 2)
    mt.DIRECTOR.sfx("riser", 1.0, at=0.0)
    TIMELINE.run(1, step)


def _montage_cut(run, stage, camera, lines, clock=None, auras=1.0):
    def step(t, dt):
        game_dt = clock.advance(t, dt) if clock else dt
        frame = board_frame(stage, camera, t, game_dt, clock.time if clock else t, auras=auras)
        letterbox(frame)
        for square, text, start in lines:
            callout(frame, camera, square, text, t, start, BAR - 0.15, size=78)
        flash(frame, 0.6 * (1 - t / 0.1) if t < 0.1 else 0)
        return finish(frame)

    return step


def shot_montage() -> None:
    # 1. Crown's Blessing at battle start
    army = (("king", "C1", None), ("pawn", "C2", None), ("knight", "B1", None), ("bishop", "D1", None), ("rook", "F1", None))
    run = mt.make_run(13, army, (("pawn", "B5"), ("pawn", "D5"), ("bishop", "B6"), ("queen", "D6")),
                      relics=("crowns_blessing",), seed=5)
    stage = Stage(run)
    state = {"go": False}
    camera = PunchCamera([(0, *mt.square_center("C2"), 1.8), (BAR, *mt.square_center("C2"), 2.0)], punches=[0.25])

    def blessing(t, dt):
        if t >= 0.2 and not state["go"]:
            state["go"] = True
            mt.start(run, stage)
        return _montage_cut(run, stage, camera, [("C2", "BLESSED", 0.4)])(t, dt)

    mt.DIRECTOR.sfx("slam", 0.5, at=0.4)
    TIMELINE.run(1, blessing)

    # 2. a wanted enemy pays out
    army = (("king", "D1", None), ("bishop", "B2", None), ("rook", "F1", None))
    run = mt.make_run(16, army, (("knight", "E5"), ("pawn", "A5"), ("pawn", "F5")), seed=6)
    run.enemies[0].trait = "wanted"
    stage = Stage(run)
    mt.start(run, stage, banner=False)
    stage.move(0.1, "B2", "E5", 0.3)
    camera = PunchCamera([(0, *mt.square_center("D4"), 1.5), (BAR, *mt.square_center("E5"), 1.75)], punches=[0.42])
    mt.DIRECTOR.sfx("coin", 1.0, at=0.5)
    mt.DIRECTOR.sfx("slam", 0.5, at=0.5)
    TIMELINE.run(1, _montage_cut(run, stage, camera, [("E5", "BOUNTY +2", 0.5)]))

    # 3. Conversion: the bishop's victim rises as a ghost
    army = (("king", "D1", None), ("bishop", "C1", None), ("rook", "A1", None))
    run = mt.make_run(18, army, (("knight", "E3"), ("pawn", "B5"), ("pawn", "F5")), relics=("conversion",), seed=7)
    stage = Stage(run)
    mt.start(run, stage, banner=False)
    stage.move(0.1, "C1", "E3", 0.3)
    camera = PunchCamera([(0, *mt.square_center("E3"), 1.6), (BAR, *mt.square_center("E3"), 1.85)], punches=[0.42])
    mt.DIRECTOR.sfx("slam", 0.5, at=0.5)
    TIMELINE.run(1, _montage_cut(run, stage, camera, [("E3", "CONVERTED", 0.5)]))

    # 4. the golden queen sweeps a file
    army = (("king", "D1", None), ("queen", "A2", "golden"), ("rook", "F1", "ghost"), ("knight", "B1", "magnet"))
    run = mt.make_run(22, army, (("rook", "A6"), ("pawn", "C5"), ("bishop", "B6"), ("knight", "D6")), seed=8)
    stage = Stage(run)
    mt.start(run, stage, banner=False)
    stage.move(0.1, "A2", "A6", 0.3)
    camera = PunchCamera([(0, *mt.square_center("A4"), 1.6), (BAR, *mt.square_center("A5"), 1.9)], punches=[0.42])
    mt.DIRECTOR.sfx("slam", 0.5, at=0.5)
    TIMELINE.run(1, _montage_cut(run, stage, camera, [("A6", "NO MERCY", 0.5)]))


def shot_victory():
    army = (("king", "D1", None), ("queen", "D2", "golden"), ("rook", "A1", "ghost"), ("knight", "E3", "wanted"),
            ("bishop", "F1", "magnet"), ("pawn", "C2", "wooden"))
    run = mt.make_run(MAX_LEVEL, army, (("queen", "D6"),), relics=("crowns_blessing", "squire", "squire", "recruitment"), seed=9)
    run.battles_won = MAX_LEVEL - 1
    run.gold_earned = 214
    run.pieces_lost = 11
    stage = Stage(run)
    mt.start(run, stage, banner=False)
    stage.move(0.25, "D2", "D6", 0.55)
    kx, ky = mt.square_center("D6")
    camera = PunchCamera([(0, mt.LAYOUT.board.centerx, mt.LAYOUT.board.centery, 1.15), (0.7, kx, ky + 140, 1.7),
                          (1.6, kx, ky + 60, 1.9), (2.4, W / 2, H / 2, 1.0), (BAR * 3, W / 2, H / 2, 1.02)], punches=[0.86])
    clock = mt.SlowMo([(0, 1.0), (0.8, 1.0), (0.9, 0.3), (1.8, 0.3), (2.2, 1.0)])
    victory = ribbon("VICTORY", 170, "burgundy")
    state = {"done": False}

    def step(t, dt):
        game_dt = clock.advance(t, dt)
        if run.phase == "victory" and not state["done"]:
            state["done"] = True
            mt.FX.holy((kx, ky), (255, 220, 140), big=True)
            mt.FX.explosion((kx, ky))
        frame = board_frame(stage, camera, t, game_dt, clock.time, auras=1.0)
        if t > 0.9:
            god_rays(frame, (W * 0.5, H * 0.2), t, 0.9 * mt.ramp(t, 0.9, 1.3))
        letterbox(frame)
        slam(frame, victory, (W * 0.5, H * 0.2), t, 0.92)
        flash(frame, 0.75 * (1 - (t - 0.88) / 0.3) if 0.88 <= t < 1.18 else 0)
        mt.fade(frame, mt.ramp(t, BAR * 3 - 0.15, BAR * 3), WARM_FLASH)
        return finish(frame)

    mt.DIRECTOR.sfx("slam", 1.0, at=0.92)
    mt.DIRECTOR.sfx("victory", 0.9, at=1.0)
    TIMELINE.run(3, step)
    return run, stage


def shot_crowned(run, stage) -> None:
    run.continue_from_victory()
    win_screen.update(0.0, run)
    camera = mt.Camera([(0, W / 2, H / 2 - 30, 1.1), (BAR * 2, W / 2, H / 2, 1.0)])
    words = ribbon("the crown is yours", 70, "parchment")

    def step(t, dt):
        frame = board_frame(stage, camera, t, dt, t)
        slam(frame, words, (W * 0.5, H * 0.88), t, BEAT * 3)
        flash(frame, 1 - t / 0.25 if t < 0.25 else 0)
        return finish(frame)

    mt.DIRECTOR.sfx("slam", 0.8, at=BEAT * 3)
    TIMELINE.run(2, step)


def shot_title() -> None:
    logo = mt.ASSETS.fitted("crownless_logo", 1150, 440) if mt.ASSETS.has("crownless_logo") else None
    tagline = ribbon("TAKE BACK THE CROWN", 66, "burgundy")
    soon = engraved("Coming Soon", 44, "ivory", italic=True)
    mt.FX.clear()

    def step(t, dt):
        frame = pygame.Surface((W, H))
        frame.fill(NIGHT)
        god_rays(frame, (W / 2, H * 0.38), t, 0.55 * mt.ramp(t, 0, 0.5))
        mt.add_glow(frame, (W / 2, H * 0.4), 640, (150, 70, 20), 0.6)
        light_sweep(frame, t, seed=152, strength=0.5 * (1 - mt.ramp(t, BEAT * 2, BAR * 2)))
        embers(frame, dt, 24)
        if logo is not None:
            k = ease_out_back(min(1.0, t / 0.3))
            img = pygame.transform.rotozoom(logo, 0, 0.7 + 0.3 * k + 0.03 * t / (BAR * 4))
            frame.blit(img, img.get_rect(center=(W / 2, H * 0.38)))
        slam(frame, tagline, (W / 2, H * 0.7), t, BEAT * 2)
        if t > BAR * 2:
            soon.set_alpha(int(255 * mt.ramp(t, BAR * 2, BAR * 2 + 0.4)))
            frame.blit(soon, soon.get_rect(center=(W / 2, H * 0.84)))
            style.ornament_rule(frame, (W // 2, int(H * 0.89)), 420, style.GOLD)
        flash(frame, 1 - t / 0.2 if t < 0.2 else 0)
        mt.fade(frame, mt.ramp(t, BAR * 4 - 0.9, BAR * 4))
        return finish(frame)

    mt.DIRECTOR.sfx("slam", 1.0, at=0.0)
    mt.DIRECTOR.sfx("slam", 0.8, at=BEAT * 2)
    TIMELINE.run(4, step)


def shot_victory_and_crown() -> None:
    run, stage = shot_victory()
    shot_crowned(run, stage)


SHOTS = [
    ("open", shot_open, 2),
    ("battle", shot_battle, 2),
    ("specials", shot_specials, 3),
    ("explosion", shot_explosion, 1),
    ("relic cards", shot_relic_cards, 2),
    ("relics fire", shot_relics_fire, 2),
    ("stages", shot_stages, 3),
    ("defeat", shot_defeat, 4),
    ("rise again", shot_rise_again, 1),
    ("montage", shot_montage, 4),
    ("victory + crown", shot_victory_and_crown, 5),
    ("title", shot_title, 4),
]
MUSIC_DROP = (sum(b for _n, _s, b in SHOTS[:7]), sum(b for _n, _s, b in SHOTS[:9]))  # bars without music (defeat)


# ----------------------------------------------------------------------------------------------- sound

SR = 44100


def load_wav(path: Path) -> np.ndarray:
    with wave.open(str(path)) as handle:
        data = np.frombuffer(handle.readframes(handle.getnframes()), "<i2").astype(np.float32) / 32768
        channels = handle.getnchannels()
    data = data.reshape(-1, channels)
    return data if channels == 2 else np.repeat(data, 2, axis=1)


def load_ogg(path: Path, ffmpeg: str) -> np.ndarray:
    raw = subprocess.run([ffmpeg, "-loglevel", "error", "-i", str(path), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, "<f4").reshape(-1, 2).copy()


def synth(kind: str) -> np.ndarray:
    rng = np.random.default_rng(len(kind))
    if kind == "slam":
        t = np.arange(int(0.6 * SR)) / SR
        freq = 45 + 80 * np.exp(-t / 0.03)
        body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t / 0.18)
        crack = rng.standard_normal(len(t)) * np.exp(-t / 0.02) * 0.6
        out = body + crack
    elif kind == "whoosh":
        t = np.arange(int(0.45 * SR)) / SR
        noise = np.convolve(rng.standard_normal(len(t)), np.ones(24) / 24, mode="same")
        out = noise * np.sin(np.pi * t / t[-1]) ** 2 * 3.0
    elif kind == "riser":
        t = np.arange(int(BAR * SR)) / SR
        k = t / t[-1]
        noise = np.convolve(rng.standard_normal(len(t)), np.ones(6) / 6, mode="same")
        tone = np.sin(2 * np.pi * np.cumsum(180 + 900 * k ** 2) / SR)
        out = (noise * 0.6 + tone * 0.25) * k ** 2.2
    else:
        out = np.zeros(1)
    out = out / (np.max(np.abs(out)) + 1e-9)
    return np.repeat(out[:, None], 2, axis=1).astype(np.float32)


SOUND_FILES = {"hit": "capture", "boom": "explosion", "chime": "relic", "move": "move", "move_enemy": "move_enemy",
               "tick": "move", "coin": "coin", "victory": "victory", "defeat": "defeat", "spawn": "spawn",
               "impact": None, "slam": None, "whoosh": None, "riser": None}
LANDING = 0.16  # moves and captures sound when the piece lands, after its travel animation


def mix_audio(length: float, sounds, path: Path, ffmpeg: str) -> None:
    audio_dir = ROOT / "assets" / "audio"
    total = int((length + 1.0) * SR)
    out = np.zeros((total, 2), np.float32)
    track = load_ogg(audio_dir / "theme_battle.ogg", ffmpeg)
    drop_start, drop_end = MUSIC_DROP[0] * BAR, MUSIC_DROP[1] * BAR

    def place(at: float, clip: np.ndarray, gain: float) -> None:
        i = int(at * SR)
        if i >= total or i < 0:
            return
        j = min(total, i + len(clip))
        out[i:j] += clip[: j - i] * gain

    # music: the track from the top until the defeat, silence through it, then the melody section to the end
    music = np.zeros_like(out)
    first = track[: int(drop_start * SR)].copy()
    fade = int(0.35 * SR)
    first[-fade:] *= np.linspace(1, 0, fade)[:, None]
    music[: len(first)] += first
    resume = int(16 * BAR * SR)  # bar 17 of the theme: the melody and claps come in
    rest = track[resume: resume + total - int(drop_end * SR)].copy()
    rest[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))[:, None]
    music[int(drop_end * SR): int(drop_end * SR) + len(rest)] += rest
    end_fade = int(1.6 * SR)
    stop = int(length * SR)
    music[stop - end_fade: stop] *= np.linspace(1, 0, end_fade)[:, None]
    music[stop:] = 0
    out += music * 0.75

    clips: dict[str, np.ndarray] = {}
    for at, kind, strength in sounds:
        name = SOUND_FILES.get(kind, kind)
        if kind not in clips:
            clips[kind] = synth(kind) if name is None else load_wav(audio_dir / f"{name}.wav")
        delay = LANDING if kind in ("hit", "boom", "move", "move_enemy", "chime") else 0.0
        gain = {"slam": 0.75, "whoosh": 0.35, "riser": 0.5, "victory": 0.9, "defeat": 1.0}.get(kind, 0.8) * strength
        place(at + delay, clips[kind], gain)
    # the defeat: a low stinger as the king falls
    place(drop_start + 2.0, load_wav(audio_dir / "defeat.wav"), 0.9)

    peak = float(np.max(np.abs(out))) or 1.0
    out = np.tanh(out / peak * 1.6) * 0.9
    pcm = (out * 32767).astype("<i2")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(SR)
        handle.writeframes(pcm.tobytes())


# ----------------------------------------------------------------------------------------------- main

class Director(mt.Director):
    def sfx(self, kind: str, strength: float = 1.0, at: float | None = None) -> None:
        """at: seconds into the segment about to run (shots book their cue sounds just before TIMELINE.run)."""
        when = self.time if at is None else self.time + at
        self.sounds.append((when, kind, strength))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=str(ROOT / "dist" / "crownless_trailer_60s.mp4"))
    parser.add_argument("--only", default="")
    parser.add_argument("--stills", type=float, default=0.0)
    parser.add_argument("--still-dir", default=str(ROOT / "dist" / "trailer60_stills"))
    args = parser.parse_args()
    only = {int(x) for x in args.only.split(",") if x.strip()}
    still_dir = Path(args.still_dir) if args.stills > 0 else None
    if still_dir is not None:
        still_dir.mkdir(parents=True, exist_ok=True)
    out = None if only else Path(args.out)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
    director = Director(out, args.stills, still_dir)
    mt.DIRECTOR = director
    for index, (name, shot, bars) in enumerate(SHOTS, start=1):
        if only and index not in only:
            TIMELINE.bar += bars
            continue
        began = director.time
        shot()
        print(f"shot {index:2d} {name:<16} {began:6.2f}s -> {director.time:6.2f}s", flush=True)
    director.finish()
    if out is None:
        return
    audio = out.with_suffix(".wav")
    mix_audio(director.time, director.sounds, audio, director.ffmpeg)
    subprocess.run([director.ffmpeg, "-y", "-loglevel", "error", "-i", str(director.video_tmp), "-i", str(audio),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], check=True)
    director.video_tmp.unlink(missing_ok=True)
    audio.unlink(missing_ok=True)
    print(f"done: {out} ({director.time:.1f}s)")


if __name__ == "__main__":
    main()
