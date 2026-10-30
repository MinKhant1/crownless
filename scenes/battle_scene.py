import pygame

from game.run_state import RunState
from rendering.asset_manager import AssetManager
from rendering.hud_renderer import _blit_text, draw_button, get_font
from rendering.battle_view import render_battle
from rendering.layout import Layout, square_at
from rendering.overlay_renderer import draw_trait_tooltip


def debug_buttons(window: tuple[int, int], layout: Layout) -> tuple[pygame.Rect, pygame.Rect]:
    width = 150
    height = 34
    x = layout.frame.right + 16
    if x + width > window[0] - 8:
        x = max(8, layout.frame.left - width - 16)
    win = pygame.Rect(x, layout.frame.y + 36, width, height)
    loss = pygame.Rect(x, win.bottom + 8, width, height)
    return win, loss


def handle_battle_click(run: RunState, pos: tuple[int, int], layout: Layout, window: tuple[int, int]) -> None:
    session = run.battle
    if session is None or session.outcome is not None:
        return
    win, loss = debug_buttons(window, layout)
    if win.collidepoint(pos):
        session.force("victory")
        run.finish_victory()
        return
    if loss.collidepoint(pos):
        session.force("defeat")
        run.finish_defeat()
        return
    square = square_at(layout, pos)
    if square is None:
        return
    session.click(*square)
    if session.outcome == "victory":
        run.finish_victory()
    elif session.outcome == "defeat":
        run.finish_defeat()


def draw_battle(screen: pygame.Surface, assets: AssetManager, run: RunState, layout: Layout, relic_bar=None) -> None:
    session = run.battle
    if session is None:
        return
    game = session.game
    game.current_level = run.level
    game.army_capacity = run.army.capacity
    game.army_size = sum(1 for piece in game.board.pieces if piece.color == "white" and piece.kind != "king")
    if session.rules is not None:
        game.statuses = session.rules.statuses
    render_battle(screen, assets, game, layout, relic_bar=relic_bar, run=run)
    _blit_text(
        screen,
        f"Gold  {run.gold}",
        get_font(22, bold=True),
        (236, 220, 196),
        midleft=(layout.frame.right + 18, layout.frame.y + 8),
    )
    win, loss = debug_buttons(screen.get_size(), layout)
    draw_button(screen, win, "Debug Win", font_size=16)
    draw_button(screen, loss, "Debug Loss", font_size=16)
    draw_trait_tooltip(screen, game, layout)
