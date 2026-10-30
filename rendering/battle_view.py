import pygame

from game.game import Game
from rendering.asset_manager import AssetManager
from rendering.board_renderer import draw_board
from rendering.army_panel import ArmyPanel
from rendering.battle_columns import draw_left_sidebar
from rendering.hud_renderer import draw_background, draw_crown, draw_debug, draw_labels, draw_turn
from rendering.layout import Layout
from rendering.piece_renderer import draw_pieces
from rendering.relic_overlays import draw_relic_overlays


def render_battle(screen: pygame.Surface, assets: AssetManager, game: Game, layout: Layout, relic_bar=None, run=None, backdrop: bool = True, army: ArmyPanel | None = None) -> None:
    if backdrop:
        draw_background(screen, assets)
    if relic_bar is not None and run is not None:
        relic_bar.draw_cards(screen, assets, run, layout)
    draw_board(screen, assets, layout)
    draw_labels(screen, layout)
    draw_pieces(screen, assets, game, layout)
    if run is not None and run.phase == "battle":
        draw_relic_overlays(screen, game, layout, run)
    draw_crown(screen, assets, layout)
    show_turn = run is None or run.phase == "battle" or run.visual_pieces is not None
    if show_turn:
        draw_turn(screen, game, layout)
    if run is not None:
        draw_left_sidebar(screen, run, layout)
        if run.visual_pieces is None:
            panel = army if army is not None else ArmyPanel()
            panel.draw(screen, assets, run, layout)
    if game.debug:
        draw_debug(screen, game, layout)
