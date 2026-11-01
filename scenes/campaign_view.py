import math

import pygame

from config.settings import BATTLE_START_TIME, VICTORY_BANNER_TIME, VICTORY_REWARD_TIME
from game.run_state import RunState
from game.scene_manager import SceneManager
from game.transitions.easing import ease_out_cubic
from rendering.asset_manager import AssetManager
from rendering.hud_renderer import _blit_text, draw_background, get_font
from rendering.layout import Layout
from rendering.shop_layout import ShopLayout
from scenes.battle_scene import draw_battle
from scenes.deployment_scene import DeploymentScene
from rendering.victory_summary import draw_victory_summary
from scenes.result_scene import draw_outcome_banner, draw_result
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
    if phase == "shop":
        draw_shop(screen, assets, run, shop_layout, backdrop=backdrop, entrance=entrance)
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
    font = get_font(40, bold=True)
    text = font.render("BATTLE START", True, (245, 230, 204))
    plate = pygame.Surface((text.get_width() + 56, text.get_height() + 28), pygame.SRCALPHA)
    pygame.draw.rect(plate, (48, 30, 20, int(210 * fade)), plate.get_rect(), border_radius=12)
    pygame.draw.rect(plate, (214, 170, 90, int(255 * fade)), plate.get_rect(), width=2, border_radius=12)
    dest = text.get_rect(center=plate.get_rect().center)
    plate.blit(text, dest)
    plate.set_alpha(int(255 * fade))
    screen.blit(plate, plate.get_rect(center=layout.board.center))


def _draw_gold_chip(screen: pygame.Surface, gold: int) -> None:
    font = get_font(20, bold=True)
    label = f"Gold  {gold}"
    width, height = font.size(label)
    rect = pygame.Rect(screen.get_width() - width - 36, 16, width + 24, height + 14)
    pygame.draw.rect(screen, (236, 220, 196), rect, border_radius=8)
    pygame.draw.rect(screen, (92, 64, 42), rect, width=2, border_radius=8)
    _blit_text(screen, label, font, (68, 40, 26), center=rect.center)


def settle_finished_board(run: RunState) -> None:
    if run.battle is None:
        return
    game = run.battle.game
    game.legal = []
    game.selected_id = None
    game.hover = None
