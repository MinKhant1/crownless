import pygame

from game.run_state import RunState
from rendering.asset_manager import AssetManager
from rendering.hud_renderer import draw_button
from rendering.battle_view import render_battle
from rendering.layout import Layout, square_at
from rendering.overlay_renderer import draw_trait_tooltip


def debug_buttons(window: tuple[int, int], layout: Layout) -> tuple[pygame.Rect, pygame.Rect]:
    width = min(160, layout.left.w - 28)
    height = 34
    x = layout.left.x + 14
    loss = pygame.Rect(x, layout.menu.y - 8 - height, width, height)
    win = pygame.Rect(x, loss.y - 8 - height, width, height)
    return win, loss


def handle_battle_click(run: RunState, pos: tuple[int, int], layout: Layout, window: tuple[int, int], enemy_busy: bool = False) -> None:
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
    if enemy_busy or session.game.turns.current == "black":
        return
    if layout.left.collidepoint(pos) or layout.right.collidepoint(pos):
        return
    square = square_at(layout, pos)
    if square is None:
        return
    session.click(*square)
    if session.outcome == "victory":
        run.finish_victory()
    elif session.outcome == "defeat":
        run.finish_defeat()


def draw_battle(screen: pygame.Surface, assets: AssetManager, run: RunState, layout: Layout, relic_bar=None, backdrop: bool = True, deployment=None) -> None:
    session = run.battle
    if session is None:
        return
    game = session.game
    game.current_level = run.level
    game.army_capacity = run.army.capacity
    game.army_size = sum(1 for piece in game.board.pieces if piece.color == "white" and piece.kind != "king")
    if session.rules is not None:
        game.statuses = session.rules.statuses
    army = None if deployment is None else deployment.army
    render_battle(screen, assets, game, layout, relic_bar=relic_bar, run=run, backdrop=backdrop, army=army)
    if session.outcome is None:
        win, loss = debug_buttons(screen.get_size(), layout)
        draw_button(screen, win, "Debug Win", font_size=16)
        draw_button(screen, loss, "Debug Loss", font_size=16)
    draw_trait_tooltip(screen, game, layout)
