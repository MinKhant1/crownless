"""The run-complete celebration: the crown comes back, coins fall, the army that made it stands on show."""

import math
import random
from dataclasses import dataclass

import pygame

from config.settings import CROWN_SOURCE, MAX_LEVEL, RELIC_CARD_HEIGHT, RELIC_CARD_WIDTH
from game.army_roster import sorted_pieces
from game.relics.relic_data import relic_by_id
from game.transitions.easing import ease_out_cubic
from rendering import style
from rendering.asset_manager import AssetManager
from rendering.battle_columns import _gold_icon
from rendering.hud_renderer import draw_background, draw_button
from rendering.piece_visual_effects import draw_contact_shadow, figurines
from rendering.relic_card import RelicCardRenderer

TITLE = "The Crown Reclaimed"
SUBTITLE = "All five battles are won, and the crown is yours again."

# (start, seconds)
CROWN_DROP = (0.0, 1.15)
GLINT = (1.05, 0.7)
PANEL_IN = (0.35, 0.6)
# first and last coin
COINS = (0.25, 2.6)
ARMY_START = 1.0
ARMY_STAGGER = 0.11
STATS_START = 1.5
STATS_STAGGER = 0.22
STATS_COUNT = 0.9
BUTTONS_IN = 1.9
COIN_COUNT = 46
GRAVITY = 1500.0

STAT_ROWS = (
    ("battles", "Battles won"),
    ("gold", "Gold earned"),
    ("relics", "Relics collected"),
    ("lost", "Pieces lost"),
)


@dataclass(frozen=True)
class WinLayout:
    crown: pygame.Rect
    panel: pygame.Rect
    title_y: int
    subtitle_y: int
    rule_y: int
    plinth: pygame.Rect
    ledger: pygame.Rect
    relics: pygame.Rect
    new_run: pygame.Rect
    menu: pygame.Rect


@dataclass(frozen=True)
class Coin:
    x: float
    delay: float
    speed: float
    size: int
    spin: float
    phase: float
    floor: float


