import math

import pygame

from config.settings import BATTLE_START_TIME, VICTORY_BANNER_TIME, VICTORY_REWARD_TIME
from game.run_state import RunState
from game.scene_manager import SceneManager
from game.transitions.easing import ease_out_cubic
from rendering.asset_manager import AssetManager
from rendering import style
from rendering.hud_renderer import _blit_text, draw_background, get_font
from rendering.layout import Layout
from rendering.shop_layout import ShopLayout
from scenes.battle_scene import draw_battle
from scenes.deployment_scene import DeploymentScene
from rendering.victory_summary import draw_victory_summary
from scenes.result_scene import draw_outcome_banner, draw_result
from rendering.battle_columns import draw_left_sidebar
from rendering.collection_overlay import collection_overlay
from rendering.shop_renderer import draw_shop


def present(
    screen: pygame.Surface,
    assets: AssetManager,
    run: RunState,
    deployment: DeploymentScene,
    relic_bar,
    scene: SceneManager,
    board_layout: Layout,
    shop_layout: ShopLayout,
) -> None:
    if scene.motion.active and scene.outgoing is not None and scene.incoming is not None:
        draw_background(screen, assets)
        size = screen.get_size()
        outgoing = scene.layer("out", size)
        incoming = scene.layer("in", size)
        _paint(outgoing, assets, run, deployment, relic_bar, scene, board_layout, shop_layout, scene.outgoing, 1.0, True)
        _paint(incoming, assets, run, deployment, relic_bar, scene, board_layout, shop_layout, scene.incoming, scene.motion.progress(), False)
        scene.motion.render(screen, outgoing, incoming)
        _draw_gold_chip(screen, run.gold)
        return
    _paint(screen, assets, run, deployment, relic_bar, scene, board_layout, shop_layout, run.phase, 1.0, False)
    if scene.banner_name == "battle_start" and run.phase == "battle" and scene.banner_elapsed < BATTLE_START_TIME:
        _draw_battle_start(screen, board_layout, scene.banner_elapsed)


def _paint(
    screen: pygame.Surface,
    assets: AssetManager,
    run: RunState,
    deployment: DeploymentScene,
    relic_bar,
    scene: SceneManager,
    board_layout: Layout,
    shop_layout: ShopLayout,
    phase: str,
    entrance: float,
    settled: bool,
) -> None:
    backdrop = not scene.motion.active
    if phase == "starter":
        draw_background(screen, assets)
        collection_overlay.paint(screen, assets, run)
        return
    if phase == "shop":
        if collection_overlay.blocks(run):
            draw_background(screen, assets)
            collection_overlay.paint(screen, assets, run)
            return
        draw_shop(screen, assets, run, shop_layout, backdrop=backdrop, entrance=entrance)
        draw_left_sidebar(screen, run, board_layout, assets)
        return
    if phase in ("preview", "deployment"):
        deployment.draw(screen, assets, run, board_layout, relic_bar, backdrop=backdrop)
        return
    if phase in ("battle", "victory", "defeat"):
        draw_battle(screen, assets, run, board_layout, relic_bar, backdrop=backdrop, deployment=deployment)
        if phase == "victory":
            _enter, reward, show_button = _victory_amounts(scene, settled)
            elapsed = 2.0 if settled else scene.banner_elapsed
            draw_victory_summary(screen, assets, run, elapsed, show_button, reward)
        elif phase == "defeat":
            enter, reward, show_button = _victory_amounts(scene, settled)
            draw_outcome_banner(screen, run, "defeat", enter, reward, show_button)
        return
    draw_result(screen, assets, run, backdrop=backdrop)


def _victory_amounts(scene: SceneManager, settled: bool) -> tuple[float, float, bool]:
    if settled:
        return 1.0, 1.0, True
    enter = ease_out_cubic(min(1.0, scene.banner_elapsed / max(0.01, VICTORY_BANNER_TIME)))
    reward = ease_out_cubic(min(1.0, max(0.0, scene.banner_elapsed - VICTORY_BANNER_TIME) / max(0.01, VICTORY_REWARD_TIME)))
    return enter, reward, scene.result_ready()


def _draw_battle_start(screen: pygame.Surface, layout: Layout, elapsed: float) -> None:
    fade = math.sin(min(1.0, elapsed / max(0.01, BATTLE_START_TIME)) * math.pi)
    wash = pygame.Surface(layout.board.size, pygame.SRCALPHA)
    wash.fill((214, 170, 90, int(40 * fade)))
    screen.blit(wash, layout.board.topleft)
    font = style.title_font(40, bold=True)
    width, height = font.size("Battle Start")
    plate = pygame.Surface((width + 80, height + 34), pygame.SRCALPHA)
    plate.blit(style.plaque(plate.get_size(), "selected"), (0, 0))
    style.text(plate, "Battle Start", font, style.GOLD_BRIGHT, shadow=(10, 4, 2, 220), center=plate.get_rect().center)
    plate.set_alpha(int(255 * fade))
    screen.blit(plate, plate.get_rect(center=layout.board.center))


def _draw_gold_chip(screen: pygame.Surface, gold: int) -> None:
    font = style.title_font(20, bold=True)
    label = f"Gold  {gold}"
    width, height = font.size(label)
    rect = pygame.Rect(screen.get_width() - width - 40, 16, width + 28, height + 14)
    screen.blit(style.plaque(rect.size, "idle"), rect.topleft)
    style.text(screen, label, font, style.GOLD_BRIGHT, shadow=(8, 4, 2, 220), center=rect.center)


def settle_finished_board(run: RunState) -> None:
    if run.battle is None:
        return
    game = run.battle.game
    game.legal = []
    game.selected_id = None
    game.hover = None
