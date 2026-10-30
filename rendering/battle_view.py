import pygame

from game.game import Game
from rendering.asset_manager import AssetManager
from rendering.board_renderer import draw_board
from rendering.hud_renderer import draw_background, draw_crown, draw_debug, draw_header_and_status, draw_labels, draw_turn
from rendering.layout import Layout
from rendering.piece_renderer import draw_pieces


def render_battle(screen: pygame.Surface, assets: AssetManager, game: Game, layout: Layout, relic_bar=None, run=None) -> None:
    draw_background(screen, assets)
    draw_header_and_status(screen, assets, game, layout)
    if relic_bar is not None and run is not None:
        relic_bar.draw_cards(screen, assets, run, layout)
    draw_board(screen, assets, layout)
    draw_labels(screen, layout)
    draw_pieces(screen, assets, game, layout)
    draw_crown(screen, assets, layout)
    draw_turn(screen, game, layout)
    if game.debug:
        draw_debug(screen, game, layout)
