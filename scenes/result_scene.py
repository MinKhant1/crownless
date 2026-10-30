import pygame

from config.settings import LIGHT_TEXT, VICTORY_GOLD
from game.run_state import RunState
from rendering.asset_manager import AssetManager
from rendering.hud_renderer import _blit_text, draw_background, draw_button, get_font


def result_button(window: tuple[int, int], run: RunState) -> tuple[pygame.Rect, pygame.Rect]:
    extra = 34 if run.phase == "victory" and run.golden_reward else 0
    panel = pygame.Rect(0, 0, min(520, window[0] - 80), 300 + extra)
    panel.center = (window[0] // 2, window[1] // 2)
    button = pygame.Rect(0, 0, 240, 52)
    button.center = (panel.centerx, panel.bottom - 64)
    return panel, button


def handle_result_click(run: RunState, pos: tuple[int, int], window: tuple[int, int]) -> str | None:
    _panel, button = result_button(window, run)
    if not button.collidepoint(pos):
        return None
    if run.phase == "victory":
        run.continue_from_victory()
        return None
    return "restart"


def draw_result(screen: pygame.Surface, assets: AssetManager, run: RunState) -> None:
    draw_background(screen, assets)
    panel, button = result_button(screen.get_size(), run)
    pygame.draw.rect(screen, (48, 30, 20), panel, border_radius=16)
    pygame.draw.rect(screen, (214, 170, 90), panel, width=3, border_radius=16)
    if run.phase == "victory":
        title = "Victory"
        lines = ["The enemy army is gone.", f"+{VICTORY_GOLD} Gold"]
        if run.golden_reward:
            lines.append(f"+{run.golden_reward} Gold from Golden pieces")
        lines.append(f"Gold  {run.gold}")
        label = "Continue"
    elif run.phase == "complete":
        title = "Run Complete"
        lines = ["You cleared every level.", f"Gold  {run.gold}"]
        label = "Restart Run"
    else:
        title = "Run Over"
        lines = ["Your King was lost.", "The run ends here."]
        label = "Restart Run"
    _blit_text(screen, title, get_font(40, bold=True), LIGHT_TEXT, center=(panel.centerx, panel.y + 58))
    font = get_font(22, bold=False)
    y = panel.y + 118
    for line in lines:
        _blit_text(screen, line, font, (236, 220, 196), center=(panel.centerx, y))
        y += 34
    draw_button(screen, button, label, font_size=22)
