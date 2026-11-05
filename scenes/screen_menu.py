import pygame

from rendering import audio as audio_module
from rendering import style
from rendering.hud_renderer import _blit_text, draw_button, get_font
from rendering.layout import Layout
from rendering.trait_style import trait_style
from rendering.ui_sounds import ui_sounds


class ScreenMenu:
    def __init__(self) -> None:
        self.mode = ""
        self.press: tuple[int, int] | None = None

    def hit_button(self, layout: Layout, pos: tuple[int, int]) -> bool:
        return layout.menu.collidepoint(pos) or layout.options.collidepoint(pos)

    def on_press(self, layout: Layout, pos: tuple[int, int]) -> bool:
        if self.mode:
            self.press = pos
            return True
        if self.hit_button(layout, pos):
            self.press = pos
            return True
        return False

    def on_release(self, pos: tuple[int, int], window: tuple[int, int], layout: Layout) -> str | None:
        if self.mode:
            action = self._overlay_action(pos, window)
            self.press = None
            return action
        if self.press is None:
            return None
        self.press = None
        if layout.menu.collidepoint(pos):
            self.mode = "menu"
            return "open"
        if layout.options.collidepoint(pos):
            self.mode = "options"
            return "open"
        return None

    def _overlay_action(self, pos: tuple[int, int], window: tuple[int, int]) -> str:
        panel, buttons = _geometry(window, self.mode)
        if not panel.collidepoint(pos):
            self.mode = ""
            return "close"
        for name, rect in buttons:
            if rect.collidepoint(pos):
                if name == "cancel" or name == "close":
                    self.mode = ""
                    return "close"
                if name == "restart":
                    self.mode = ""
                    return "restart"
                if name == "main_menu":
                    self.mode = ""
                    return "main_menu"
                if name == "readability":
                    trait_style.toggle()
                    return "readability"
                if name in AUDIO_BUTTONS:
                    kind, sign = AUDIO_BUTTONS[name]
                    if kind == "music":
                        audio_module.audio.change_music(sign * audio_module.STEP)
                    else:
                        audio_module.audio.change_sound(sign * audio_module.STEP)
                    return "audio"
        return "block"

    def draw(self, screen: pygame.Surface) -> None:
        if not self.mode:
            return
        shade = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        shade.fill((20, 12, 8, 120))
        screen.blit(shade, (0, 0))
        ui_sounds.modal()  # the panel takes every click; buttons underneath stay quiet
        panel, buttons = _geometry(screen.get_size(), self.mode)
        style.drop_shadow(screen, panel, offset=10, spread=18, alpha=150)
        screen.blit(style.framed_parchment(None, panel.size, seed=11, border=12), panel.topleft)
        if self.mode == "menu":
            style.text(screen, "Main Menu", style.title_font(28, bold=True), style.INK, center=(panel.centerx, panel.y + 46))
            style.text(screen, "Leave this run, or start it over?", style.body_font(18), style.INK_SOFT, center=(panel.centerx, panel.y + 84))
        else:
            state = "On" if trait_style.strong else "Off"
            style.text(screen, "Options", style.title_font(28, bold=True), style.INK, center=(panel.centerx, panel.y + 46))
            sound = audio_module.audio
            rows = audio_rows(panel)
            for kind, label, value in (("music", "Music", sound.music_volume), ("sound", "Sound", sound.sound_volume)):
                row = rows[kind]
                style.text(screen, label, style.title_font(20, bold=True), style.INK, midleft=(row.x, row.centery))
                _draw_volume(screen, volume_bar(row), value)
            style.text(screen, f"Strong piece marks  {state}", style.body_font(17), style.INK_SOFT, center=(panel.centerx, rows["sound"].bottom + 30))
        for name, rect in buttons:
            label = BUTTON_LABELS[name]
            draw_button(screen, rect, label, font_size=22 if name in AUDIO_BUTTONS else 18)


BUTTON_LABELS = {
    "restart": "Restart Run", "cancel": "Cancel", "readability": "Piece Marks", "close": "Close", "main_menu": "Main Menu",
    "music-": "-", "music+": "+", "sound-": "-", "sound+": "+",
}
BUTTON_MARGIN = 24  # space between the lowest button and the panel's bottom edge
BUTTON_GAP = 10
AUDIO_BUTTONS = {"music-": ("music", -1), "music+": ("music", 1), "sound-": ("sound", -1), "sound+": ("sound", 1)}


def audio_rows(panel: pygame.Rect) -> dict[str, pygame.Rect]:
    width = panel.w - 64
    music = pygame.Rect(panel.x + 32, panel.y + 86, width, 40)
    sound = pygame.Rect(panel.x + 32, music.bottom + 14, width, 40)
    return {"music": music, "sound": sound}


def volume_bar(row: pygame.Rect) -> pygame.Rect:
    """The ten-step meter between the - and + buttons."""
    return pygame.Rect(row.x + 128, row.y + 11, row.w - 128 - 104, 18)


def _draw_volume(screen: pygame.Surface, bar: pygame.Rect, value: float) -> None:
    steps = 10
    gap = 4
    width = (bar.w - gap * (steps - 1)) / steps
    lit = int(round(value * steps))
    for i in range(steps):
        cell = pygame.Rect(int(bar.x + i * (width + gap)), bar.y, max(2, int(width)), bar.h)
        color = style.GOLD if i < lit else (150, 128, 96)
        pygame.draw.rect(screen, color, cell, border_radius=3)
        pygame.draw.rect(screen, style.INK_SOFT, cell, width=1, border_radius=3)
    label = "Off" if lit == 0 else f"{lit * 10}%"
    style.text(screen, label, style.body_font(15, bold=True), style.INK, midleft=(bar.right + 8, bar.centery))


def _geometry(window: tuple[int, int], mode: str) -> tuple[pygame.Rect, list[tuple[str, pygame.Rect]]]:
    height = 300 if mode == "menu" else 370
    panel = pygame.Rect(0, 0, min(460 if mode != "menu" else 420, window[0] - 48), height)
    panel.center = (window[0] // 2, window[1] // 2)
    width = min(240, panel.w - 48)
    # buttons stack upward from a margin that clears the parchment's 12px frame and its corner studs
    bottom = pygame.Rect(0, 0, width, 42)
    bottom.bottom = panel.bottom - BUTTON_MARGIN
    bottom.centerx = panel.centerx
    top = bottom.move(0, -(bottom.h + BUTTON_GAP))
    if mode == "menu":
        upper = top.move(0, -(top.h + BUTTON_GAP))
        return panel, [("main_menu", upper), ("restart", top), ("cancel", bottom)]
    buttons = [("readability", top), ("close", bottom)]
    rows = audio_rows(panel)
    for kind in ("music", "sound"):
        row = rows[kind]
        bar = volume_bar(row)
        minus = pygame.Rect(0, 0, 36, 34)
        minus.midright = (bar.x - 8, row.centery)
        plus = pygame.Rect(0, 0, 36, 34)
        plus.midleft = (bar.right + 52, row.centery)
        buttons += [(f"{kind}-", minus), (f"{kind}+", plus)]
    return panel, buttons
