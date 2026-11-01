import pygame

from config.settings import LIGHT_TEXT, VICTORY_GOLD
from game.level_manager import describe_counts
from game.relics.relic_data import relic_by_id
from game.run_state import RunState
from game.transitions.easing import ease_out_cubic
from rendering.asset_manager import AssetManager
from rendering.hud_renderer import _blit_text, draw_background, draw_button, get_font
from rendering.victory_summary import continue_rect


def result_button(window: tuple[int, int], run: RunState) -> tuple[pygame.Rect, pygame.Rect]:
    panel = pygame.Rect(0, 0, min(560, window[0] - 80), 340)
    panel.center = (window[0] // 2, window[1] // 2)
    button = pygame.Rect(0, 0, 240, 52)
    button.center = (panel.centerx, panel.bottom - 48)
    return panel, button


def outcome_button(window: tuple[int, int], run: RunState) -> pygame.Rect | None:
    if run.phase == "complete":
        return result_button(window, run)[1]
    if run.phase == "victory":
        return continue_rect(window, run)
    if run.phase == "defeat":
        return _banner_button(window, run, run.phase)
    return None


def handle_result_click(run: RunState, pos: tuple[int, int], window: tuple[int, int]) -> str | None:
    button = outcome_button(window, run)
    if button is None or not button.collidepoint(pos):
        return None
    if run.phase == "victory":
        return "continue"
    if run.phase in ("defeat", "complete"):
        return "restart"
    return None


def draw_result(screen: pygame.Surface, assets: AssetManager, run: RunState, backdrop: bool = True) -> None:
    if backdrop:
        draw_background(screen, assets)
    panel, button = result_button(screen.get_size(), run)
    pygame.draw.rect(screen, (48, 30, 20), panel, border_radius=16)
    pygame.draw.rect(screen, (214, 170, 90), panel, width=3, border_radius=16)
    if run.phase == "complete":
        title = "CROWNLESS — RUN COMPLETE"
        lines = ["Level 5 is clear.", f"Gold  {run.gold}", describe_counts(_army_counts(run))]
        label = "Restart Run"
    elif run.phase == "defeat":
        title = "GAME OVER"
        lines = ["Your King was lost.", "The run ends here."]
        label = "Restart Run"
    else:
        title = f"LEVEL {run.level} COMPLETE"
        lines = _reward_lines(run)
        label = "Continue"
    _blit_text(screen, title, get_font(32, bold=True), LIGHT_TEXT, center=(panel.centerx, panel.y + 52))
    font = get_font(22, bold=False)
    y = panel.y + 112
    for line in lines:
        _blit_text(screen, line, font, (236, 220, 196), center=(panel.centerx, y))
        y += 32
    draw_button(screen, button, label, font_size=22)


def draw_outcome_banner(
    screen: pygame.Surface,
    run: RunState,
    kind: str,
    enter: float,
    reward: float,
    show_button: bool,
) -> None:
    window = screen.get_size()
    panel = _banner_panel(window, run, kind, enter)
    slide = pygame.Surface(panel.size, pygame.SRCALPHA)
    pygame.draw.rect(slide, (48, 30, 20, 230), slide.get_rect(), border_radius=16)
    pygame.draw.rect(slide, (214, 170, 90, 255), slide.get_rect(), width=3, border_radius=16)
    title = "GAME OVER" if kind == "defeat" else f"LEVEL {run.level} COMPLETE"
    _blit_text(slide, title, get_font(32, bold=True), LIGHT_TEXT, center=(panel.w // 2, 48))
    if kind == "defeat":
        _blit_text(slide, "Your King was lost.", get_font(22, bold=False), (236, 220, 196), center=(panel.w // 2, 96))
    elif reward > 0.02:
        y = 92
        for line in _reward_lines(run):
            _blit_text(slide, line, get_font(22, bold=False), (236, 220, 196), center=(panel.w // 2, y))
            y += 28
    slide.set_alpha(int(255 * ease_out_cubic(enter)))
    screen.blit(slide, panel.topleft)
    if show_button and enter >= 0.99:
        label = "Restart Run" if kind == "defeat" else "Continue"
        draw_button(screen, _banner_button(window, run, kind), label, font_size=20)


def _reward_lines(run: RunState) -> list[str]:
    lines = [f"+{VICTORY_GOLD} Gold"]
    if run.golden_reward:
        lines.append(f"+{run.golden_reward} Gold from Golden pieces")
    charm = _charm_bonus(run)
    if charm:
        lines.append(f"+{charm} Gold from Gold Charm")
    lines.append(f"Gold  {run.gold}")
    return lines


def _charm_bonus(run: RunState) -> int:
    if not run.relics.owns("gold_charm"):
        return 0
    definition = relic_by_id("gold_charm")
    if definition is None:
        return 0
    return int(definition.parameters.get("gold", 0))


def _army_counts(run: RunState) -> dict[str, int]:
    counts: dict[str, int] = {}
    for piece in run.army.pieces:
        counts[piece.kind] = counts.get(piece.kind, 0) + 1
    return counts


def _banner_panel(window: tuple[int, int], run: RunState, kind: str, enter: float) -> pygame.Rect:
    lines = 2 if kind == "defeat" else len(_reward_lines(run))
    height = 132 + lines * 28
    width = min(520, window[0] - 80)
    settled_y = (window[1] - height) // 2 - 10
    y = settled_y + int((1.0 - max(0.0, min(1.0, enter))) * -80)
    return pygame.Rect((window[0] - width) // 2, y, width, height)


def _banner_button(window: tuple[int, int], run: RunState, kind: str) -> pygame.Rect:
    panel = _banner_panel(window, run, kind, 1.0)
    button = pygame.Rect(0, 0, 220, 46)
    button.center = (panel.centerx, panel.bottom - 32)
    return button