def win_layout(window: tuple[int, int]) -> WinLayout:
    """The crown and the panel as one group, centred, with the panel sized to what it holds."""
    width, height = window
    crown_h = max(84, min(136, int(height * 0.15)))
    crown_w = int(round(crown_h * CROWN_SOURCE[0] / CROWN_SOURCE[1]))
    crest = crown_h // 4
    plinth_h = max(64, min(116, int(height * 0.13)))
    ledger_h = max(104, min(148, int(height * 0.16)))
    relics_h = max(88, min(100, int(height * 0.12)))
    head = crest + 36 + 40 + 26 + 14
    foot = 24 + 50 + 24
    panel_h = head + plinth_h + 12 + ledger_h + 12 + relics_h + foot
    room = height - 16 - (crown_h - crest)
    if panel_h > room:
        squeeze = (room - head - foot - 24) / max(1, plinth_h + ledger_h + relics_h)
        plinth_h = max(48, int(plinth_h * squeeze))
        ledger_h = max(88, int(ledger_h * squeeze))
        relics_h = max(72, int(relics_h * squeeze))
        panel_h = head + plinth_h + 12 + ledger_h + 12 + relics_h + foot
    group_top = max(8, (height - (crown_h - crest) - panel_h) // 2)
    crown = pygame.Rect(0, 0, crown_w, crown_h)
    crown.midtop = (width // 2, group_top)
    top = crown.bottom - crest
    panel = pygame.Rect(0, top, min(860, width - 80), panel_h)
    panel.centerx = width // 2
    inner = panel.inflate(-56, -40)
    title_y = top + crest + 36
    subtitle_y = title_y + 40
    rule_y = subtitle_y + 26
    plinth = pygame.Rect(inner.x, rule_y + 14, inner.w, plinth_h)
    ledger = pygame.Rect(0, plinth.bottom + 12, min(520, inner.w), ledger_h)
    ledger.centerx = panel.centerx
    relics = pygame.Rect(inner.x, ledger.bottom + 12, inner.w, relics_h)
    button_w = min(240, (inner.w - 24) // 2)
    new_run = pygame.Rect(0, 0, button_w, 50)
    menu = pygame.Rect(0, 0, button_w, 50)
    new_run.bottomright = (panel.centerx - 12, panel.bottom - 24)
    menu.bottomleft = (panel.centerx + 12, panel.bottom - 24)
    return WinLayout(crown, panel, title_y, subtitle_y, rule_y, plinth, ledger, relics, new_run, menu)


def stat_values(run) -> dict[str, int]:
    return {
        "battles": int(getattr(run, "battles_won", MAX_LEVEL)),
        "gold": int(getattr(run, "gold_earned", 0)),
        "relics": len(run.relics.owned),
        "lost": int(getattr(run, "pieces_lost", 0)),
    }


def shown_values(run, elapsed: float) -> dict[str, int]:
    """Each stat counts up from zero, one after another."""
    shown = {}
    for index, (key, _label) in enumerate(STAT_ROWS):
        amount = ease_out_cubic(_span(elapsed, STATS_START + index * STATS_STAGGER, STATS_COUNT))
        shown[key] = int(round(stat_values(run)[key] * amount))
    return shown


def finished_at(run) -> float:
    army = len(run.army.pieces)
    return max(
        COINS[1] + 1.2,
        ARMY_START + army * ARMY_STAGGER + 0.4,
        STATS_START + len(STAT_ROWS) * STATS_STAGGER + STATS_COUNT,
        BUTTONS_IN + 0.4,
    )


class WinScreen:
    def __init__(self) -> None:
        self.elapsed = 0.0
        self.cards = RelicCardRenderer()
        self._run_key: tuple | None = None
        self._coins: list[Coin] = []
        self._window: tuple[int, int] | None = None

    def update(self, dt: float, run) -> None:
        key = (id(run), run.seed)
        if key != self._run_key:
            self._run_key = key
            self.elapsed = 0.0
            self._window = None
        self.elapsed += max(0.0, dt)

    def buttons(self, window: tuple[int, int]) -> tuple[pygame.Rect, pygame.Rect]:
        places = win_layout(window)
        return places.new_run, places.menu

    def buttons_shown(self) -> bool:
        return self.elapsed >= BUTTONS_IN

    def draw(self, screen: pygame.Surface, assets: AssetManager, run, backdrop: bool = True) -> None:
        window = screen.get_size()
        if (id(run), run.seed) != self._run_key:
            self.update(0.0, run)
        if self._window != window:
            self._window = window
            self._coins = _make_coins(window, run.seed)
        places = win_layout(window)
        t = self.elapsed
        if backdrop:
            draw_background(screen, assets)
        warm = style.candle_glow((int(window[0] * 1.2), int(window[1] * 1.1)), strength=int(70 * ease_out_cubic(_span(t, 0.0, 1.2))))
        screen.blit(warm, warm.get_rect(center=(window[0] // 2, places.crown.bottom)), special_flags=pygame.BLEND_RGB_ADD)
        self._draw_coins(screen, assets, t, window)
        panel_in = ease_out_cubic(_span(t, *PANEL_IN))
        if panel_in > 0:
            self._draw_panel(screen, assets, run, places, panel_in, t)
        self._draw_crown(screen, assets, places, t)

    def _draw_panel(self, screen: pygame.Surface, assets, run, places: WinLayout, amount: float, t: float) -> None:
        panel = places.panel.move(0, int((1.0 - amount) * 30))
        style.drop_shadow(screen, panel, offset=14, spread=26, alpha=int(170 * amount), radius=12)
        sheet = style.framed_parchment(assets, panel.size, seed=31, border=16)
        if amount < 1.0:
            sheet = sheet.copy()
            sheet.set_alpha(int(255 * amount))
        screen.blit(sheet, panel.topleft)
        if amount < 0.6:
            return
        dy = panel.y - places.panel.y
        alpha = int(255 * min(1.0, (amount - 0.6) / 0.4))
        title = style.fitted_title(TITLE, 44, panel.w - 80, bold=True)
        style.text(screen, TITLE, title, style.BURGUNDY_DEEP, shadow=(255, 246, 222, 170), alpha=alpha, center=(panel.centerx, places.title_y + dy))
        subtitle = style.body_font(19, italic=True)
        style.text(screen, SUBTITLE, subtitle, style.INK_SOFT, alpha=alpha, center=(panel.centerx, places.subtitle_y + dy))
        style.ornament_rule(screen, (panel.centerx, places.rule_y + dy), min(460, panel.w - 140), style.GOLD_DIM, alpha=alpha)
        self._draw_army(screen, assets, run, places.plinth.move(0, dy), t)
        self._draw_ledger(screen, run, places.ledger.move(0, dy), t)
        self._draw_relics(screen, assets, run, places.relics.move(0, dy), t)
        if t >= BUTTONS_IN:
            fade = ease_out_cubic(_span(t, BUTTONS_IN, 0.35))
            for rect, label, primary in ((places.new_run, "New Run", True), (places.menu, "Main Menu", False)):
                drawn = rect.move(0, int((1.0 - fade) * 12))
                draw_button(screen, drawn, label, font_size=20, selected=primary and not drawn.collidepoint(_pointer()))

    def _draw_army(self, screen: pygame.Surface, assets, run, area: pygame.Rect, t: float) -> None:
        pieces = sorted_pieces(list(run.army.pieces))
        if not pieces:
            return
        gap = 6
        box = min(area.h - 16, 96)
        while box > 30 and len(pieces) * (box + gap) - gap > area.w - 40:
            box -= 2
        row_w = len(pieces) * (box + gap) - gap
        plinth = pygame.Rect(0, 0, row_w + 48, 16)
        plinth.midbottom = (area.centerx, area.bottom)
        style.drop_shadow(screen, plinth, offset=4, spread=6, alpha=110, radius=4)
        screen.blit(style.plaque(plinth.size, "idle"), plinth.topleft)
        left = area.centerx - row_w // 2
        for index, piece in enumerate(pieces):
            pop = _span(t, ARMY_START + index * ARMY_STAGGER, 0.38)
            if pop <= 0:
                continue
            scale = max(0.05, style.ease_out_back(pop))
            center = (left + index * (box + gap) + box // 2, plinth.top - box // 2 + 4)
            draw_contact_shadow(screen, (center[0], plinth.top + 1), int(box * scale), 0.0)
            image = figurines.image(assets, piece, box)
            if abs(scale - 1.0) > 0.01:
                image = pygame.transform.smoothscale(image, (max(1, int(image.get_width() * scale)), max(1, int(image.get_height() * scale))))
            screen.blit(image, image.get_rect(midbottom=(center[0], plinth.top + 4)))

    def _draw_ledger(self, screen: pygame.Surface, run, area: pygame.Rect, t: float) -> None:
        shown = shown_values(run, t)
        row_h = area.h // len(STAT_ROWS)
        label_font = style.body_font(max(16, min(20, row_h - 12)))
        value_font = style.title_font(max(17, min(23, row_h - 8)), bold=True)
        for index, (key, label) in enumerate(STAT_ROWS):
            start = STATS_START + index * STATS_STAGGER
            if t < start:
                continue
            alpha = int(255 * ease_out_cubic(_span(t, start, 0.25)))
            y = area.y + index * row_h + row_h // 2
            left = style.text(screen, label, label_font, style.INK, alpha=alpha, midleft=(area.x, y))
            value = str(shown[key])
            right = style.text(screen, value, value_font, style.BURGUNDY_DEEP, alpha=alpha, midright=(area.right, y))
            for x in range(left.right + 10, right.left - 8, 7):
                pygame.draw.circle(screen, (172, 140, 96), (x, y + label_font.get_height() // 4), 1)

    def _draw_relics(self, screen: pygame.Surface, assets, run, area: pygame.Rect, t: float) -> None:
        owned = run.ordered_relics()
        start = STATS_START + 2 * STATS_STAGGER
        if not owned or t < start:
            return
        gap = 8
        card_h = max(36, area.h)
        card_w = int(round(card_h * RELIC_CARD_WIDTH / RELIC_CARD_HEIGHT))
        while card_w > 28 and len(owned) * (card_w + gap) - gap > area.w:
            card_w -= 2
            card_h = int(round(card_w * RELIC_CARD_HEIGHT / RELIC_CARD_WIDTH))
        row_w = len(owned) * (card_w + gap) - gap
        left = area.centerx - row_w // 2
        top = area.y + (area.h - card_h) // 2
        for index, item in enumerate(owned):
            appear = ease_out_cubic(_span(t, start + index * 0.06, 0.3))
            if appear <= 0:
                continue
            relic = relic_by_id(item.relic_id)
            if relic is None:
                continue
            rect = pygame.Rect(left + index * (card_w + gap), top + int((1.0 - appear) * 10), card_w, card_h)
            style.drop_shadow(screen, rect, offset=4, spread=5, alpha=int(110 * appear), radius=6)
            face = self.cards.mini_surface(assets, relic, card_w, card_h, "active")
            if appear < 1.0:
                face = face.copy()
                face.set_alpha(int(255 * appear))
            screen.blit(face, rect.topleft)

    def _draw_crown(self, screen: pygame.Surface, assets, places: WinLayout, t: float) -> None:
        if not assets.has("crown"):
            return
        drop = style.ease_out_back(_span(t, *CROWN_DROP), overshoot=0.9)
        rest = places.crown
        y = int(-rest.h * 1.2 + (rest.y + rest.h * 1.2) * drop)
        image = assets.scaled("crown", rest.size)
        glint = _span(t, *GLINT)
        if 0.0 < glint < 1.0:
            flash = math.sin(glint * math.pi)
            image = image.copy()
            image.fill((int(60 * flash), int(48 * flash), int(26 * flash)), special_flags=pygame.BLEND_RGB_ADD)
        screen.blit(image, (rest.x, y))
        if 0.0 < glint < 1.0:
            flash = math.sin(glint * math.pi)
            tip = (rest.x + int(rest.w * 0.15), y + int(rest.h * 0.07))
            style.sparkle(screen, tip, 4 + 12 * flash, int(255 * flash))
            style.sparkle(screen, (rest.x + int(rest.w * 0.62), y + int(rest.h * 0.22)), 2 + 6 * flash, int(200 * flash))

    def _draw_coins(self, screen: pygame.Surface, assets, t: float, window: tuple[int, int]) -> None:
        for coin in self._coins:
            age = t - coin.delay
            if age <= 0:
                continue
            y = -coin.size + coin.speed * age + 0.5 * GRAVITY * age * age
            landed = y >= coin.floor
            y = min(y, coin.floor)
            turn = 1.0 if landed else abs(math.cos(coin.phase + coin.spin * age))
            icon = _gold_icon(assets, coin.size)
            if icon is None:
                continue
            width = max(2, int(icon.get_width() * max(0.18, turn)))
            face = pygame.transform.smoothscale(icon, (width, icon.get_height())) if width != icon.get_width() else icon
            screen.blit(face, face.get_rect(center=(int(coin.x), int(y))))


def _make_coins(window: tuple[int, int], seed: int) -> list[Coin]:
    rng = random.Random(f"win-coins:{seed}")
    width, height = window
    coins = []
    for index in range(COIN_COUNT):
        coins.append(
            Coin(
                x=rng.uniform(width * 0.04, width * 0.96),
                delay=COINS[0] + (COINS[1] - COINS[0]) * index / COIN_COUNT + rng.uniform(-0.08, 0.08),
                speed=rng.uniform(60, 220),
                size=rng.randint(20, 34),
                spin=rng.uniform(6, 12),
                phase=rng.uniform(0, math.pi),
                floor=height - rng.uniform(10, 44),
            )
        )
    return coins


def _span(t: float, start: float, length: float) -> float:
    return max(0.0, min(1.0, (t - start) / max(0.001, length)))


def _pointer() -> tuple[int, int]:
    return pygame.mouse.get_pos() if pygame.display.get_surface() is not None else (-1, -1)


win_screen = WinScreen()
