import pygame

from rendering.hud_renderer import _blit_text, draw_button, get_font
from rendering.layout import Layout
from rendering.trait_style import trait_style


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
                if name == "readability":
                    trait_style.toggle()
                    return "readability"
        return "block"

    def draw(self, screen: pygame.Surface) -> None:
        if not self.mode:
            return
        shade = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        shade.fill((20, 12, 8, 120))
        screen.blit(shade, (0, 0))
        panel, buttons = _geometry(screen.get_size(), self.mode)
        pygame.draw.rect(screen, (48, 30, 20), panel, border_radius=16)
        inner = panel.inflate(-8, -8)
        pygame.draw.rect(screen, (232, 214, 184), inner, border_radius=12)
        pygame.draw.rect(screen, (214, 170, 90), panel, width=2, border_radius=16)
        if self.mode == "menu":
            _blit_text(screen, "Main Menu", get_font(28, bold=True), (62, 40, 28), center=(panel.centerx, panel.y + 48))
            _blit_text(screen, "Restart this run?", get_font(18, bold=False), (92, 64, 42), center=(panel.centerx, panel.y + 86))
        else:
            state = "On" if trait_style.strong else "Off"
            _blit_text(screen, "Options", get_font(28, bold=True), (62, 40, 28), center=(panel.centerx, panel.y + 48))
            _blit_text(screen, f"Strong piece marks  {state}", get_font(18, bold=False), (92, 64, 42), center=(panel.centerx, panel.y + 86))
        for name, rect in buttons:
            label = {"restart": "Restart Run", "cancel": "Cancel", "readability": "Piece Marks", "close": "Close"}[name]
            draw_button(screen, rect, label, font_size=18)


def _geometry(window: tuple[int, int], mode: str) -> tuple[pygame.Rect, list[tuple[str, pygame.Rect]]]:
    panel = pygame.Rect(0, 0, min(420, window[0] - 48), 230)
    panel.center = (window[0] // 2, window[1] // 2)
    width = min(240, panel.w - 48)
    top = pygame.Rect(0, 0, width, 42)
    top.center = (panel.centerx, panel.bottom - 78)
    bottom = pygame.Rect(0, 0, width, 42)
    bottom.center = (panel.centerx, panel.bottom - 28)
    if mode == "menu":
        return panel, [("restart", top), ("cancel", bottom)]
    return panel, [("readability", top), ("close", bottom)]
